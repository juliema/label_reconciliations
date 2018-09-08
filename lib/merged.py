"""Merge reconciled, explanations, unreconciled dataframes into one."""

import pandas as pd
import lib.util as util


def merged_output(args, unreconciled, reconciled, explanations, column_types):
    """Output the merved dataframe."""
    merged_df = merge_df.merge(
        args, unreconciled, reconciled, explanations, column_types)
    merged_df.to_csv(args.merged, index=False)


def merge_df(args, unreconciled, reconciled, explanations, column_types):
    """
    Combine dataframes.

    Make sure they are grouped by subject ID. Also sort them within each
    subject ID group.
    """
    # Make the index a column
    rec = reconciled.reset_index()
    exp = explanations.reset_index()
    unr = unreconciled.astype(object).copy()

    # Sort by group-by then by row_type and then key-column
    rec['row_type'] = '1-reconciled'
    exp['row_type'] = '2-explanations'
    unr['row_type'] = '3-unreconciled'

    # Merge and format the dataframes
    merged = pd.concat([rec, exp, unr], sort=True)
    columns = util.sort_columns(args, merged.columns, column_types)
    return (merged.reindex(columns, axis=1)
                  .fillna('')
                  .sort_values([args.group_by, 'row_type', args.key_column]))

    return merged
