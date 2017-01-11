"""This module builds up the data used to reconcile the data later."""

import sys
import json
import dateutil
import pandas as pd


SELECT_COLUMN_FLAG = 's'  # Flag a select column
TEXT_COLUMN_FLAG = 't'    # Flag a text column


def extract_json_value(subject_json, column=''):
    """Pull fields out of a json object object as a string value."""
    if column in list(subject_json.values())[0]:
        return list(subject_json.values())[0][column]


def extract_json_date(metadata_json, column=''):
    """Extract dates from a json object."""
    return dateutil.parser.parse(metadata_json[column]).strftime('%d-%b-%Y %H:%M:%S')


def header_label(task_id, label, task_type):
    """
    Build a column header from the annotations json object. It contains flags for later processing.
    """
    return '{}{:0>3}{}: {}'.format(task_id[0], task_id[1:], task_type, label)


def extract_an_annotaion(unreconciled_df, task, task_id, index):
    """Hoists an annotion field into the data frame."""
    if isinstance(task.get('value'), list):
        for subtask in task['value']:
            subtask_id = subtask.get('task', task_id)
            extract_an_annotaion(unreconciled_df, subtask, subtask_id, index)
    elif task.get('select_label'):
        header = header_label(task_id, task['select_label'], SELECT_COLUMN_FLAG)
        value = task.get('label')
        unreconciled_df.loc[index, header] = value
    elif task.get('task_label'):
        header = header_label(task_id, task['task_label'], TEXT_COLUMN_FLAG)
        value = task.get('value')
        unreconciled_df.loc[index, header] = value
    else:
        raise ValueError()


def extract_annotations_json(unreconciled_df):
    """
    Extract annotations from a json object. Annotations are a deeply nested json blob with a
    peculiar data format. We use this function to gather the data type so that we can hoist the
    data later on.
    """
    unreconciled_df['annotation_json'] = unreconciled_df['annotations'].map(json.loads)
    for index, row in unreconciled_df.iterrows():
        for task in row['annotation_json']:
            task_id = task['task']
            try:
                extract_an_annotaion(unreconciled_df, task, task_id, index)
            except ValueError:
                print('Bad transcription for classification {}'.format(row['classification_id']))
                break
    unreconciled_df.drop('annotation_json', axis=1, inplace=True)


def extract_subject_json(unreconciled_df):
    """Hoist the subject data into the data frame."""
    unreconciled_df['subject_json'] = unreconciled_df['subject_data'].map(json.loads)
    subject_keys = {}
    for subj in unreconciled_df['subject_json']:
        for val in iter(subj.values()):
            for k in val.keys():
                subject_keys[k] = 1
    for k in subject_keys:
        unreconciled_df['subject_' + k] = unreconciled_df['subject_json'].apply(
            extract_json_value, column=k)
    unreconciled_df.drop('subject_json', axis=1, inplace=True)


def extract_metata_json(unreconciled_df):
    """Hoist desired metadata data into the data frame."""
    unreconciled_df['metadata_json'] = unreconciled_df['metadata'].map(json.loads)
    unreconciled_df['classification_started_at'] = unreconciled_df['metadata_json'].apply(
        extract_json_date, column='started_at')
    unreconciled_df['classification_finished_at'] = unreconciled_df['metadata_json'].apply(
        extract_json_date, column='finished_at')
    unreconciled_df.drop('metadata_json', axis=1, inplace=True)


def get_workflow_id(workflow_id, unreconciled_df):
    """Pull the workflow ID from the dataframe if it was not given."""
    if workflow_id:
        return workflow_id
    workflow_ids = unreconciled_df.workflow_id.unique()
    if len(workflow_ids) > 1:
        print('There are multiple workflows in this file. You must provide a workflow ID')
        sys.exit(1)
    return workflow_ids[0]


def create_unreconciled_dataframe(workflow_id, classifications):
    """This is the main function called by external modules."""
    unreconciled_df = pd.read_csv(classifications)
    workflow_id = get_workflow_id(workflow_id, unreconciled_df)

    # We need to do this by workflow because each one's annotations have a different structure
    # pylint: disable=no-member
    unreconciled_df = unreconciled_df.loc[unreconciled_df.workflow_id == workflow_id, :]
    # pylint: enable=no-member

    # bring the last column to be the first
    cols = unreconciled_df.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    unreconciled_df = unreconciled_df[cols]

    # Make key data types match in the two data frames
    unreconciled_df['subject_ids'] = unreconciled_df.subject_ids.map(
        lambda x: int(str(x).split(';')[0]))

    extract_metata_json(unreconciled_df)
    extract_annotations_json(unreconciled_df)
    extract_subject_json(unreconciled_df)

    unreconciled_df.drop(['user_id', 'user_ip'], axis=1, inplace=True)
    unreconciled_df.rename(columns={'subject_ids': 'subject_id'}, inplace=True)
    unreconciled_df.sort_values(['subject_id', 'classification_id'], inplace=True)

    return unreconciled_df
