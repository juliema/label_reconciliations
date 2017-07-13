"""This module is used to convert the Adler's Notes from Nature expedition CSV
dumps into the format that will be input into the rest of the modules.
"""

import re
import sys
import json
from dateutil.parser import parse
import pandas as pd
import lib.util as util


def read(args):
    """This is the main function that does the conversion."""

    df = pd.read_csv(args.input)

    # Workflows must be processed individually
    workflow_id = util.get_workflow_id(df, args)

    # Remove anything not in the workflow
    df = df.loc[df.workflow_id == workflow_id, :]

    # Extract the various json blobs
    tasks = extract_annotations(df)
    extract_metadata(df)
    extract_subject_data(df)

    # Get the subject_id from the subject_ids list, use the first one
    df['subject_id'] = df.subject_ids.map(
        lambda x: int(str(x).split(';')[0]))

    # Remove unwanted columns
    df.drop(['user_id', 'user_ip'], axis=1, inplace=True)

    adjust_column_names(df, tasks)
    df = sort_columns(df, tasks).fillna('')
    df.sort_values([args.group_by, args.sort_by], inplace=True)

    return df, tasks


def get_workflow_id(df):
    """Pull the workflow ID from the df if it was not given."""

    workflow_ids = df.workflow_id.unique()

    if len(workflow_ids) > 1:
        sys.exit('There are multiple workflows in this file. '
                 'You must provide a workflow ID as an argument.')

    return workflow_ids[0]


def extract_metadata(df):
    """One column in the expedition CSV file contains a json object with
    metadata about the transcription event. We only need a few fields from this
    object.
    """

    df['json'] = df['metadata'].map(json.loads)

    df['classification_started_at'] = df['json'].apply(
        extract_date, column='started_at')
    df['classification_finished_at'] = df['json'].apply(
        extract_date, column='finished_at')

    df.drop(['metadata', 'json'], axis=1, inplace=True)


def extract_subject_data(df):
    """Extract the subject data from the json object in the subject_data
    column. We prefix the new column names with "subject_" to keep them
    separate from the other df columns.
    The subject data json looks like:
        {subject_id: {"key_1": "value_1", "key_2": "value_2", ...}}
    """

    df['json'] = df['subject_data'].map(json.loads)

    for subject in df['json']:
        for subject_dict in iter(subject.values()):
            for column, value in subject_dict.items():
                column = re.sub(r'\W+', '_', column)
                column = re.sub(r'^_+|__$', '', column)
                if isinstance(value, dict):
                    value = json.dumps(value)
                df['subject: ' + column] = value

    df.drop(['subject_data', 'json'], axis=1, inplace=True)

    if 'subject_id' in df.columns:
        df.rename(columns={'subject_id': 'subject_id_external'}, inplace=True)


def extract_annotations(df):
    """Extract annotations from the json object in the annotations column.
    Annotations are nested json blobs with a peculiar data format.
    """

    df['json'] = df['annotations'].map(json.loads)

    all_tasks = {}

    for classification_id, tasks in df.iterrows():
        tasks_seen = {}
        for task in tasks['json']:
            try:
                extract_tasks(
                    df, classification_id, task, all_tasks, tasks_seen)
            except ValueError:
                print('Bad transcription for classification {}'.format(
                    classification_id))
                break

    df.drop(['annotations', 'json'], axis=1, inplace=True)

    return all_tasks


def extract_tasks(df, classification_id, task, all_tasks, tasks_seen):
    """Hoists a task annotation field into the data frame."""

    if isinstance(task.get('value'), list):
        for subtask in task['value']:
            extract_tasks(
                df, classification_id, subtask, all_tasks, tasks_seen)
    elif task.get('select_label'):
        header = create_header(
            task['select_label'], all_tasks, tasks_seen, 'select')
        df.loc[classification_id, header] = task.get('label', '')
    elif task.get('task_label'):
        header = create_header(
            task['task_label'], all_tasks, tasks_seen, 'text')
        df.loc[classification_id, header] = task.get('value', '')
    else:
        raise ValueError()


def create_header(label, all_tasks, tasks_seen, reconciler):
    """Create a header from the given label. We need to handle name collisions.
    tasks_seen = all of the columns so far in the row
    all_tasks = all of the columns so far in the entire dataframe
    """

    # Strip out problematic characters from the label
    label = re.sub(r'^\s+|\s+$', '', label)

    tie_breaker = 1  # Tie breaker for duplicate column names
    header = label   # Start with the label
    while header in tasks_seen:
        tie_breaker += 1
        header = '{} #{}'.format(label, tie_breaker)
    tasks_seen[header] = 1

    if not all_tasks.get(header):
        last = max([v['order'] for v in all_tasks.values()], default=1)
        all_tasks[header] = {'type': reconciler,
                             'order': last + 1,
                             'name': header}

    return header


def extract_date(metadata, column=''):
    """Extract dates from a json object."""

    return parse(metadata[column]).strftime('%d-%b-%Y %H:%M:%S')


def adjust_column_names(df, tasks):
    """Rename columns to add a "#1" suffix if there is a corresponding column
    with a "#2" suffix.
    """

    rename = {}
    for name in tasks.keys():
        old_name = name[:-3]
        if name.endswith('#2') and tasks.get(old_name):
            rename[old_name] = old_name + ' #1'

    for old_name, new_name in rename.items():
        new_task = tasks[old_name]
        new_task['name'] = new_name
        tasks[new_name] = new_task
        del tasks[old_name]

    df.rename(columns=rename, inplace=True)


def sort_columns(df, tasks):
    """Put columns into an order useful for displaying."""

    columns = ['subject_id', 'classification_id']
    columns.extend([v['name'] for v
                    in sorted(tasks.values(), key=lambda x: x['order'])])
    columns.extend([c for c in df.columns if c not in columns])

    return df.reindex_axis(columns, axis=1)
