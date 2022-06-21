# noqa pylint: disable=invalid-name
import re
from collections import defaultdict
from collections import namedtuple
from dataclasses import dataclass
from itertools import combinations

from fuzzywuzzy import fuzz  # pylint: disable=import-error

from pylib import cell
from pylib.fields.base_field import BaseField
from pylib.utils import P

FuzzyRatioScore = namedtuple("FuzzyRatioScore", "score value")
FuzzySetScore = namedtuple("FuzzySetScore", "score value tokens")
ExactScore = namedtuple("ExactScore", "value count")


@dataclass(kw_only=True)
class TextField(BaseField):
    value: str

    def to_dict(self):
        return {self.label: self.value}


def reconcile(group, args=None):  # noqa pylint: disable=unused-argument
    group = group.astype(str)
    values = [
        "\n".join([" ".join(ln.split()) for ln in str(g).splitlines()]) for g in group
    ]

    count = len(values)

    # Look for exact matches
    exact = exact_match(values)
    blanks = count - sum(f.count for f in exact)

    match exact:

        # No matches
        case []:
            note = (
                f"{P('The', count)} {count} {P('record', count)} "
                f"{P('is', count)} blank"
            )
            return cell.all_blank(note=note)

        # Everyone chose the same value
        case [e0] if e0.count == count:
            note = f"Exact unanimous match, {e0.count} of {count} {P('record', count)}"
            return cell.unanimous(note=note, value=e0.value)

        # It was a tie for the text chosen
        case [e0, e1, *_] if e0.count > 1 and e0.count == e1.count:
            note = (
                f"Exact match is a tie, {e0.count} of {count} {P('record', count)} "
                f"with {blanks} {P('blank', blanks)}"
            )
            return cell.majority(note=note, value=e0.value)

        # We have a winner
        case [e0, *_] if e0.count > 1:
            note = (
                f"Exact match, {e0.count} of {count} {P('record', count)} with "
                f"{blanks} {P('blank', blanks)}"
            )
            return cell.majority(note=note, value=e0.value)

    # Look for normalized exact matches
    filled = only_filled_values(values)
    blanks = count - sum(f.count for f in filled)

    match filled:

        # No matches
        case []:
            note = (
                f"{P('The', count)} {count} normalized {P('record', count)} "
                f"{P('is', count)} blank"
            )
            return cell.no_match(note=note)

        # Everyone chose the same value
        case [f0] if f0.count == count:
            note = (
                f"Normalized unanimous match, {f0.count} of {count} "
                f"{P('record', count)}"
            )
            return cell.unanimous(note=note, value=f0.value)

        # It was a tie for the values chosen
        case [f0, f1, *_] if f0.count == f1.count:
            note = (
                f"Normalized match is a tie, {f0.count} of {count} "
                f"{P('record', count)} with {blanks} {P('blank', blanks)}"
            )
            return cell.ok(note=note, value=f0.value)

        case [f0] if f0 == 1:
            note = f"Only 1 transcript in {count} {P('record', count)}"
            return cell.only_one(note=note, value=f0.value)

    # Check for simple in-place fuzzy matches
    top = top_partial_ratio(group)

    if top.score >= args.fuzzy_ratio_threshold:
        note = (
            f"Partial ratio match on {count} {P('record', count)} with {blanks} "
            f"{P('blank', blanks)}, score={top.score}"
        )
        return cell.fuzzy(note=note, value=top.value)

    # Now look for the best token match
    top = top_token_set_ratio(values)
    if top.score >= args.fuzzy_set_threshold:
        note = (
            f"Token set ratio match on {count} {P('record', count)} with {blanks} "
            f"{P('blank', blanks)}, score={top.score}"
        )
        return cell.fuzzy(note=note, value=top.value)

    # Nothing matches
    note = (
        f"No text match on {count} {P('record', count)} with {blanks} "
        f"{P('blank', blanks)}"
    )
    return cell.no_match(note=note)


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
            squished = re.sub(r"\W+", "", value).lower()
            all_filled[squished].append(value)

    only_filled = []
    for _, vals in all_filled.items():
        longest = sorted(vals, key=len, reverse=True)[0]
        only_filled.append(ExactScore(longest, len(vals)))

    return sorted(only_filled, key=lambda s: s.count, reverse=True)


def top_partial_ratio(group):
    """Return the best partial ratio match from fuzzywuzzy module."""
    scores = []
    group = group.reset_index(level=0, drop=True).astype(str)
    for combo in combinations(zip(group, group.index), 2):
        score = fuzz.partial_ratio(combo[0][0], combo[1][0])
        value = combo[0][0] if len(combo[0][0]) >= len(combo[1][0]) else combo[1][0]
        scores.append(FuzzyRatioScore(score, value))

    scores = sorted(scores, reverse=True, key=lambda s: (s.score, len(s.value)))
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
        scores, reverse=True, key=lambda s: (s.score, s.tokens, -len(s.value))
    )
    return ordered[0]
