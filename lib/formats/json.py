"""Import a flat JSON file as unreconciled data."""

import pandas as pd
import lib.util as util


def read(args):
    """Read a JSON file into a data-frame."""
    unreconciled = pd.read_json(args.input_file)
    unreconciled = util.unreconciled_setup(args, unreconciled)

    return unreconciled, {}
