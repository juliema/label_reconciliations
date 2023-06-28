import sys
from collections import namedtuple
from importlib import util as i_util
from pathlib import Path
from types import ModuleType

import inflect

E = inflect.engine()
E.defnoun("The", "All")
P = E.plural

Point = namedtuple("Point", "x y")


def get_plugins(subdir) -> dict[str, ModuleType]:
    """Get plug-ins from a directory."""
    dir_ = Path(__file__).parent / subdir

    plugins = {}

    exclude = ["__init__", "common"]

    for path in [p for p in dir_.glob("*.py") if p.stem not in exclude]:
        module_name = f"pylib.{subdir}.{path.name}"
        spec = i_util.spec_from_file_location(module_name, str(path))
        if spec is None:
            error_exit(f"Could not find spec '{spec}'")
        module = i_util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plugins[path.stem] = module

    return plugins


def error_exit(msgs):
    msgs = msgs if isinstance(msgs, list) else [msgs]
    for msg in msgs:
        print(msg, file=sys.stderr)
    sys.exit(1)
