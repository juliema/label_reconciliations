"""Take the unreconciled dataframe and build the reconciled and explanations dataframes."""

import re
from functools import reduce
from collections import Counter, namedtuple
from itertools import combinations
from fuzzywuzzy import fuzz
import util

ARGS = None
PLACE_HOLDERS = ['placeholder']  # Replace these placeholders with an empty string

ExactScore = namedtuple('ExactScore', 'value count')
FuzzyRatioScore = namedtuple('FuzzyRatioScore', 'score value')
FuzzySetScore = namedtuple('FuzzySetScore', 'score value tokens')

UNWANTED_COLUMNS = ['subject_data', 'subject_retired', 'subject_subjectId']


def normalize_text(group):
    """Collapse space into one space and EOLs into one EOL."""
    return ['\n'.join([' '.join(ln.split()) for ln in str(g).splitlines()]) for g in group]


def top_partial_ratio(values):
    """Return the best partial ratio match from fuzzywuzzy module."""
    scores = []
    for combo in combinations(values, 2):
        score = fuzz.partial_ratio(combo[0], combo[1])
        value = combo[0] if len(combo[0]) >= len(combo[1]) else combo[1]
        scores.append(FuzzyRatioScore(score, value))
    scores = sorted(scores,
                    reverse=True,
                    key=lambda s: '{:0>6} {:0>6}'.format(s.score, len(s.value)))
    return scores[0]


def top_token_set_ratio(values):
    """Return the best token set ratio match from fuzzywuzzy module."""
    scores = []
    for combo in combinations(values, 2):
        score = fuzz.token_set_ratio(combo[0], combo[1])
        tokens_0 = len(combo[0].split())
        tokens_1 = len(combo[1].split())
        if tokens_0 > tokens_1:
            value = combo[0]
            tokens = tokens_0
        elif tokens_0 < tokens_1:
            value = combo[1]
            tokens = tokens_1
        else:
            tokens = tokens_0
            value = combo[0] if len(combo[0]) <= len(combo[1]) else combo[1]
        scores.append(FuzzySetScore(score, value, tokens))
    ordered = sorted(scores, reverse=True,
                     key=lambda s: '{:0>6} {:0>6} {:0>6}'.format(
                         s.score, s.tokens, 1000000 - len(s.value)))
    return ordered[0]


def all_are_identical(group):
    """Handle a group where all of the items are identical."""
    values = [g for g in group]
    return values[0]


def explain_values(values, filled):
    """Get group values used in the best choice explanations."""
    record_count = len(values)
    blank_count = record_count - reduce((lambda x, y: x + y.count), filled, 0)
    return record_count, blank_count


TOTAL_PLURALS = {'records': 'records', 'All': 'All', 'are': 'are'}
TOTAL_SINGULARS = {'records': 'record', 'All': 'The', 'are': 'is'}
BLANK_PLURALS = {'blanks': 'blanks'}
BLANK_SINGULARS = {'blanks': 'blank'}


# pylint: disable=too-many-arguments
def format_explanation(form, record_count=None, blank_count=None,
                       match_count=None, match_type=None, score=None):
    """Build an explaination for the group's best choice."""
    std_words = dict(record_count=record_count, blank_count=blank_count,
                     match_count=match_count, match_type=match_type, score=score)
    total_words = TOTAL_SINGULARS.copy() if record_count == 1 else TOTAL_PLURALS.copy()
    blank_words = BLANK_SINGULARS.copy() if blank_count == 1 else BLANK_PLURALS.copy()
    words = dict(list(total_words.items()) + list(blank_words.items()) + list(std_words.items()))
    return form.format(**words)
# pylint: enable=too-many-arguments


def explain_all_blank(values):
    """Explain case where all values in the group are blank."""
    record_count = len(values)
    return (format_explanation('{All} {record_count} {records} {are} blank',
                               record_count=record_count), '')


def explain_one_transcript(value, values, filled):
    """Explain the case where one value in the group is filled and all others are blank."""
    record_count, _ = explain_values(values, filled)
    form = 'Only 1 transcript in {record_count} {records}'
    return (format_explanation(form, record_count=record_count), value)


def explain_no_match(values, filled, match_type):
    """Explain when we are unable to match any value in the group."""
    record_count, blank_count = explain_values(values, filled)
    form = 'No {match_type} match on {record_count} {records} with {blank_count} {blanks}'
    return (format_explanation(form, record_count=record_count,
                               blank_count=blank_count, match_type=match_type), '')


def explain_exact_match(value, values, filled, match_type):
    """Explain when we have an exact match between items in the group."""
    record_count, blank_count = explain_values(values, filled)
    form = ('{match_type} match, {match_count} of {record_count} '
            '{records} with {blank_count} {blanks}')
    return (format_explanation(form, record_count=record_count, match_count=filled[0].count,
                               blank_count=blank_count, match_type=match_type), value)


def explain_fuzzy_match(value, values, filled, score, match_type):
    """Explain the case where we do a fuzzy match on the group."""
    record_count, blank_count = explain_values(values, filled)
    form = ('{match_type} match on {record_count} {records} '
            'with {blank_count} {blanks}, score={score}')
    return (format_explanation(form, record_count=record_count, blank_count=blank_count,
                               match_type=match_type, score=score), value)


def only_filled_values(values):
    """Get the items in the group where they are filled and sort by frequency."""
    return [ExactScore(cnt[0], cnt[1]) for cnt in Counter([v for v in values if v]).most_common()]


def best_select_value(group):
    """Handle the case where the group is for a drop-down select list."""
    values = [str(g) if str(g).lower() not in PLACE_HOLDERS else '' for g in group]
    filled = only_filled_values(values)

    if not filled:
        return explain_all_blank(values)

    if filled[0].count > 1:
        return explain_exact_match(filled[0].value, values, filled, 'Exact')

    if len(filled) == 1:
        return explain_one_transcript(filled[0].value, values, filled)

    return explain_no_match(values, filled, 'select')


def best_text_value(group):
    """Handle the case where the group is a free-form text field."""
    values = normalize_text(group)
    filled = only_filled_values(values)

    if not filled:
        return explain_all_blank(values)

    if filled[0].count > 1:
        return explain_exact_match(filled[0].value, values, filled, 'Normalized exact')

    if len(filled) == 1:
        return explain_one_transcript(filled[0].value, values, filled)

    # Check for simple inplace fuzzy matches
    top = top_partial_ratio(values)
    if top.score >= ARGS.fuzzy_ratio_threshold:
        return explain_fuzzy_match(top.value, values, filled, top.score, 'Partial ratio')

    # Now look for the best token match
    top = top_token_set_ratio(values)
    if top.score >= ARGS.fuzzy_set_threshold:
        return explain_fuzzy_match(top.value, values, filled, top.score, 'Token set ratio')

    return explain_no_match(values, filled, 'text')


def create_reconciled_dataframes(unreconciled_df, args):
    """This is the function called by external modules."""
    # pylint: disable=global-statement
    global ARGS  # We need these values in a function where we don't controll the signature.
    # pylint: enable=global-statement
    ARGS = args

    # How to aggregate columns based on each column's type which is determined by the column name
    method_for_select_columns = {col: best_select_value for col in unreconciled_df.columns
                                 if re.match(util.SELECT_COLUMN_PATTERN, col)}
    method_for_text_columns = {col: best_text_value for col in unreconciled_df.columns
                               if re.match(util.TEXT_COLUMN_PATTERN, col)}
    method_for_subject_columns = {col: all_are_identical for col in unreconciled_df.columns
                                  if col.startswith('subject_') and col != util.GROUP_BY}

    best_value_methods = method_for_select_columns.copy()
    best_value_methods.update(method_for_text_columns)
    best_value_methods.update(method_for_subject_columns)

    best_value_methods = {k: v for k, v in best_value_methods.items()
                          if k not in UNWANTED_COLUMNS}  # Remove junk

    # Aggregate using the per column functions setup above
    reconciled_df = unreconciled_df.fillna('').groupby(util.GROUP_BY).aggregate(best_value_methods)

    # Split the combined reconciled value and explanation tuple into separate columns
    for col in list(method_for_text_columns.keys()) + list(method_for_select_columns.keys()):
        reconciled_df[col + '_explanation'] = reconciled_df[col].apply(lambda t: t[0])
        reconciled_df[col] = reconciled_df[col].apply(lambda t: t[1])

    reconciled_df = reconciled_df.reindex_axis(sorted(reconciled_df.columns), axis=1)

    explanations_df = reconciled_df.loc[:, [col for col in reconciled_df.columns
                                            if col.endswith('_explanation')]]
    explanations_cols = {col: col.replace('_explanation', '') for col in explanations_df.columns}
    explanations_df.rename(columns=explanations_cols, inplace=True)

    reconciled_df.drop([col for col in reconciled_df.columns if col.endswith('_explanation')],
                       axis=1, inplace=True)

    return reconciled_df, explanations_df
