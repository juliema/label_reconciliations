"""Common utilities."""

import re
import sys

GROUP_BY = 'subject_id'                # We group on this column
COLUMN_PATTERN = r'^\d+T\d+[st]:\s*'   # Either a select or text column
SELECT_COLUMN_PATTERN = r'^\d+T\d+s:'  # How select columns are labeled
TEXT_COLUMN_PATTERN = r'^\d+T\d+t:'    # How text columns are labeled
ROW_TYPES = {  # Row types and their sort order
    'explanations': 'A',
    'reconciled': 'B',
    'unreconciled': 'C'}


def get_workflow_id(df, args):
    """Pull the workflow ID from the dataframe if it was not given."""

    if args.workflow_id:
        return args.workflow_id

    workflow_ids = df.workflow_id.unique()

    if len(workflow_ids) > 1:
        sys.exit('There are multiple workflows in this file. '
                 'You must provide a workflow ID as an argument.')

    return workflow_ids[0]


def format_header(header):
    """Remove tag ID and type flag from the column header."""

    header = re.sub(COLUMN_PATTERN, '', header)
    header = re.sub(r'\W', '_', header)
    header = re.sub(r'__+', '_', header)
    return header


def header_label(task_id, label, task_type, task_count):
    """Build a column header from the annotations json object. It contains
    flags for later processing and a tiebreaker (task_count) to handle
    duplicate task IDs.
    """

    label = '{:0>3}{}{:0>3}{}: {}_{}'.format(
        task_count, task_id[0], task_id[1:], task_type, label, task_count)
    return label
