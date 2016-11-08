import re
from functools import reduce
from collections import Counter, namedtuple
from itertools import combinations
from fuzzywuzzy import fuzz
import utils

ARGS = None
PLACE_HOLDERS = ['placeholder']  # Replace these placeholders with an empty string
GROUP_BY = 'subject_id'          # We group on this column
SEPARATOR = ':'                  # Used to separate match flags from values TODO use namedtuple


ExactScore = namedtuple('ExactScore', 'value count')
FuzzyRatioScore = namedtuple('FuzzyRatioScore', 'score value')
FuzzySetScore = namedtuple('FuzzySetScore', 'score value tokens')
ReconciledValue = namedtuple('ReconciledValue', 'flag best_value')

UNWANTED_COLUMNS = ['subject_data', 'subject_retired', 'subject_subjectId']


def normalize_text(group):
    return ['\n'.join([' '.join(ln.split()) for ln in g.splitlines()]) for g in group]


def top_partial_ratio(group):
    scores = []
    for c in combinations(group, 2):
        score = fuzz.partial_ratio(c[0], c[1])
        value = c[0] if len(c[0]) >= len(c[1]) else c[1]
        scores.append(FuzzyRatioScore(score, value))
    scores = sorted(scores, reverse=True, key=lambda s: '{:0>6} {:0>6}'.format(s.score, len(s.value)))
    return scores[0]


def top_token_set_ratio(group):
    scores = []
    for c in combinations(group, 2):
        score = fuzz.token_set_ratio(c[0], c[1])
        tokens_0 = len(c[0].split())
        tokens_1 = len(c[1].split())
        if tokens_0 > tokens_1:
            value = c[0]
            tokens = tokens_0
        elif tokens_0 < tokens_1:
            value = c[1]
            tokens = tokens_1
        else:
            tokens = tokens_0
            value = c[0] if len(c[0]) <= len(c[1]) else c[1]
        scores.append(FuzzySetScore(score, value, tokens))
    ordered = sorted(scores, reverse=True,
                     key=lambda s: '{:0>6} {:0>6} {:0>6}'.format(s.score, s.tokens, 1000000 - len(s.value)))
    return ordered[0]


def all_are_identical(group):
    values = [g for g in group]
    return values[0]


def explain_values(values, filled):
    record_count = len(values)
    blank_count = record_count - reduce((lambda x, y: x + y.count), filled, 0)
    return record_count, blank_count


TOTAL_PLURALS = {'records': 'records', 'All': 'All', 'are': 'are'}
TOTAL_SINGULARS = {'records': 'record', 'All': 'The', 'are': 'is'}
BLANK_PLURALS = {'blanks': 'blanks'}
BLANK_SINGULARS = {'blanks': 'blank'}


def format_explanation(form, value='', record_count=None, blank_count=None,
                       match_count=None, match_type=None, score=None):
    form += '{separator}{value}'
    std_words = dict(value=value, separator=SEPARATOR, record_count=record_count, blank_count=blank_count,
                     match_count=match_count, match_type=match_type, score=score)
    total_words = TOTAL_SINGULARS.copy() if record_count == 1 else TOTAL_PLURALS.copy()
    blank_words = BLANK_SINGULARS.copy() if blank_count == 1 else BLANK_PLURALS.copy()
    words = dict(list(total_words.items()) + list(blank_words.items()) + list(std_words.items()))
    return form.format(**words)


def explain_all_blank(values):
    record_count = len(values)
    return format_explanation('{All} {record_count} {records} {are} blank', record_count=record_count)


def explain_one_transcript(value, values, filled):
    record_count, blank_count = explain_values(values, filled)
    form = 'Only 1 transcript in {record_count} {records}'
    return format_explanation(form, value=value, record_count=record_count)


def explain_no_match(values, filled, match_type):
    record_count, blank_count = explain_values(values, filled)
    form = 'No {match_type} match on {record_count} {records} with {blank_count} {blanks}'
    return format_explanation(form, record_count=record_count, blank_count=blank_count, match_type=match_type)


def explain_exact_match(value, values, filled, match_type):
    record_count, blank_count = explain_values(values, filled)
    form = '{match_type} match, {match_count} of {record_count} {records} with {blank_count} {blanks}'
    return format_explanation(form, value=value, record_count=record_count, match_count=filled[0].count,
                              blank_count=blank_count, match_type=match_type)


def explain_fuzzy_match(value, values, filled, score, match_type):
    record_count, blank_count = explain_values(values, filled)
    form = '{match_type} match on {record_count} {records} with {blank_count} {blanks}, score={score}'
    return format_explanation(form, record_count=record_count, blank_count=blank_count,
                              match_type=match_type, score=score)


def only_filled_values(values):
    return [ExactScore(c[0], c[1]) for c in Counter([v for v in values if v]).most_common()]


def best_select_value(group):
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
    global ARGS

    values = normalize_text(group)
    filled = only_filled_values(values)

    if not filled:
        return explain_all_blank(values)

    if filled[0].count > 1:
        return explain_exact_match(filled[0].value, values, filled, 'Normalized exact')

    if len(filled) == 1:
        return explain_one_transcript(filled[0].value, values, filled)

    # Check for simple inplace fuzzy matches
    top = top_partial_ratio(group)
    if top.score >= ARGS.fuzzy_ratio_threshold:
        return explain_fuzzy_match(top.value, values, filled, top.score, 'Partial ratio')

    # Now look for the best token match
    top = top_token_set_ratio(group)
    if top.score >= ARGS.fuzzy_set_threshold:
        return explain_fuzzy_match(top.value, values, filled, top.score, 'Token set ratio')

    return explain_no_match(values, filled, 'text')


def create_reconciled_dataframes(unreconciled_df, args):
    global ARGS
    ARGS = args

    # How to aggregate the columns based on each column's type which is determined by the column name
    method_for_select_columns = {c: best_select_value for c in unreconciled_df.columns
                                 if re.match(utils.SELECT_COLUMN_PATTERN, c)}
    method_for_text_columns = {c: best_text_value for c in unreconciled_df.columns
                               if re.match(utils.TEXT_COLUMN_PATTERN, c)}
    method_for_subject_columns = {c: all_are_identical for c in unreconciled_df.columns
                                  if c.startswith('subject_') and c != GROUP_BY}

    best_value_methods = method_for_select_columns.copy()
    best_value_methods.update(method_for_text_columns)
    best_value_methods.update(method_for_subject_columns)

    best_value_methods['locations'] = all_are_identical  # We want this column
    best_value_methods = {k: v for k, v in best_value_methods.items() if k not in UNWANTED_COLUMNS}  # Remove junk

    # Aggregate using the per column functions setup above
    reconciled_df = unreconciled_df.fillna('').groupby(GROUP_BY).aggregate(best_value_methods)

    # Split the combined reconciled value and flag into separate columns
    for c in list(method_for_text_columns.keys()) + list(method_for_select_columns.keys()):
        reconciled_df[c + '_explanation'], reconciled_df[c] = reconciled_df[c].str.split(SEPARATOR, n=1).str

    reconciled_df = reconciled_df.reindex_axis(sorted(reconciled_df.columns), axis=1)

    explanations_df = reconciled_df.loc[:, [c for c in reconciled_df.columns if c.endswith('_explanation')]]
    explanations_cols = {c: c.replace('_explanation', '') for c in explanations_df.columns}
    explanations_df.rename(columns=explanations_cols, inplace=True)

    reconciled_df.drop([c for c in reconciled_df.columns if c.endswith('_explanation')], axis=1, inplace=True)

    return reconciled_df, explanations_df
