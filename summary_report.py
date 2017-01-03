"""Render a summary of the reconciliation process."""

import re
import sys
from datetime import datetime
import pandas as pd
from jinja2 import Environment, PackageLoader
import util

# These depend on the patterns put into explanations_df
NO_MATCH_PATTERN = r'^No (?:select|text) match on'
EXACT_MATCH_PATTERN = r'^(?:Exact|Normalized exact) match'
FUZZ_MATCH_PATTERN = r'^(?:Partial|Token set) ratio match'
ALL_BLANK_PATTERN = r'^(?:All|The) \d+ record'
ONESIES_PATTERN = r'^Only 1 transcript in'


def get_workflow_name(args, unreconciled_df):
    """Extract and format the workflow name from the dataframe."""
    try:
        workflow_name = unreconciled_df.loc[0, 'workflow_name']
        workflow_name = re.sub(r'^[^_]*_', '', workflow_name)
    except KeyError:
        print('Workflow ID {} not found in classifications file.'.format(args.workflow_id))
        sys.exit(1)
    return workflow_name


def header_data(args, reconciled_df, unreconciled_df):
    """Data that goes into the report header."""
    workflow_name = get_workflow_name(args, unreconciled_df)
    return {
        'date': datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M'),
        'title': 'Summary of {}'.format(args.workflow_id),
        'ratio': '{:.2f}'.format(unreconciled_df.shape[0] / reconciled_df.shape[0]),
        'heading': 'Summary of "{}" ({})'.format(workflow_name, args.workflow_id),
        'subjects': '{:,}'.format(reconciled_df.shape[0]),
        'transcripts': '{:,}'.format(unreconciled_df.shape[0]),
        'workflow_name': workflow_name,
    }


def reconciled_summary(explanations_df):
    """Build a summary of how each field was reconciled."""
    reconciled = []
    for col in [c for c in explanations_df.columns]:
        col_type = 'select' if re.match(util.SELECT_COLUMN_PATTERN, col) else 'text'
        num_no_match = explanations_df[explanations_df[col].str.contains(NO_MATCH_PATTERN)].shape[0]
        reconciled.append({
            'name': util.format_name(col),
            'col_type': col_type,
            'num_no_match': num_no_match,
            'num_exact_match': '{:,}'.format(
                explanations_df[explanations_df[col].str.contains(EXACT_MATCH_PATTERN)].shape[0]),
            'num_fuzzy_match': '{:,}'.format(explanations_df[explanations_df[col].str.contains(
                FUZZ_MATCH_PATTERN)].shape[0]) if col_type == 'text' else '',
            'num_all_blank': '{:,}'.format(
                explanations_df[explanations_df[col].str.contains(ALL_BLANK_PATTERN)].shape[0]),
            'num_onesies': '{:,}'.format(
                explanations_df[explanations_df[col].str.contains(ONESIES_PATTERN)].shape[0]),
            'num_reconciled': '{:,}'.format(explanations_df.shape[0] - num_no_match),
        })
    return reconciled


def merge_dataframes(unreconciled_df, reconciled_df, explanations_df):
    """Combine the dataframes so that we can print them out in order for the detail report."""

    # Make subject_id a column
    rec_df = reconciled_df.reset_index()
    exp_df = explanations_df.reset_index()
    unr_df = unreconciled_df.copy()

    # We want the detail rows to come out in this order
    rec_df['row_type'] = util.ROW_TYPES['reconciled']
    exp_df['row_type'] = util.ROW_TYPES['explanations']
    unr_df['row_type'] = util.ROW_TYPES['unreconciled']

    # Merge and format the dataframes
    merged_df = pd.concat([exp_df, rec_df, unr_df]).fillna('')
    merged_df.sort_values(['subject_id', 'row_type', 'classification_id'], inplace=True)
    merged_df = merged_df.astype(object)

    # Put the columns into this order and remove excess
    merged_cols = [rec_df.columns[0], 'classification_id']
    merged_cols.extend(rec_df.columns[1:])
    merged_df = merged_df.loc[:, merged_cols]
    merged_df.rename(columns={c: util.format_name(c) for c in merged_cols}, inplace=True)

    return merged_df.columns, merged_df.groupby(util.GROUP_BY)


def problems(explanations_df):
    """Make a list of problems for each subject."""
    probs = {}
    pattern = '|'.join([NO_MATCH_PATTERN, ONESIES_PATTERN])
    for subject_id, cols in explanations_df.iterrows():
        probs[subject_id] = {}
        for col, value in cols.iteritems():
            if re.search(pattern, value):
                probs[subject_id][util.format_name(col)] = 1
    return probs


def create_summary_report(unreconciled_df, reconciled_df, explanations_df, args):
    """Build the report from the template."""
    env = Environment(loader=PackageLoader('reconcile', '.'))
    template = env.get_template('summary_report_template.html')

    merged_cols, merged_df = merge_dataframes(unreconciled_df, reconciled_df, explanations_df)

    # pylint: disable=E1101
    summary = template.render(
        header=header_data(args, reconciled_df, unreconciled_df),
        row_types=util.ROW_TYPES,
        reconciled=reconciled_summary(explanations_df),
        problems=problems(explanations_df),
        options=[util.format_name(col) for col in explanations_df.columns],
        merged_cols=merged_cols,
        merged_df=merged_df)
    # pylint: enable=E1101

    with open(args.summary, 'w') as out_file:
        out_file.write(summary)
        # out_file.write(merged_df.to_html())  # Not flexible enuf
        # out_file.write('</section></body></html>')
