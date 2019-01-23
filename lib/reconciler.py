"""Build reconciled and explanations dataframes from unreconciled dataframe."""

from functools import partial
import pandas as pd
import lib.util as util


NO_EXPLANATIONS = ['same']  # We may want these later


def build(args, unreconciled, column_types):
    """Build the reconciled and explanations data-frames."""
    plugins = util.get_plugins('column_types')
    reconcilers = {k: plugins[v['type']] for k, v in column_types.items()}

    # Get group and then reconcile the data
    aggregators = {r: partial(reconcilers[r].reconcile, args=args)
                   for r in reconcilers
                   if r in unreconciled.columns}

    # keep the userID associated with the data handed to the reconciler.
    reconciled = unreconciled.set_index(
        args.user_column, append=True).groupby(
            args.group_by).agg(aggregators, args)
    explanations = pd.DataFrame()
    for column in reconciled.columns:
        reconciler = reconcilers.get(column)
        if reconciler:
            if column_types[column]['type'] not in NO_EXPLANATIONS:
                explanations[column] = reconciled[column].apply(lambda x: x[0])
            reconciled[column] = reconciled[column].apply(lambda x: x[1])
    return reconciled, explanations
