import json

import pandas as pd

from pylib import cell
from pylib import utils


def build(args, raw_data, column_types):
    plugins = utils.get_plugins("column_types")
    converts = {
        k: getattr(plugins[v], "RAW_DATA_TYPE")
        for k, v in column_types.items()
        if hasattr(plugins[v], "RAW_DATA_TYPE")
    }

    dfs = []

    for col_name, col_series in raw_data.iteritems():
        convert = converts.get(col_name)
        if convert == "json":
            data = col_series.map(json.loads).tolist()
            data = [cell.rename(prefix=col_name, fields=f) for f in data]
            data = pd.json_normalize(data)
            dfs.append(data)
        else:
            dfs.append(col_series)

    unreconciled = pd.concat(dfs, axis="columns")
    unreconciled = format_data_frame(args, unreconciled, column_types)

    return unreconciled


def format_data_frame(args, unreconciled, column_types):
    """Sort and rename column headers and remove unwanted columns."""
    columns = [args.group_by, args.key_column]
    if args.user_column:
        columns += [args.user_column]

    unreconciled = cell.format_data_frame(columns, unreconciled, column_types)
    return unreconciled
