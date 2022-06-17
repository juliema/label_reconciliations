import pandas as pd

from .. import util


def read(args):
    unreconciled = pd.read_csv(args.input_file, dtype=str)
    unreconciled = util.unreconciled_setup(args, unreconciled)

    return unreconciled, {}
