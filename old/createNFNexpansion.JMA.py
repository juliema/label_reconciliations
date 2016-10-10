import pandas as pd
from pandas.io.json import json_normalize
import numpy as np
import json
from dateutil import parser
import sys
import os


def extract_json_value(subject_json, column=''):
    if column in list(subject_json.values())[0]:
        return list(subject_json.values())[0][column]


def extract_json_value_loc(subject_json):
    return ';'.join(list(subject_json.values()))


def extract_json_date(metadata_json, column=''):
    return parser.parse(metadata_json[column]).strftime('%d-%b-%Y %H:%M:%S')


def extendedUserID(row):
    if pd.isnull(row['user_id']):
        extended = row['user_name']
    else:
        extended = row['user_id']
    return extended


def extract_annotations(df):
    for index, row in df.iterrows():
        for i in row['annotation_json']:
            if type(i['value']) is str:
                # create columns with task names and assign content to the appropriate row
                df.loc[index, i['task'] + '_value'] = i['value']
                if i.get('task_label', "None") != "None":
                    df.loc[index, i['task'] + '_task_label'] = i['task_label']
            if i.get('task_label', "not_combo") == "not_combo":
                if type(i['value']) is list:
                    # create a column for each dropdown value
                    count = 0
                    # iterate over cases where the values are a list
                    for dropdown in i['value']:
                        count += 1
                        df.loc[index, i['task'] + "_select_label" + "_" + str(count)] = dropdown['select_label']
                        if 'option' in dropdown:
                            df.loc[index, i['task'] + "_option" + "_" + str(count)] = dropdown['option']
                        if 'value' in dropdown:
                            df.loc[index, i['task'] + "_value" + "_" + str(count)] = dropdown['value']
                        if 'label' in dropdown:
                            df.loc[index, i['task'] + "_label" + "_" + str(count)] = dropdown['label']
            else:
                if type(i['value']) is list:
                    # create a column for each dropdown value
                    count = 0
                    for dropdown in i['value']:
                        count += 1
                        if type(dropdown['value']) is str:
                            df.loc[index, dropdown['task'] + "_value"] = dropdown['value']
                            df.loc[index, dropdown['task'] + "_task_label"] = dropdown['task_label']
                        elif type(dropdown['value']) is list:
                            val_count = 0
                            for val in dropdown['value']:
                                val_count += 1
                                df.loc[index, dropdown['task'] + "_select_label_" + str(val_count)] = val['select_label']
                                if 'option' in val:
                                    df.loc[index, dropdown['task'] + "_option_" + str(val_count)] = val['option']
                                if 'value' in val:
                                    df.loc[index, dropdown['task'] + "_value_" + str(val_count)] = val['value']
                                if 'label' in val:
                                    df.loc[index, dropdown['task'] + "_label_" + str(val_count)] = val['label']


def expandNFNClassifications(workflow_id, classifications_file, subjects_file):
    print("Reading classifications csv file for NfN...")
    df = pd.read_csv(classifications_file)
    df['subject_ids'] = df.subject_ids.map(lambda x: int(x.split(';')[0]))

    subjects_df = pd.read_csv(subjects_file)

    # expand only the workflows that we know how to expand
    df = df.loc[df.workflow_id == workflow_id, :]
    df.drop(['user_id', 'user_ip'], axis=1, inplace=True)

    # bring the last column to be the first
    cols = df.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    df = df[cols]

    subjects_df['locations_json'] = subjects_df.locations.map(lambda x: json.loads(x))
    subjects_df['locations'] = subjects_df.locations_json.apply(extract_json_value_loc)

    df = pd.merge(df, subjects_df[['subject_id', 'locations']], how='left', left_on='subject_ids', right_on='subject_id')

    # apply a json.loads function on the whole annotations column
    df['annotation_json'] = df['annotations'].map(lambda x: json.loads(x))

    # apply a json.loads function on the metadata column
    df['metadata_json'] = df['metadata'].map(lambda x: json.loads(x))

    # apply a json.loads function on the subject_data column
    df['subject_json'] = df['subject_data'].map(lambda x: json.loads(x))

    subject_keys = {}
    for subj in df['subject_json']:
        for val in iter(subj.values()):
            for k in val.keys():
                subject_keys[k] = 1
    for k in subject_keys.keys():
        df['subject_' + k] = df['subject_json'].apply(extract_json_value, column=k)

    df['classification_started_at'] = df['metadata_json'].apply(extract_json_date, column='started_at')
    df['classification_finished_at'] = df['metadata_json'].apply(extract_json_date, column='finished_at')

    extract_annotations(df)
    # delete the unnecessary columns
    df.drop(['annotation_json', 'metadata_json', 'subject_json', 'subject_id'], axis=1, inplace=True)

    # reordering the columns so that all the elements are grouped in the same task
    original_cols = list(df.ix[:, 0:df.columns.get_loc('classification_finished_at') + 1].columns.values)
    expanded_cols = list(df.ix[:, df.columns.get_loc('classification_finished_at') + 1:len(df.columns)].columns.values)

    sorted_cols = sorted(expanded_cols, key=lambda x: int(x[1:].split('_')[0]))

    df = df[original_cols + sorted_cols]

    print("The new columns:")
    print(df.columns.values)

    df.to_csv('expandedNfN_' + str(workflow_id) + '.csv', sep=',', index=False, encoding='utf-8')


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
    expandNFNClassifications(workflow_id, classifications_file, subjects_file)
