import sys
from importlib import util as i_util
from pathlib import Path

import inflect

E = inflect.engine()
E.defnoun("The", "All")
P = E.plural


def get_plugins(subdir):
    """Get plug-ins from a directory."""
    dir_ = Path(__file__).parent / subdir

    plugins = {}

    for path in [p for p in dir_.glob("*.py") if p.stem != "__init__"]:
        module_name = f"pylib.{subdir}.{path.name}"
        spec = i_util.spec_from_file_location(module_name, str(path))
        module = i_util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plugins[path.stem] = module

    return plugins


def error_exit(msgs):
    """Handle error exits."""
    msgs = msgs if isinstance(msgs, list) else [msgs]
    for msg in msgs:
        print(msg)
    sys.exit(1)
