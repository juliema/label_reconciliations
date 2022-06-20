import importlib.util as i_util
import sys
from pathlib import Path

import inflect

E = inflect.engine()
E.defnoun("The", "All")
P = E.plural


def get_plugins(subdir):
    """Get plug-ins from a directory."""
    dir_ = Path(__file__).parent / subdir

    plugins = {}

    for path in [p for p in dir_.glob("*.py") if p.find("__init__") > -1]:
        module_name = f"lib.{subdir}.{path.name}"
        spec = i_util.spec_from_file_location(module_name, str(path))
        module = i_util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plugins[path.name] = module

    return plugins


def error_exit(msgs):
    """Handle error exits."""
    msgs = msgs if isinstance(msgs, list) else [msgs]
    for msg in msgs:
        print(msg)
    sys.exit(1)
