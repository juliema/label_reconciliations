import pandas as pd

from . import common


def read(args):
    df = pd.read_csv(args.input_file, dtype=str)
    return common.read_table(args, df)
