"""Render a summary of the reconciliation process."""

import re
import sys
from datetime import datetime
from jinja2 import Environment, PackageLoader
import utils

# These depend on the patterns put into explanations_df FIXME
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
        col_type = 'select' if re.match(utils.SELECT_COLUMN_PATTERN, col) else 'text'
        num_no_match = explanations_df[explanations_df[col].str.contains(NO_MATCH_PATTERN)].shape[0]
        reconciled.append({
            'name': utils.format_name(col),
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


def problem_thead_data(explanations_df):
    """Get the header fields for the problem summary of each subject."""
    problem_thead = []
    problem_thead.append(explanations_df.index.name)
    for col in explanations_df.columns:
        problem_thead.append(utils.format_name(col))
    return problem_thead


def problem_tbody_data(explanations_df):
    """Get the data fields for the problem summary of each subject."""
    problem_tbody = []
    pattern = '|'.join([NO_MATCH_PATTERN, ONESIES_PATTERN])
    for subject_id, cols in explanations_df.iterrows():
        trow = []
        trow.append(str(subject_id))
        keep = False
        for col in cols:
            tdata = ''
            if re.search(pattern, col):
                keep = True
                tdata = col
            trow.append(tdata)
        if keep:
            problem_tbody.append(trow)
    return problem_tbody


def create_summary_report(unreconciled_df, reconciled_df, explanations_df, args):
    """Build the report from the template."""
    env = Environment(loader=PackageLoader('reconcile', '.'))
    template = env.get_template('summary_report_template.html')
    # pylint: disable=E1101
    summary = template.render(header=header_data(args, reconciled_df, unreconciled_df),
                              reconciled=reconciled_summary(explanations_df),
                              problem_thead=problem_thead_data(explanations_df),
                              problem_tbody=problem_tbody_data(explanations_df))
    # pylint: enable=E1101

    with open(args.summary, 'w') as out_file:
        out_file.write(summary)
