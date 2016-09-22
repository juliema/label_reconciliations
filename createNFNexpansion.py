import os
import re
import sys
import json
import pandas as pd
import dateutil


def extract_json_value(subject_json, column=''):
    if column in list(subject_json.values())[0]:
        return list(subject_json.values())[0][column]


def extract_json_date(metadata_json, column=''):
    return dateutil.parser.parse(metadata_json[column]).strftime('%d-%b-%Y %H:%M:%S')


def header_label(task_id, label, task_type):
    return '({}{}) {}'.format(task_id, task_type, label)


def extract_an_annotaion(df, task, task_id, index):
    if isinstance(task.get('value'), list):
        for subtask in task['value']:
            subtask_id = subtask.get('task', task_id)
            extract_an_annotaion(df, subtask, subtask_id, index)
    elif task.get('select_label'):
        header = header_label(task_id, task['select_label'], 's')
        value = task.get('label')
        df.loc[index, header] = value
    elif task.get('task_label'):
        header = header_label(task_id, task['task_label'], 't')
        value = task.get('value')
        df.loc[index, header] = value
    else:
        print('Error: Could not parse the annotations.')
        sys.exit()


def extract_annotations_json(df):
    df['annotation_json'] = df['annotations'].map(lambda x: json.loads(x))
    for index, row in df.iterrows():
        for task in row['annotation_json']:
            task_id = task['task']
            extract_an_annotaion(df, task, task_id, index)
    df.drop('annotation_json', axis=1, inplace=True)


def extract_subject_json(df):
    df['subject_json'] = df['subject_data'].map(lambda x: json.loads(x))
    subject_keys = {}
    for subj in df['subject_json']:
        for val in iter(subj.values()):
            for k in val.keys():
                subject_keys[k] = 1
    for k in subject_keys.keys():
        df['subject_' + k] = df['subject_json'].apply(extract_json_value, column=k)
    df.drop('subject_json', axis=1, inplace=True)


def extract_metata_json(df):
    df['metadata_json'] = df['metadata'].map(lambda x: json.loads(x))
    df['classification_started_at'] = df['metadata_json'].apply(extract_json_date, column='started_at')
    df['classification_finished_at'] = df['metadata_json'].apply(extract_json_date, column='finished_at')
    df.drop('metadata_json', axis=1, inplace=True)


def expand(workflow_id, classifications_file, subjects_file):
    print("Reading classifications csv file for NfN...")

    subjects_df = pd.read_csv(subjects_file)

    df = pd.read_csv(classifications_file)
    # We need to do this by workflow because each one's annotations have a different structure
    df = df.loc[df.workflow_id == workflow_id, :]

    # bring the last column to be the first
    cols = df.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    df = df[cols]

    # Make key data types match in the two data frames
    df['subject_ids'] = df.subject_ids.map(lambda x: int(x.split(';')[0]))

    # Get subject info we need from the subjects_df
    df = pd.merge(df, subjects_df[['subject_id', 'locations']], how='left',
                  left_on='subject_ids', right_on='subject_id')

    df.drop(['user_id', 'user_ip', 'subject_id'], axis=1, inplace=True)

    extract_metata_json(df)
    extract_annotations_json(df)
    extract_subject_json(df)

    df.sort(['subject_ids', 'classification_id'], inplace=True)
    print("The new columns:")
    print(df.columns.values)

    df.to_csv('expanded_values_{}.csv'.format(workflow_id), sep=',', index=False, encoding='utf-8')


def args():
    if len(sys.argv) < 4:
        help()
    try:
        workflow_id = int(sys.argv[1])
    except:
        help('Workflow ID should be a number.')
    if not os.path.isfile(sys.argv[2]):
        help('Cannot read classifications file "{}".'.format(sys.argv[2]))
    if not os.path.isfile(sys.argv[3]):
        help('Cannot read subjects file "{}".'.format(sys.argv[3]))
    return workflow_id, sys.argv[2], sys.argv[3]


def help(msg=''):
    print('Usage: python createNFNexpansion.py <workflow ID> <classifications file> <subjects file>')
    if msg:
        print(msg)
    sys.exit()


if __name__ == "__main__":
    workflow_id, classifications_file, subjects_file = args()
    expand(workflow_id, classifications_file, subjects_file)
