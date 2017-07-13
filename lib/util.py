"""Common utilities."""

import re
import sys
import importlib
from glob import glob
from os.path import join, dirname, splitext, basename
import pandas as pd


GROUP_BY = 'subject_id'                # We group on this column
COLUMN_PATTERN = r'^\d+T\d+[st]:\s*'   # Either a select or text column
SELECT_COLUMN_PATTERN = r'^\d+T\d+s:'  # How select columns are labeled
TEXT_COLUMN_PATTERN = r'^\d+T\d+t:'    # How text columns are labeled
ROW_TYPES = {  # Row types and their sort order
    'explanations': 'A',
    'reconciled': 'B',
    'unreconciled': 'C'}


def get_plugins(subdir):
    """Get the plug-ins from the reconcilers directory."""

    pattern = join(dirname(__file__), subdir, '*.py')

    names = [splitext(basename(p))[0] for p in glob(pattern)
             if p.find('__init__') == -1]

    plugins = {}

    for name in names:
        module_name = 'lib.{}.{}'.format(subdir, name)
        spec = importlib.util.find_spec(module_name)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plugins[name] = module

    return plugins


def unreconciled_setup(args, unreconciled):
    """Simple processing of the unreconciled dataframe. This is not used
    when there is a large amount of processing of the input."""

    unreconciled = pd.read_csv(args.input)

    # Workflows must be processed individually
    workflow_id = get_workflow_id(unreconciled, args)

    # Remove anything not in the workflow
    unreconciled = unreconciled.loc[unreconciled.workflow_id == workflow_id, :]
    unreconciled = unreconciled.fillna('')

    unreconciled.sort_values([args.group_by, args.sort_by], inplace=True)

    return unreconciled


def get_workflow_id(df, args):
    """Pull the workflow ID from the data-frame if it was not given."""

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
