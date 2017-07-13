"""Reconcile free text fields."""

import re
from collections import Counter, namedtuple
from itertools import combinations
from fuzzywuzzy import fuzz
import inflect

HAS_EXPLANATIONS = True

PLACEHOLDERS = ['placeholder']
E = inflect.engine()
E.defnoun('The', 'All')
P = E.plural

FuzzyRatioScore = namedtuple('FuzzyRatioScore', 'score value')
FuzzySetScore = namedtuple('FuzzySetScore', 'score value tokens')


def reconcile(group, args=None):
    """Reconcile the data."""

    values = [re.sub(r'\W+', '', str(v)).lower() for v in group]
    print(values)

    filled = Counter([v for v in values if v.strip()]).most_common()
    count = len(values)
    blanks = count - sum([f[1] for f in filled])

    if not filled:
        reason = [P('The', count), str(count), P('record', count),
                  P('is', count), 'blank']
        return ' '.join(reason), ''

    if filled[0][1] > 1:
        reason = ['Normalized exact match,', filled[0][1], 'of',
                  str(count), P('record', count), 'with', str(blanks),
                  P('blank', blanks)]
        return ' '.join(reason), filled[0][0]

    if filled[0][1] == 1:
        reason = ['Only 1 transcript in', str(count), P('record', count)]
        return ' '.join(reason), filled[0][0]

    # Check for simple in-place fuzzy matches
    top = top_partial_ratio(values)
    if top.score >= args.fuzzy_ratio_threshold:
        reason = ['Partial ratio match on', str(count), P('record', count),
                  'with', str(blanks), P('blank', blanks),
                  'score=', str(top.score)]
        return ' '.join(reason), top.value

    # Now look for the best token match
    top = top_token_set_ratio(values)
    if top.score >= args.fuzzy_set_threshold:
        reason = ['Token set ratio match on', str(count), P('record', count),
                  'with', str(blanks), P('blank', blanks),
                  'score=', str(top.score)]
        return ' '.join(reason), top.value

    reason = ['No exact match on', str(count), P('record', count),
              'with', str(blanks), P('blank', blanks)]
    return ' '.join(reason), ''


def top_partial_ratio(values):
    """Return the best partial ratio match from fuzzywuzzy module."""

    scores = []
    for combo in combinations(values, 2):
        score = fuzz.partial_ratio(combo[0], combo[1])
        value = combo[0] if len(combo[0]) >= len(combo[1]) else combo[1]
        scores.append(FuzzyRatioScore(score, value))
    scores = sorted(scores,
                    reverse=True,
                    key=lambda s: (s.score, len(s.value)))
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
            value = combo[1]
            if len(combo[0]) <= len(combo[1]):
                value = combo[0]
        scores.append(FuzzySetScore(score, value, tokens))

    ordered = sorted(
        scores,
        reverse=True,
        key=lambda s: (s.score, s.tokens, 1000000 - len(s.value)))
    return ordered[0]
