"""Format and output the reconciled dataframe."""
import lib.column_types
import lib.util as util


def reconciled_output(args, reconciled, column_types):
    columns = lib.column_types.sort_columns(args, reconciled.columns, column_types)
    del columns[0]
    del columns[0]
    del columns[0]
    reconciled = reconciled.reindex(columns, axis="columns").fillna("")

    plugins = util.get_plugins("column_types")
    for _, plugin in plugins.items():
        if hasattr(plugin, "adjust_reconciled_columns"):
            reconciled = plugin.adjust_reconciled_columns(reconciled, column_types)

    reconciled.to_csv(args.reconciled)

    return reconciled
