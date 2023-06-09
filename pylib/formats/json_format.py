import pandas as pd

from . import common_format


def read(args):
    df = pd.read_json(args.input_file)
    return common_format.read_table(args, df)
