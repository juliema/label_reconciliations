"""Reconcile free text fields."""

import re
from collections import namedtuple, defaultdict
from itertools import combinations
import inflect
from fuzzywuzzy import fuzz  # pylint: disable=import-error


E = inflect.engine()
E.defnoun('The', 'All')
P = E.plural

FuzzyRatioScore = namedtuple('FuzzyRatioScore', 'score value')
FuzzySetScore = namedtuple('FuzzySetScore', 'score value tokens')
ExactScore = namedtuple('ExactScore', 'value count')


def reconcile(group, args=None):
    """Reconcile the data."""
    group = group.astype(str)
    values = ['\n'.join([' '.join(ln.split()) for ln in str(g).splitlines()])
              for g in group]

    count = len(values)

    # Look for exact matches
    exact = exact_match(values)
    blanks = count - sum(f.count for f in exact)

    if not exact:  # Note: Only spaces are removed
        reason = '{} {} {} {} blank'.format(
            P('The', count), count, P('record', count), P('is', count))
        return reason, ''

    if exact[0].count > 1 and exact[0].count == count:
        reason = 'Exact unanimous match, {} of {} {}'.format(
            exact[0].count, count, P('record', count))
        return reason, exact[0].value

    if (len(exact) > 1 and exact[0].count > 1
            and exact[0].count == exact[1].count):
        reason = 'Exact match is a tie, {} of {} {} with {} {}'.format(
            exact[0].count, count, P('record', count),
            blanks, P('blank', blanks))
        return reason, exact[0].value

    if exact[0].count > 1:
        reason = 'Exact match, {} of {} {} with {} {}'.format(
            exact[0].count, count, P('record', count),
            blanks, P('blank', blanks))
        return reason, exact[0].value

    # Look for normalized exact matches
    filled = only_filled_values(values)
    blanks = count - sum(f.count for f in filled)

    if not filled:  # Note: Both spaces & punctuation are removed
        reason = '{} {} normalized {} {} blank'.format(
            P('The', count), count, P('record', count), P('is', count))
        return reason, ''

    if filled[0].count > 1 and filled[0].count == count:
        reason = 'Normalized unanimous match, {} of {} {}'.format(
            filled[0].count, count, P('record', count))
        return reason, filled[0].value

    if len(filled) > 1 and filled[0].count > 1 \
            and filled[0].count == filled[1].count:
        reason = 'Normalized match is a tie, {} of {} {} with {} {}'.format(
            filled[0].count, count, P('record', count),
            blanks, P('blank', blanks))
        return reason, filled[0].value

    if filled[0].count > 1:
        reason = 'Normalized match, {} of {} {} with {} {}'.format(
            filled[0].count, count, P('record', count),
            blanks, P('blank', blanks))
        return reason, filled[0].value

    if len(filled) == 1:
        reason = 'Only 1 transcript in {} {}'.format(count, P('record', count))
        return reason, filled[0].value

    # Check for simple in-place fuzzy matches
    top = top_partial_ratio(group, args.user_weights)
    if top.score >= args.fuzzy_ratio_threshold:
        reason = 'Partial ratio match on {} {} with {} {}, score={}'.format(
            count, P('record', count), blanks, P('blank', blanks), top.score)
        return reason, top.value

    # Now look for the best token match
    top = top_token_set_ratio(values)
    if top.score >= args.fuzzy_set_threshold:
        reason = 'Token set ratio match on {} {} with {} {}, score={}'.format(
            count, P('record', count), blanks, P('blank', blanks), top.score)
        return reason, top.value

    reason = 'No text match on {} {} with {} {}'.format(
        count, P('record', count), blanks, P('blank', blanks))
    return reason, ''


def exact_match(values):
    """Look for exact matches in the value list."""
    filled = defaultdict(int)
    for value in values:
        filled[value] += 1

    exact = [ExactScore(k, v) for k, v in filled.items() if k]
    return sorted(exact, key=lambda s: (s.count, len(s.value)), reverse=True)


def only_filled_values(values):
    """
    Get the filled items items in the group.

    Then sort them by frequency. Normalize the text for comparison by removing
    spaces and punctuation, and setting all letters to lower case. The exemplar
    for the group is the longest pre-normalized value. So if we have three
    values like so:
      "A test label"  "a Test Label."   "A TEST LABEL"
    They will normalize to "a test label" and the second value "a Test Label."
    will become the returned value for that group.
    """
    all_filled = defaultdict(list)
    for value in values:
        value = value.strip()
        if value:
            squished = re.sub(r'\W+', '', value).lower()
            all_filled[squished].append(value)

    only_filled = []
    for _, vals in all_filled.items():
        longest = sorted(vals, key=len, reverse=True)[0]
        only_filled.append(ExactScore(longest, len(vals)))

    return sorted(only_filled, key=lambda s: s.count, reverse=True)


def top_partial_ratio(group, user_weights):
    """Return the best partial ratio match from fuzzywuzzy module."""
    scores = []
    group = group.reset_index(level=0, drop=True)
    for combo in combinations(zip(group, group.index), 2):
        # combo format is ((value1, username1),(value2, username2))
        score = fuzz.partial_ratio(combo[0][0], combo[1][0])
        if len(combo[0][0]) >= len(combo[1][0]):
            value, user_name = combo[0][0], combo[0][1]
        else:
            value, user_name = combo[1][0], combo[1][1]
        score = score + user_weights.get(user_name.lower(), 0)  # add weight
        score = min(max(score, 0), 100)  # enforce a ceiling and floor
        scores.append(FuzzyRatioScore(score, value))

    scores = sorted(
        scores, reverse=True, key=lambda s: (s.score, len(s.value)))
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
        key=lambda s: (s.score, s.tokens, -len(s.value)))
    return ordered[0]
