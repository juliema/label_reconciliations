"""Common utilities."""

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

    unreconciled = unreconciled.fillna('')
    unreconciled.sort_values([args.group_by, args.key_column], inplace=True)
    return unreconciled


def sort_columns(args, df, column_types):
    """Put columns into an order useful for displaying."""

    columns = [args.group_by, args.key_column]
    columns.extend([v['name'] for v
                    in sorted(column_types.values(),
                              key=lambda x: x['order'])])
    columns.extend([c for c in df.columns
                    if c not in columns and c not in ['row_type']])

    # TODO: Delete this
    if 'row_type' in df.columns:
        columns.append('row_type')

    return columns


def last_column_type(column_types):
    """Return the max order in the order types."""

    return max([v['order'] for v in column_types.values()], default=0)
