"""Common utilities."""

import sys
from importlib.machinery import SourceFileLoader
from glob import glob
from os.path import join, dirname, splitext, basename


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
    """Simple processing of the unreconciled data frame.

    Not used when there is a large amount of processing of the input.
    """
    unreconciled = unreconciled.fillna('')
    unreconciled.sort_values([args.group_by, args.key_column], inplace=True)
    return unreconciled


def sort_columns(args, all_columns, column_types):
    """Put columns into an order useful for displaying."""
    columns = [args.group_by, args.key_column]
    columns += [c['name'] for c
                in sorted(column_types.values(), key=lambda x: x['order'])]
    columns += [c for c in all_columns if c not in columns]
    return columns


def last_column_type(column_types):
    """Return the max order in the order types."""
    return max([v['order'] for v in column_types.values()], default=0)


def error_exit(msg):
    """Handle error exits."""
    if not isinstance(msg, list):
        msg = [msg]
    for m in msg:
        print(msg)
    sys.exit(1)
