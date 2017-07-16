"""Import a flat CSV file as unreconciled data."""

import pandas as pd
import lib.util as util


def read(args):
    """This is the main function that does the conversion."""

    unreconciled = pd.read_csv(args.input_file)
    unreconciled = util.unreconciled_setup(args, unreconciled)

    return unreconciled, {}
