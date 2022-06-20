import pandas as pd

from pylib import utils
from pylib.cell import rename


def build(args, unreconciled, column_types):
    plugins = utils.get_plugins("column_types")
    reconcilers = {
        k: plugins[v]
        for k, v in column_types.items()
        if hasattr(plugins[v], "reconcile")
    }
    row_reconcilers = {
        plugins[v]: 1
        for k, v in column_types.items()
        if hasattr(plugins[v], "reconcile_row")
    }

    unreconciled = unreconciled.sort_values([args.group_by, args.key_column])
    grouped = unreconciled.groupby(args.group_by)

    rows = []
    for group_by, group_df in grouped:
        reconciled_row = {args.group_by: group_by}

        for col_type in group_df.columns:

            if module := reconcilers.get(col_type):
                fields = module.reconcile(group_df[col_type], args)
                reconciled_row |= rename(prefix=col_type, fields=fields)

        # Process the whole row because some values depend on values in other columns
        for row_reconciler in row_reconcilers.keys():
            row_reconciler.reconcile_row(reconciled_row)

        rows.append(reconciled_row)

    rows = pd.DataFrame(rows)
    sort_columns(rows)
    print(rows)
    return rows


def sort_columns(df):
    return df
