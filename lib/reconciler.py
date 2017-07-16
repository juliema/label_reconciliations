"""Take the unreconciled data-frame and build the reconciled and explanations
data-frames.
"""

from functools import partial
import pandas as pd
import lib.util as util

NO_EXPLANATIONS = ['same']  # We may want these later


def build(args, unreconciled, column_types):
    """This function builds the reconciled and explanations data-frames."""

    plugins = util.get_plugins('column_types')
    reconcilers = {k: plugins[v['type']] for k, v in column_types.items()}

    # Get group and then reconcile the data
    aggregators = {r: partial(reconcilers[r].reconcile, args=args)
                   for r in reconcilers
                   if r in unreconciled.columns}
    reconciled = unreconciled.groupby(args.group_by).aggregate(aggregators)

    # Split combined value and explanation tuples into their own data frames
    explanations = pd.DataFrame()
    for column in reconciled.columns:
        reconciler = reconcilers.get(column)
        if reconciler:
            if column_types[column]['type'] not in NO_EXPLANATIONS:
                explanations[column] = reconciled[column].apply(lambda x: x[0])
            reconciled[column] = reconciled[column].apply(lambda x: x[1])

    return reconciled, explanations
