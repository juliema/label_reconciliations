"""Convert Adler's Notes from Nature expedition CSV format."""

import re
import json
from dateutil.parser import parse
import pandas as pd
import lib.util as util

SUBJECT_PREFIX = 'Subject '
STARTED_AT = 'Classification started at'
USER_NAME = 'user_name'
KEEP_COUNT = 3


def read(args):
    """The main function that does the conversion."""
    df = pd.read_csv(args.input_file, dtype=str)

    # Workflows must be processed individually
    workflow_id = get_workflow_id(df, args)

    df = remove_rows_not_in_workflow(df, workflow_id)

    get_nfn_only_defaults(df, args, workflow_id)

    # Extract the various json blobs
    column_types = {}
    extract_annotations(df, column_types)
    extract_subject_data(df, column_types)
    extract_metadata(df)

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
    df.drop(unwanted_columns, axis=1, inplace=True)
    column_types = {k: v for k, v in column_types.items()
                    if k not in unwanted_columns}

    adjust_column_names(df, column_types)
    columns = util.sort_columns(args, df.columns, column_types)
    df = df.reindex_axis(columns, axis=1).fillna('')
    df.sort_values([args.group_by, STARTED_AT], inplace=True)
    df.drop_duplicates([args.group_by, USER_NAME], keep='first', inplace=True)
    df = df.groupby(args.group_by).head(KEEP_COUNT)

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

    if not args.user_column and args.summary:
        args.user_column = 'user_name'


def get_workflow_id(df, args):
    """Pull the workflow ID from the data-frame if it was not given."""
    if args.workflow_id:
        return args.workflow_id

    workflow_ids = df.workflow_id.unique()

    if len(workflow_ids) > 1:
        util.error_exit('There are multiple workflows in this file. '
                        'You must provide a workflow ID as an argument.')

    return workflow_ids[0]


def get_workflow_name(df):
    """Extract and format the workflow name from the data frame."""
    try:
        workflow_name = df.workflow_name.iloc[0]
        workflow_name = re.sub(r'^[^_]*_', '', workflow_name)
    except KeyError:
        util.error_exit('Workflow name not found in classifications file.')
    return workflow_name


def extract_metadata(df):
    """Extract a few fields from the metadata JSON object."""
    df['json'] = df['metadata'].map(json.loads)

    name = 'Classification started at'
    df[name] = df['json'].apply(extract_date, column='started_at')

    name = 'Classification finished at'
    df[name] = df['json'].apply(extract_date, column='finished_at')

    df.drop(['metadata', 'json'], axis=1, inplace=True)


def extract_subject_data(df, column_types):
    """Extract subject data from the json object in the subject_data column.

    We prefix the new column names with "subject_" to keep them separate from
    the other df columns. The subject data json looks like:
        {subject_id: {"key_1": "value_1", "key_2": "value_2", ...}}
    """
    df['json'] = df['subject_data'].map(json.loads)

    # Put the subject data into the data frame
    for key, row in df.iterrows():
        for subject_dict in iter(row['json'].values()):
            for column, value in subject_dict.items():
                column = re.sub(r'\W+', '_', column)
                column = re.sub(r'^_+|__$', '', column)
                if isinstance(value, dict):
                    value = json.dumps(value)
                df.loc[key, SUBJECT_PREFIX + column] = value

    # Get rid of unwanted data
    df.drop(['subject_data', 'json'], axis=1, inplace=True)

    # Put the subject columns into the column_types: They're all 'same'
    last = util.last_column_type(column_types)
    for name in df.columns:
        if name.startswith(SUBJECT_PREFIX):
            last += 1
            column_types[name] = {'type': 'same', 'order': last, 'name': name}


def extract_annotations(df, column_types):
    """Extract annotations from the json object in the annotations column.

    Annotations are nested json blobs with a peculiar data format.
    """
    df['json'] = df['annotations'].map(json.loads)

    for key, row in df.iterrows():
        tasks_seen = {}
        for task in row['json']:
            try:
                extract_tasks(
                    df, key, task, column_types, tasks_seen)
            except ValueError:
                print('Bad transcription for classification {}'.format(
                    key))
                break

    df.drop(['annotations', 'json'], axis=1, inplace=True)


def extract_tasks(df, key, task, column_types, tasks_seen):
    """Hoist a task annotation field into the data frame."""
    if isinstance(task.get('value'), list):
        for subtask in task['value']:
            extract_tasks(
                df, key, subtask, column_types, tasks_seen)
    elif task.get('select_label'):
        header = create_header(
            task['select_label'], column_types, tasks_seen, 'select')
        df.loc[key, header] = task.get('label', '')
    elif task.get('task_label'):
        header = create_header(
            task['task_label'], column_types, tasks_seen, 'text')
        df.loc[key, header] = task.get('value', '')
    else:
        raise ValueError()


def create_header(label, column_types, tasks_seen, reconciler):
    """Create a header from the given label.

    We need to handle name collisions.
        tasks_seen = all of the columns so far in the row
        column_types = all of the columns so far in the entire data frame
    """
    # Strip out problematic characters from the label
    label = re.sub(r'^\s+|\s+$', '', label)

    tie_breaker = 1  # Tie breaker for duplicate column names
    header = label   # Start with the label
    while header in tasks_seen:
        tie_breaker += 1
        header = '{} #{}'.format(label, tie_breaker)
    tasks_seen[header] = 1

    if not column_types.get(header):
        last = util.last_column_type(column_types)
        column_types[header] = {'type': reconciler,
                                'order': last + 1,
                                'name': header}

    return header


def extract_date(metadata, column=''):
    """Extract dates from a json object."""
    return parse(metadata[column]).strftime('%d-%b-%Y %H:%M:%S')


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

    df.rename(columns=rename, inplace=True)
