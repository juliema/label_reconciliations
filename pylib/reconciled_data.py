import pandas as pd

from pylib import cell
from pylib import utils


def build(args, raw_data, column_types):
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

    grouped = raw_data.groupby(args.group_by)

    reconciled = []
    for group_by, group_df in grouped:
        reconciled_row = {args.group_by: group_by}

        for col_name in group_df.columns:

            if module := reconcilers.get(col_name):
                fields = module.reconcile(group_df[col_name], args)

                # "reconcile()" will return generic column names. This will make them
                # specific by prepending the true column name to the generic one
                reconciled_row |= cell.rename(prefix=col_name, fields=fields)

        # Process the whole row because some values depend on values in other columns
        for row_reconciler in row_reconcilers.keys():
            row_reconciler.reconcile_row(reconciled_row)

        reconciled.append(reconciled_row)

    reconciled = pd.DataFrame(reconciled)
    reconciled = format_data_frame(args, reconciled, column_types)
    return reconciled


def format_data_frame(args, reconciled, column_types):
    """Sort and rename column headers and remove unwanted columns."""
    columns = [args.group_by]
    reconciled = cell.format_data_frame(columns, reconciled, column_types)
    return reconciled


def output_csv(args, reconciled):
    unwanted = [c for c in reconciled.columns if c.split()[-1] in ["note", "flag"]]
    reconciled = reconciled.drop(unwanted, axis="columns")
    reconciled.to_csv(args.reconciled, index=False)
