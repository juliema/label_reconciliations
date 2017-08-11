"""Import a flat CSV file as unreconciled data."""

import pandas as pd
import lib.util as util


def read(args):
    """Import a CSV file into a data-frame."""
    unreconciled = pd.read_csv(args.input_file, dtype=str)
    unreconciled = util.unreconciled_setup(args, unreconciled)

    return unreconciled, {}
