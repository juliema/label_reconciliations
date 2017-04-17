"""Render a summary of the reconciliation process."""

import re
import sys
from datetime import datetime
import pandas as pd
from jinja2 import Environment, PackageLoader
import lib.util as util


class SummaryReport:
    """Render a summary of the reconciliation process."""

    user_column = 'user_name'

    # These depend on the patterns put into explanations_df
    no_match_pattern = r'^No (?:select|text) match on'
    exact_match_pattern = r'^(?:Exact|Normalized exact) match'
    fuzz_match_pattern = r'^(?:Partial|Token set) ratio match'
    all_blank_pattern = r'^(?:All|The) \d+ record'
    onesies_pattern = r'^Only 1 transcript in'

    def __init__(self, args, unreconciled_df, reconciled_df, explanations_df):
        self.args = args
        self.unreconciled_df = unreconciled_df
        self.reconciled_df = reconciled_df
        self.explanations_df = explanations_df

    def report(self):
        """Build the report from the template."""

        env = Environment(loader=PackageLoader('reconcile', '.'))
        template = env.get_template('lib/summary_report_template.html')

        merged_cols, merged_df = self.merge_dataframes()
        transcribers, transcriber_count = self.user_summary()

        with open('lib/d3/d3.min.js') as js_file:
            d3 = js_file.readlines()

        for _, group in merged_df:
            first = True
            for row in group.itertuples():
                if first and row.row_type != util.ROW_TYPES['explanations']:
                    print(row.subject_id, row.row_type)
                first = False

        summary = template.render(
            header=self.header_data(),
            row_types=util.ROW_TYPES,
            reconciled=self.reconciled_summary(),
            problems=self.problems(),
            transcribers=transcribers,
            transcriber_count=transcriber_count,
            options=[util.format_name(col)
                     for col in self.explanations_df.columns],
            merged_cols=merged_cols,
            merged_df=merged_df,
            d3=d3)

        with open(self.args.summary, 'w') as out_file:
            out_file.write(summary)

    def user_summary(self):
        """Get a list of users and how many transcriptions they did."""

        series = self.unreconciled_df.fillna('').groupby(self.user_column)
        series = series[self.user_column].count()
        series.sort_values(ascending=False, inplace=True)
        transcribers = [{'name': name, 'count': count}
                        for name, count in series.iteritems()]
        return transcribers, len(transcribers)

    def get_workflow_name(self):
        """Extract and format the workflow name from the dataframe."""

        try:
            workflow_name = self.unreconciled_df.workflow_name.iloc[0]
            workflow_name = re.sub(r'^[^_]*_', '', workflow_name)
        except KeyError:
            print('Workflow name not found in classifications file.')
            sys.exit(1)
        return workflow_name

    def header_data(self):
        """Data that goes into the report header."""

        workflow_name = self.get_workflow_name()
        return {
            'date': datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M'),
            'title': 'Summary of {}'.format(self.args.workflow_id),
            'ratio':
                self.unreconciled_df.shape[0] / self.reconciled_df.shape[0],
            'heading': 'Summary of "{}" ({})'.format(
                workflow_name, self.args.workflow_id),
            'subjects': self.reconciled_df.shape[0],
            'transcripts': self.unreconciled_df.shape[0],
            'workflow_name': workflow_name}

    def reconciled_summary(self):
        """Build a summary of how each field was reconciled."""

        reconciled = []
        for col in [c for c in self.explanations_df.columns]:

            col_type = 'text'
            if re.match(util.SELECT_COLUMN_PATTERN, col):
                col_type = 'select'

            num_fuzzy_match = ''
            if col_type == 'text':
                num_fuzzy_match = '{:,}'.format(self.explanations_df[
                    self.explanations_df[col].str.contains(
                        self.fuzz_match_pattern)].shape[0])

            num_no_match = self.explanations_df[
                self.explanations_df[col].str.contains(
                    self.no_match_pattern)].shape[0]

            reconciled.append({
                'name': util.format_name(col),
                'col_type': col_type,
                'num_no_match': num_no_match,
                'num_fuzzy_match': num_fuzzy_match,
                'num_reconciled': self.explanations_df.shape[0] - num_no_match,
                'num_exact_match': self.explanations_df[
                    self.explanations_df[col].str.contains(
                        self.exact_match_pattern)].shape[0],
                'num_all_blank': self.explanations_df[
                    self.explanations_df[col].str.contains(
                        self.all_blank_pattern)].shape[0],
                'num_onesies': self.explanations_df[
                    self.explanations_df[col].str.contains(
                        self.onesies_pattern)].shape[0]})
        return reconciled

    def merge_dataframes(self):
        """Combine the dataframes so that we can print them out in order for
        the detail report.
        """

        # Make subject_id a column
        rec_df = self.reconciled_df.reset_index()
        exp_df = self.explanations_df.reset_index()
        unr_df = self.unreconciled_df.copy()

        # We want the detail rows to come out in this order
        rec_df['row_type'] = util.ROW_TYPES['reconciled']
        exp_df['row_type'] = util.ROW_TYPES['explanations']
        unr_df['row_type'] = util.ROW_TYPES['unreconciled']

        # Merge and format the dataframes
        merged_df = pd.concat([exp_df, rec_df, unr_df]).fillna('')
        merged_df.sort_values(['subject_id', 'row_type', 'classification_id'],
                              inplace=True)
        merged_df = merged_df.astype(object)

        # Put the columns into this order and remove excess
        merged_cols = [rec_df.columns[0], 'classification_id']
        merged_cols.extend(rec_df.columns[1:])
        merged_df = merged_df.loc[:, merged_cols]
        merged_df.rename(columns={c: util.format_name(c) for c in merged_cols},
                         inplace=True)

        return merged_df.columns, merged_df.groupby(util.GROUP_BY)

    def problems(self):
        """Make a list of problems for each subject."""

        probs = {}
        pattern = '|'.join([self.no_match_pattern, self.onesies_pattern])
        for subject_id, cols in self.explanations_df.iterrows():
            probs[subject_id] = {}
            for col, value in cols.iteritems():
                if re.search(pattern, value):
                    probs[subject_id][util.format_name(col)] = 1
        return probs
