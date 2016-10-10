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
GROUP_BY = 'subject_ids'         # We group on this column

# Type of matching
EXACT_MATCH = 'exact'
NORMALIZED_EXACT_MATCH = 'exact_normalized'
PARTIAL_RATIO_MATCH = 'partial_ratio'
TOKEN_SET_RATIO_MATCH = 'token_set_ratio'

# Useful for naming data fields, rather than numbers
ExactScore = namedtuple('ExactScore', 'value count')
FuzzyRatioScore = namedtuple('FuzzyRatioScore', 'score value')
FuzzySetScore = namedtuple('FuzzySetScore', 'score value tokens')

EXPLAINATIONS = None  # Explanations dataframe (Holds data on how the data were reconciled)
ARGS = None


def output(best, type, group=None, matches=None, score=None):
    print(group.name)
    sys.exit()
    return value


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
    ordered = sorted(scores, reverse=True, key=lambda s: '{:0>6} {:0>6}'.format(s.score, len(s.value)))
    return ordered[0]


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
    return values[0]


def reconcile_select(group):
    values = [g if g.lower() not in PLACE_HOLDERS else '' for g in group]
    top = top_exact(values)
    best = best.value if best else NO_MATCHES
    return output(best, EXACT_MATCH)


def reconcile_text(group):
    global ARGS

    group = normalize_text(group)

    # Look for identical matches and order them by how common they are
    counts = [ExactScore(c[0], c[1]) for c in Counter(group).most_common()]
    if not counts[0].value and len(counts) == 1:
        return ''
    if counts[0].count > 1:
        return counts[0].value

    # Check for simple inplace fuzzy matches
    top = top_partial_ratio(group)
    if top.score == ARGS.fuzzy_ratio_threshold:
        return top.value

    # Now look for the best token match
    top = top_token_set_ratio(group)
    return top.value if top.score > ARGS.fuzzy_set_threshold else NO_MATCHES


def reconcile():
    global ARGS
    df = pd.read_csv(ARGS.input)

    select_cols = {c: reconcile_select for c in df.columns if re.match(r'T\d+s:', c)}
    text_cols = {c: reconcile_text for c in df.columns if re.match(r'T\d+t:', c)}
    subject_cols = {c: reconcile_same for c in df.columns
                    if c.startswith('subject_') and c not in ['subject_data', 'subject_id', 'subject_ids']}
    aggregate_cols = dict(list(select_cols.items()) + list(text_cols.items()) + list(subject_cols.items()))

    grouped = df.fillna('').groupby(GROUP_BY, as_index=False).aggregate(aggregate_cols)

    # Reshape the reconciled dataframe to sort the columns and put the subject_ids first
    grouped = grouped.reindex_axis([grouped.columns[0]] + sorted(grouped.columns[1:]), axis=1)
    grouped.rename(columns={'subject_ids': 'subject_id'}, inplace=True)

    grouped.to_csv(ARGS.output, sep=',', index=False, encoding='utf-8')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help='The raw extracts CSV file to reconcile')
    parser.add_argument('-o', '--output', required=True, help='Write the reconciled extracts to this CSV file')
    parser.add_argument('-r', '--fuzzy-ratio-threshold', default=100, type=int,
                        help='Sets the cutoff for fuzzy ratio matching (0-100, default=100). '
                             'See https://github.com/seatgeek/fuzzywuzzy.')
    parser.add_argument('-s', '--fuzzy-set-threshold', default=50, type=int,
                        help='Sets the cutoff for fuzzy set matching (0-100, default=50). '
                             'See https://github.com/seatgeek/fuzzywuzzy.')
    parser.add_argument('-e', '--explanation', help='Write reconcilliation explanations to this file')
    ARGS = parser.parse_args()

    reconcile()
