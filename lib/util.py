import importlib.util as i_util
import sys
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext

import inflect

E = inflect.engine()
E.defnoun("The", "All")
P = E.plural


def get_plugins(subdir):
    """Get plug-ins from a directory."""
    pattern = join(dirname(__file__), subdir, "*.py")

    plugins = {}

    for path in glob(pattern):
        if path.find("__init__") > -1:
            continue
        name = splitext(basename(path))[0]
        module_name = f"lib.{subdir}.{name}"
        spec = i_util.spec_from_file_location(module_name, path)
        module = i_util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plugins[name] = module

    return plugins


def unreconciled_setup(args, unreconciled):
    """
    Process the unreconciled data frame.

    Not used when there is a large amount of processing of the input.
    """
    unreconciled = unreconciled.fillna("")
    unreconciled = unreconciled.sort_values([args.group_by, args.key_column])
    return unreconciled


def error_exit(msgs):
    """Handle error exits."""
    msgs = msgs if isinstance(msgs, list) else [msgs]
    for msg in msgs:
        print(msg)
    sys.exit(1)
