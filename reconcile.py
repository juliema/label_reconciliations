import re
import sys
import json
import argparse
import pandas as pd
from collections import Counter, namedtuple
from itertools import combinations
from fuzzywuzzy import fuzz

PLACE_HOLDERS = ['placeholder']  # Replace these placeholders with an empty string
NO_MATCHES = '<NO MATCHES>'      # A flag for unmatched data
GROUP_BY = 'subject_id'          # We group on this column
SEPARATOR = ':'                  # Used to separate match flags from values

# Type of matching
EXACT_MATCH = 'Exact match'
NORMALIZED_EXACT_MATCH = 'Normalized exact match'
PARTIAL_RATIO_MATCH = 'Partial ratio match'
TOKEN_SET_RATIO_MATCH = 'Token set ratio match'
SELECT_NO_MATCH = '<No match on select>'
TEXT_NO_MATCH = '<No match on text>'
NOT_ENOUGH_TO_MATCH = '<Only one transcript>'

# Useful for naming data fields, rather than using indexes into tuples
ExactScore = namedtuple('ExactScore', 'value count')
FuzzyRatioScore = namedtuple('FuzzyRatioScore', 'score value')
FuzzySetScore = namedtuple('FuzzySetScore', 'score value tokens')

UNWANTED_COLUMNS = ['subject_data', 'subject_retired', 'subject_subjectId']
COLUMNS_WITH_BAD_DATA = {}  # Subject_* columns with non-identical values in a group
ARGS = None


def output(best, match_type, count=None, total=None, score=None):
    if match_type in [EXACT_MATCH, NORMALIZED_EXACT_MATCH]:
        return '{} {}/{}{}{}'.format(match_type, count, total, SEPARATOR, best)
    elif match_type in [PARTIAL_RATIO_MATCH, TOKEN_SET_RATIO_MATCH]:
        return '{} score={}{}{}'.format(match_type, score, SEPARATOR, best)
    return '{}{}{}'.format(match_type, SEPARATOR, best)


def normalize_text(group):
    return ['\n'.join([' '.join(ln.split()) for ln in g.splitlines()]) for g in group]


def top_exact(values):
    counts = [ExactScore(c[0], c[1]) for c in Counter(values).most_common()]
    return counts[0] if counts[0].count > 1 else None


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


def reconcile_same(group):
    values = [g for g in group]
    counts = Counter(values)
    # Remove columns where we expect identical values but do not get them
    if len(counts) > 1:
        COLUMNS_WITH_BAD_DATA[group.name] = 1
        return ''
    return values[0]


def reconcile_select(group):
    values = [str(g) if str(g).lower() not in PLACE_HOLDERS else '' for g in group]
    if len(values) < 2:
        return output(NO_MATCHES, NOT_ENOUGH_TO_MATCH)
    top = top_exact(values)
    if top:
        return output(top.value, EXACT_MATCH, count=top.count, total=len(values))
    return output(NO_MATCHES, SELECT_NO_MATCH)


def reconcile_text(group):
    global ARGS

    values = normalize_text(group)
    if len(values) < 2:
        return output(NO_MATCHES, NOT_ENOUGH_TO_MATCH)

    # Look for identical matches and order them by how common they are
    counts = [ExactScore(c[0], c[1]) for c in Counter(values).most_common()]
    if (not counts[0].value and len(counts) == 1) or (counts[0].count > 1):
        return output(counts[0].value, NORMALIZED_EXACT_MATCH, count=counts[0].count, total=len(values))

    # Check for simple inplace fuzzy matches
    top = top_partial_ratio(group)
    if top.score >= ARGS.fuzzy_ratio_threshold:
        return output(top.value, PARTIAL_RATIO_MATCH, score=top.score)

    # Now look for the best token match
    top = top_token_set_ratio(group)
    if top.score >= ARGS.fuzzy_set_threshold:
        return output(top.value, TOKEN_SET_RATIO_MATCH, score=top.score)
    return output(NO_MATCHES, TEXT_NO_MATCH)


def reconcile():
    global ARGS
    df = pd.read_csv(ARGS.input)

    # How to aggregate the columns based on each column's type which is determined by the column name
    select_cols = {c: reconcile_select for c in df.columns if re.match(r'T\d+s:', c)}
    text_cols = {c: reconcile_text for c in df.columns if re.match(r'T\d+t:', c)}
    subject_cols = {c: reconcile_same for c in df.columns if c.startswith('subject_') and c != GROUP_BY}
    aggregate_cols = dict(list(select_cols.items()) + list(text_cols.items()) + list(subject_cols.items()))
    aggregate_cols['locations'] = reconcile_same
    aggregate_cols = {k: v for k, v in aggregate_cols.items() if k not in UNWANTED_COLUMNS}

    # Aggregate using the per column functions setup above
    grouped = df.fillna('').groupby(GROUP_BY).aggregate(aggregate_cols)

    grouped.drop(COLUMNS_WITH_BAD_DATA.keys(), axis=1, inplace=True)

    # Split the combined reconciled value and flag into separate columns
    for c in list(text_cols.keys()) + list(select_cols.keys()):
        grouped[c + '_explanation'], grouped[c] = grouped[c].str.split(SEPARATOR, n=1).str

    grouped = grouped.reindex_axis(sorted(grouped.columns), axis=1)

    # Make the sidecar explanations file -- DELETE these lines if we want one file for this
    explanations = grouped.loc[:, [c for c in grouped.columns if c.endswith('_explanation')]]
    grouped.drop([c for c in grouped.columns if c.endswith('_explanation')], axis=1, inplace=True)
    if ARGS.explanations:
        explanations.to_csv(ARGS.explanations, sep=',', encoding='utf-8')

    grouped.to_csv(ARGS.output, sep=',', encoding='utf-8')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help='The raw extracts CSV file to reconcile')
    parser.add_argument('-o', '--output', required=True, help='Write the reconciled extracts to this CSV file')
    parser.add_argument('-r', '--fuzzy-ratio-threshold', default=90, type=int,
                        help='Sets the cutoff for fuzzy ratio matching (0-100, default=90). '
                             'See https://github.com/seatgeek/fuzzywuzzy.')
    parser.add_argument('-s', '--fuzzy-set-threshold', default=50, type=int,
                        help='Sets the cutoff for fuzzy set matching (0-100, default=50). '
                             'See https://github.com/seatgeek/fuzzywuzzy.')
    parser.add_argument('-e', '--explanations', help='Write reconciliation explanations to this file')
    ARGS = parser.parse_args()

    reconcile()
