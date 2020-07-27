"""Convert Adler's Notes from Nature expedition CSV format."""

# pylint: disable=invalid-name,unused-argument

import re
import json
from dateutil.parser import parse
import pandas as pd
import lib.util as util

SUBJECT_PREFIX = 'subject_'
STARTED_AT = 'classification_started_at'
USER_NAME = 'user_name'


def read(args):
    """Read and convert the input CSV data."""
    df = pd.read_csv(args.input_file, dtype=str)

    # Workflows must be processed individually
    workflow_id = get_workflow_id(df, args)

    df = remove_rows_not_in_workflow(df, str(workflow_id))

    get_nfn_only_defaults(df, args, workflow_id)

    # Extract the various json blobs
    column_types = {}
    df = (extract_annotations(df, args, column_types)
          .pipe(extract_subject_data, column_types)
          .pipe(extract_metadata))

    # Get the subject_id from the subject_ids list, use the first one
    df[args.group_by] = df.subject_ids.map(
        lambda x: int(str(x).split(';')[0]))

    # Remove unwanted columns
    unwanted_columns = [c for c in df.columns
                        if c.lower() in [
                            'user_id',
                            'user_ip',
                            'subject_ids',
                            'subject_data',
                            (SUBJECT_PREFIX + 'retired').lower()]]
    df = df.drop(unwanted_columns, axis=1)
    column_types = {k: v for k, v in column_types.items()
                    if k not in unwanted_columns}

    columns = util.sort_columns(args, df.columns, column_types)
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.reindex(columns, axis='columns').fillna('')
    df = df.sort_values([args.group_by, STARTED_AT])
    df = df.drop_duplicates([args.group_by, USER_NAME], keep='first')
    df = df.groupby(args.group_by).head(args.keep_count)

    return df, column_types


def remove_rows_not_in_workflow(df, workflow_id):
    """Remove all rows not in the dataframe."""
    return df.loc[df.workflow_id == workflow_id, :]


def get_nfn_only_defaults(df, args, workflow_id):
    """Set nfn-only argument defaults."""
    if args.summary:
        workflow_name = get_workflow_name(df)

    if not args.title and args.summary:
        args.title = 'Summary of "{}" ({})'.format(workflow_name, workflow_id)

    if not args.user_column:
        args.user_column = USER_NAME


def get_workflow_id(df, args):
    """Pull the workflow ID from the data-df if it was not given."""
    if args.workflow_id:
        return args.workflow_id

    workflow_ids = df.workflow_id.unique()

    if len(workflow_ids) > 1:
        util.error_exit('There are multiple workflows in this file. '
                        'You must provide a workflow ID as an argument.')

    return workflow_ids[0]


def get_workflow_name(df):
    """Extract and format the workflow name from the data df."""
    try:
        workflow_name = df.workflow_name.iloc[0]
        workflow_name = re.sub(r'^[^_]*_', '', workflow_name)
    except KeyError:
        util.error_exit('Workflow name not found in classifications file.')
    return workflow_name


def extract_metadata(df):
    """Extract a few fields from the metadata JSON object."""
    def _extract_date(value):
        return parse(value).strftime('%d-%b-%Y %H:%M:%S')

    data = df.metadata.map(json.loads).tolist()
    data = pd.DataFrame(data, index=df.index)

    df[STARTED_AT] = data.started_at.map(_extract_date)

    name = 'classification_finished_at'
    df[name] = data.finished_at.map(_extract_date)

    return df.drop(['metadata'], axis=1)


def extract_subject_data(df, column_types):
    """
    Extract subject data from the json object in the subject_data column.

    We prefix the new column names with "subject_" to keep them separate from
    the other data df columns. The subject data json looks like:
        {<subject_id>: {"key_1": "value_1", "key_2": "value_2", ...}}
    """
    data = (df.subject_data.map(json.loads)
            .apply(lambda x: list(x.values())[0])
            .tolist())
    data = pd.DataFrame(data, index=df.index)
    df = df.drop(['subject_data'], axis=1)

    if 'retired' in data.columns:
        data = data.drop(['retired'], axis=1)

    if 'id' in data.columns:
        data = data.rename(columns={'id': 'external_id'})

    columns = [re.sub(r'\W+', '_', c) for c in data.columns]
    columns = [re.sub(r'^_+|_$', '', c) for c in columns]
    columns = [SUBJECT_PREFIX + c for c in columns]

    columns = dict(zip(data.columns, columns))
    data = data.rename(columns=columns)

    df = pd.concat([df, data], axis=1)

    # Put the subject columns into the column_types: They're all 'same'
    last = util.last_column_type(column_types)
    for name in data.columns:
        last += util.COLUMN_ADD
        column_types[name] = {'type': 'same', 'order': last, 'name': name}

    return df


def extract_annotations(df, args, column_types):
    """
    Extract annotations from the json object in the annotations column.

    Annotations are nested json blobs with a peculiar data format.
    """
    data = df.annotations.map(json.loads)
    data = [flatten_annotations(a, args, column_types) for a in data]
    data = pd.DataFrame(data, index=df.index)

    df = pd.concat([df, data], axis=1)

    return adjust_column_names(
        df, column_types).drop(['annotations'], axis=1)


# #############################################################################

def flatten_annotations(annotations, args, column_types):
    """
    Flatten annotations.

    Annotations are nested json blobs with a peculiar data format. So we
    flatten it to make it easier to reconcile.

    We also need to consider that some tasks have the same label. In that case
    we add a tie breaker, which is handled in the annotation_key() function.
    """
    tasks = {}

    for annotation in annotations:
        flatten_annotation(args, column_types, tasks, annotation)

    return tasks


def flatten_annotation(args, column_types, tasks, task):
    """Flatten one annotation recursively."""
    if isinstance(task.get('value'), list):
        subtask_annotation(args, column_types, tasks, task)
    elif 'select_label' in task:
        select_label_annotation(column_types, tasks, task)
    elif 'task_label' in task:
        task_label_annotation(column_types, tasks, task)
    elif 'tool_label' in task:
        tool_label_annotation(args, column_types, tasks, task)
    else:
        print('Annotation task type not found: {}'.format(task))


def subtask_annotation(args, column_types, tasks, task):
    """Handle a task annotation with subtasks."""
    for subtask in task['value']:
        flatten_annotation(args, column_types, tasks, subtask)


def select_label_annotation(column_types, tasks, task):
    """Handle a select label task annotation."""
    key = annotation_key(tasks, task['select_label'])
    option = task.get('option')
    value = task.get('label', '') if option else task.get('value', '')
    tasks[key] = value
    append_column_type(column_types, key, 'select')


def task_label_annotation(column_types, tasks, task):
    """Handle a task label task annotation."""
    key = annotation_key(tasks, task['task_label'])
    tasks[key] = task.get('value', '')
    append_column_type(column_types, key, 'text')


def tool_label_annotation(args, column_types, tasks, task):
    """Handle a tool label task annotation."""
    # Get the tool label attributes
    label = '{}: box'.format(task['tool_label'])
    label = annotation_key(tasks, label)
    value = json.dumps({
        'left': round(task['x']),
        'right': round(task['x'] + task['width']),
        'top': round(task['y']),
        'bottom': round(task['y'] + task['height'])})
    tasks[label] = value
    append_column_type(column_types, label, 'box')

    # Get the actual tool label value
    label = '{}: select'.format(task['tool_label'])
    label = annotation_key(tasks, label)
    value = task['details'][0]['value'][0]['value']
    tasks[label] = args.tool_label_hack.get(value, '')
    append_column_type(column_types, label, 'select')


def annotation_key(tasks, label):
    """Make a key for the annotation."""
    label = re.sub(r'^\s+|\s+$', '', label)
    i = 1
    base = label
    while label in tasks:
        i += 1
        label = '{} #{}'.format(base, i)
    return label


def append_column_type(column_types, key, column_type):
    """Append the column type to the end of the list of columns."""
    if key not in column_types:
        last = util.last_column_type(column_types)
        column_types[key] = {
            'type': column_type, 'order': last + util.COLUMN_ADD, 'name': key}


# #############################################################################

def adjust_column_names(df, column_types):
    """Rename columns to add a "#1" suffix if there exists a "#2" suffix."""
    rename = {}
    for name in column_types.keys():
        old_name = name[:-3]
        if name.endswith('#2') and column_types.get(old_name):
            rename[old_name] = old_name + ' #1'

    for old_name, new_name in rename.items():
        new_task = column_types[old_name]
        new_task['name'] = new_name
        column_types[new_name] = new_task
        del column_types[old_name]

    return df.rename(columns=rename)
