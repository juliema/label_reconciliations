"""Common utilities."""

import sys
from importlib.machinery import SourceFileLoader
from glob import glob
from os.path import join, dirname, splitext, basename

# pylint: disable=invalid-name


def get_plugins(subdir):
    """Get the plug-ins from the reconcilers directory."""

    pattern = join(dirname(__file__), subdir, '*.py')

    plugins = {}

    for path in glob(pattern):
        if path.find('__init__') > -1:
            continue
        name = splitext(basename(path))[0]
        module_name = 'lib.{}.{}'.format(subdir, name)
        module = SourceFileLoader(module_name, path).load_module()
        plugins[name] = module

    return plugins


def unreconciled_setup(args, unreconciled):
    """Simple processing of the unreconciled data frame. This is not used
    when there is a large amount of processing of the input."""

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


def last_column_type(column_types):
    """Return the max order in the order types."""

    return max([v['order'] for v in column_types.values()], default=0)
