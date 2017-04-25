"""This module builds up the data used to reconcile the data later."""

import re
import sys
import json
import dateutil
import pandas as pd
import lib.util as util


class UnreconciledBuilder:
    """Build the unreconciled dataframe from the raw CSV file."""

    select_column_flag = 's'  # Flag a select column
    text_column_flag = 't'    # Flag a text column

    def __init__(self, workflow_id, classifications_file):
        self.classifications_file = classifications_file  # File being parsed
        self.workflow_id = workflow_id  # Workflow extracted from CSV file
        self.df = None                  # Dataframe being built

    def build(self):
        """This is the main function called by external modules."""

        self.df = pd.read_csv(self.classifications_file)
        workflow_id = self.get_workflow_id(self.workflow_id)

        # We need to do this by workflow because each workflow's annotations
        # may have a different structure
        self.df = self.df.loc[self.df.workflow_id == workflow_id, :]

        # bring the last column to be the first
        cols = self.df.columns.tolist()
        cols = cols[-1:] + cols[:-1]
        self.df = self.df[cols]

        # Make key data types match in the two data frames
        self.df['subject_ids'] = \
            self.df.subject_ids.map(lambda x: int(str(x).split(';')[0]))

        self.extract_metata_json()
        self.extract_annotations_json()
        self.extract_subject_json()

        if 'subject_id' in self.df.columns:
            self.df.rename(
                columns={'subject_id': 'subject_id_external'}, inplace=True)
        self.df.drop(['user_id', 'user_ip'], axis=1, inplace=True)
        self.rename_columns()
        self.df.sort_values(['subject_id', 'classification_id'], inplace=True)

        return self.df

    def get_workflow_id(self, workflow_id):
        """Pull the workflow ID from the dataframe if it was not given."""

        if workflow_id:
            return workflow_id
        workflow_ids = self.df.workflow_id.unique()
        if len(workflow_ids) > 1:
            print('There are multiple workflows in this file. '
                  'You must provide a workflow ID')
            sys.exit(1)
        return workflow_ids[0]

    def extract_metata_json(self):
        """Hoist desired metadata data into the data frame."""

        self.df['metadata_json'] = self.df['metadata'].map(json.loads)
        self.df['classification_started_at'] = self.df['metadata_json'].apply(
            self.extract_json_date, column='started_at')
        self.df['classification_finished_at'] = self.df['metadata_json'].apply(
            self.extract_json_date, column='finished_at')
        self.df.drop('metadata_json', axis=1, inplace=True)

    def extract_annotations_json(self):
        """Extract annotations from a json object. Annotations are a deeply
        nested json blob with a peculiar data format. We use this function to
        gather the data type so that we can hoist the data later on.
        """

        self.df['annotation_json'] = self.df['annotations'].map(json.loads)
        for index, row in self.df.iterrows():
            task_count = 0
            for task in row['annotation_json']:
                task_id = task['task']
                task_count += 1
                try:
                    task_count = self.extract_an_annotaion(
                        task, task_id, index, task_count)
                except ValueError:
                    print('Bad transcription for classification {}'.format(
                        row['classification_id']))
                    break
        self.df.drop('annotation_json', axis=1, inplace=True)

    def extract_an_annotaion(self, task, task_id, index, task_count):
        """Hoists an annotation field into the data frame."""

        if isinstance(task.get('value'), list):
            for subtask in task['value']:
                subtask_id = subtask.get('task', task_id)
                task_count += 1
                task_count = self.extract_an_annotaion(
                    subtask, subtask_id, index, task_count)
        elif task.get('select_label'):
            header = util.header_label(task_id,
                                       task['select_label'],
                                       self.select_column_flag,
                                       task_count)
            value = task.get('label')
            self.df.loc[index, header] = value
        elif task.get('task_label'):
            header = util.header_label(task_id,
                                       task['task_label'],
                                       self.text_column_flag,
                                       task_count)
            value = task.get('value')
            self.df.loc[index, header] = value
        else:
            raise ValueError()

        return task_count

    def extract_subject_json(self):
        """Hoist the subject data into the data frame. We also have to handle
        duplicate task names with a tiebreaker.
        """

        self.df['subject_json'] = self.df['subject_data'].map(json.loads)
        subject_keys = {}
        for subj in self.df['subject_json']:
            for val in iter(subj.values()):
                for k in val.keys():
                    subject_keys[k] = 1
        for k in subject_keys:
            self.df['subject_' + k] = self.df['subject_json'].apply(
                self.extract_json_value, column=k)
        self.df.drop('subject_json', axis=1, inplace=True)

    @staticmethod
    def extract_json_value(subject_json, column=''):
        """Pull a field out of a json object and put it into its own column
        (as a string value).
        """

        if column in list(subject_json.values())[0]:
            return list(subject_json.values())[0][column]

    @staticmethod
    def extract_json_date(metadata_json, column=''):
        """Extract dates from a json object."""

        return dateutil.parser.parse(metadata_json[column]).strftime(
            '%d-%b-%Y %H:%M:%S')

    def rename_columns(self):
        """Change column names for readablity.
        Rename subject_ids to subject_id.
        Rename duplicate tasks to replace the column count with a group number.
        """

        renames = {}
        tasks = {}

        # Get all tasks and their associated columns
        for column in self.df.columns:
            if re.match(util.COLUMN_PATTERN, column):
                task = util.format_header(column)
                task = re.sub(r'_\d+$', '', task)
                if task not in tasks:
                    tasks[task] = []
                tasks[task].append(column)

        # Get new columns names
        for task, columns in tasks.items():
            if len(columns) > 1:
                for i, column in enumerate(columns, 1):
                    renames[column] = re.sub(r'\d+$', str(i), column)
            else:
                column = columns[0]
                renames[column] = re.sub(r'_\d+$', '', column)

        renames['subject_ids'] = 'subject_id'

        self.df.rename(columns=renames, inplace=True)
