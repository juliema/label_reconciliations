"""Common utilities."""

import sys
import importlib
from glob import glob
from os.path import join, dirname, splitext, basename
import pandas as pd


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
    """Simple processing of the unreconciled data frame. This is not used
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

    workflow_ids = df[args.workflow_id_column].unique()

    if len(workflow_ids) > 1:
        sys.exit('There are multiple workflows in this file. '
                 'You must provide a workflow ID as an argument.')

    return workflow_ids[0]


def sort_columns(args, df, column_types):
    """Put columns into an order useful for displaying."""

    columns = [args.group_by, args.sort_by]
    columns.extend([v['name'] for v
                    in sorted(column_types.values(),
                              key=lambda x: x['order'])])
    columns.extend([c for c in df.columns
                    if c not in columns and c not in ['row_type']])
    if 'row_type' in df.columns:
        columns.append('row_type')

    return df.reindex_axis(columns, axis=1)
