import pandas as pd

from . import common_format


def read(args):
    df = pd.read_csv(args.input_file, dtype=str)
    return common_format.read_table(args, df)
