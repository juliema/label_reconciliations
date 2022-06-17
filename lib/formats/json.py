import pandas as pd

from .. import util


def read(args):
    unreconciled = pd.read_json(args.input_file)
    unreconciled = util.unreconciled_setup(args, unreconciled)

    return unreconciled, {}
