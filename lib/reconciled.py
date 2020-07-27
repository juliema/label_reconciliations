"""Format and output the reconciled dataframe."""

import lib.util as util

EXPLANATION_SUFFIX = ' Explanation'


def reconciled_output(
        args, unreconciled, reconciled, explanations, column_types):
    """
    Output the reconciled based upon the given arguments.

    1) Split any mmr columns into individual columns for Mean, Mode, and Range.

    2) If the --explanations option is selected then add an
       explanations column for every output column just after the reconciled
       output.

    3) If the --transcribers option is selected then add two columns
       for every user. One for the user name and one for the value entered.
    """
    columns = util.sort_columns(args, reconciled.columns, column_types)
    del columns[0]
    del columns[0]
    del columns[0]
    reconciled = reconciled.reindex(columns, axis='columns').fillna('')

    plugins = util.get_plugins('column_types')
    for _, plugin in plugins.items():
        if hasattr(plugin, 'adjust_reconciled_columns'):
            reconciled = plugin.adjust_reconciled_columns(
                reconciled, column_types)

    if args.explanations:
        reconciled = add_explanations(reconciled, explanations, column_types)

    if args.transcribers:
        reconciled = add_transcribers(reconciled, unreconciled, column_types)

    reconciled.to_csv(args.reconciled)

    return reconciled


def add_explanations(reconciled, explanations, column_types):
    """Add explanation columns just after the reconciled value columns."""
    reconciled = reconciled.join(explanations, rsuffix=EXPLANATION_SUFFIX)

    transcribed = {c for c in reconciled.columns
                   if column_types.get(c, {'type': 'same'})['type'] != 'same'}

    moves = []
    for column in transcribed:
        moves.append(column)
        _append_column(reconciled, moves, column + EXPLANATION_SUFFIX)
    others = [c for c in reconciled.columns if c not in moves]

    return reconciled.reindex(moves + others, axis='columns')


def add_transcribers(reconciled, unreconciled, column_types):
    """Add user input columns just after the reconciled value columns."""
    columns = {'subject_id', 'user_name'}
    columns |= {c for c in unreconciled.columns
                if column_types.get(c, {'type': 'same'})['type'] != 'same'}
    drops = [c for c in unreconciled.columns if c not in columns]
    unreconciled = unreconciled.drop(drops, axis='columns')
    unreconciled['transcriber'] = unreconciled.groupby('subject_id').cumcount()
    unreconciled.transcriber += 1
    max_transcriber = unreconciled.transcriber.max() + 1
    columns -= {'subject_id'}

    unreconciled = unreconciled.pivot(
        index='subject_id', columns='transcriber', values=list(columns))
    renames = [f'{x} {i}'
               for x in unreconciled.columns.levels[0]
               for i in unreconciled.columns.levels[1]]
    unreconciled.columns = renames
    reconciled = reconciled.join(unreconciled, rsuffix=' Transcriber')

    transcribed = {c for c in reconciled.columns
                   if column_types.get(c, {'type': 'same'})['type'] != 'same'}

    moves = []
    for column in transcribed:
        moves.append(column)
        _append_column(reconciled, moves, column + EXPLANATION_SUFFIX)
        for i in range(1, max_transcriber):
            _append_column(reconciled, moves, f'user_name {i}')
            _append_column(reconciled, moves, f'{column} {i}')

    others = [c for c in reconciled.columns if c not in moves]
    return reconciled.reindex(moves + others, axis='columns')


def _append_column(reconciled, columns, name):
    if name not in columns and name in reconciled.columns:
        columns.append(name)
