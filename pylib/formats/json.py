import pandas as pd

from . import common


def read(args):
    df = pd.read_json(args.input_file)
    return common.read_table(args, df)
