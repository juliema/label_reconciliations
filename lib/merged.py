"""Merge the three dataframes: reconciled, explanations, unreconciled into one
dataframe."""

import pandas as pd
import lib.util as util

ROW_TYPES = {  # Row types and their sort order
    'reconciled': 'A',
    'explanations': 'B',
    'unreconciled': 'C'}


def merge(
        args, unreconciled, reconciled, explanations, column_types):
    """Combine the dataframes so that we can print them out in order for
    the detail report.
    """

    # Make the index a column
    rec = reconciled.reset_index()
    exp = explanations.reset_index()
    unr = unreconciled.astype(object).copy()

    # Sort by group-by then by row_type and then key-column
    rec['row_type'] = ROW_TYPES['reconciled']
    exp['row_type'] = ROW_TYPES['explanations']
    unr['row_type'] = ROW_TYPES['unreconciled']

    # Merge and format the dataframes
    merged = pd.concat([rec, exp, unr])
    columns = util.sort_columns(args, merged, column_types)
    merged = merged.reindex_axis(columns, axis=1).fillna('')
    merged.sort_values(
        [args.group_by, 'row_type', args.key_column], inplace=True)

    return merged
