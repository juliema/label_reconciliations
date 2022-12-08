"""Reconcile free for text fields."""
import re
from collections import Counter
from collections import defaultdict
from collections import namedtuple
from dataclasses import dataclass
from itertools import combinations

from fuzzywuzzy import fuzz  # pylint: disable=import-error

from pylib.fields.base_field import BaseField
from pylib.result import Result
from pylib.result import sort_results
from pylib.utils import P


FuzzyRatioScore = namedtuple("FuzzyRatioScore", "score value")
FuzzySetScore = namedtuple("FuzzySetScore", "score value tokens")
ExactScore = namedtuple("ExactScore", "string count")


@dataclass(kw_only=True)
class TextField(BaseField):
    value: str = ""

    def to_dict(self):
        return {self.label: self.value}

    @classmethod
    def reconcile(cls, group, args=None):
        strings = [" ".join(f.value.split()) if f.value else "" for f in group]
        count = len(strings)

        # Look for exact matches
        exact = exact_matches(strings)
        blanks = count - sum(f.count for f in exact)

        match exact:

            # No matches
            case []:
                note = (
                    f"{P('The', count)} {count} {P('record', count)} "
                    f"{P('is', count)} blank"
                )
                return cls(note=note, result=Result.ALL_BLANK)

            # Only one selected
            case [e0] if e0.count == 1:
                note = f"Only 1 transcript in {count} {P('record', count)}"
                return cls(note=note, value=e0.string, result=Result.ONLY_ONE)

            # Everyone chose the same value
            case [e0] if e0.count == count and e0.count > 1:
                note = (
                    f"Exact unanimous match, {e0.count} of {count} {P('record', count)}"
                )
                return cls(note=note, value=e0.string, result=Result.UNANIMOUS)

            # It was a tie for the text chosen
            case [e0, e1, *_] if e0.count > 1 and e0.count == e1.count:
                note = (
                    f"Exact match is a tie, {e0.count} of {count} {P('record', count)} "
                    f"with {blanks} {P('blank', blanks)}"
                )
                return cls(note=note, value=e0.string, result=Result.MAJORITY)

            # We have a winner
            case [e0, *_] if e0.count > 1:
                note = (
                    f"Exact match, {e0.count} of {count} {P('record', count)} with "
                    f"{blanks} {P('blank', blanks)}"
                )
                return cls(note=note, value=e0.string, result=Result.MAJORITY)

        # Look for normalized exact matches
        norm = normalized_exact_matches(strings)
        blanks = count - sum(f.count for f in norm)

        match norm:

            # No matches
            case []:
                note = (
                    f"{P('The', count)} {count} normalized {P('record', count)} "
                    f"{P('is', count)} blank"
                )
                return cls(note=note, result=Result.NO_MATCH)

            # Everyone chose the same value
            case [n0] if n0.count == count and n0.count > 1:
                note = (
                    f"Normalized unanimous match, {n0.count} of {count} "
                    f"{P('record', count)}"
                )
                return cls(note=note, value=n0.string, result=Result.UNANIMOUS)

            # The winners are a tie
            case [n0, n1, *_] if n0.count > 1 and n0.count == n1.count:
                note = (
                    f"Normalized match is a tie, {n0.count} of {count} "
                    f"{P('record', count)} with {blanks} {P('blank', blanks)}"
                )
                return cls(note=note, value=n0.string, result=Result.MAJORITY)

            # We have a winner
            case [n0, *_] if n0.count > 1:
                note = (
                    f"Normalized match, {n0.count} of {count} {P('record', count)} "
                    f"with {blanks} {P('blank', blanks)}"
                )
                return cls(note=note, value=n0.string, result=Result.MAJORITY)

        # Check for simple in-place fuzzy matches
        top = top_partial_ratio(strings)
        if top.score >= args.fuzzy_ratio_threshold:
            note = (
                f"Partial ratio match on {count} {P('record', count)} with {blanks} "
                f"{P('blank', blanks)}, score={top.score}"
            )
            return cls(note=note, value=top.value, result=Result.FUZZY)

        # Now look for the best token match
        top = top_token_set_ratio(strings)
        if top.score >= args.fuzzy_set_threshold:
            note = (
                f"Token set ratio match on {count} {P('record', count)} with {blanks} "
                f"{P('blank', blanks)}, score={top.score}"
            )
            return cls(note=note, value=top.value, result=Result.FUZZY)

        # Nothing matches
        note = (
            f"No text match on {count} {P('record', count)} with {blanks} "
            f"{P('blank', blanks)}"
        )
        return cls(note=note, result=Result.NO_MATCH)

    @classmethod
    def pad_group(cls, group, length):
        while len(group) < length:
            group.append(cls())
        return group

    @staticmethod
    def results():
        return sort_results(
            Result.ALL_BLANK,
            Result.UNANIMOUS,
            Result.MAJORITY,
            Result.ONLY_ONE,
            Result.NO_MATCH,
            Result.FUZZY,
        )


def exact_matches(strings):
    """Look for exact matches in the string list."""
    counts = Counter(strings)
    exact = [ExactScore(string, count) for string, count in counts.items() if string]
    return sorted(exact, key=lambda s: (s.count, len(s.string)), reverse=True)


def normalized_exact_matches(strings):
    """
    Get normalized strings for the group items in the group.

    Then sort them by frequency. Normalize the text for comparison by removing
    spaces and punctuation, and setting all letters to lower case. The exemplar
    for the group is the longest pre-normalized value. So if we have three
    strings like so:
      "A test label"  "a Test Label."   "A TEST LABEL"
    They will normalize to "a test label" and the second value "a Test Label."
    will become the returned value for that group.
    """
    norms = defaultdict(list)
    for string in strings:
        if squished := re.sub(r"\W+", "", string).lower():
            norms[squished].append(string)

    normalized = []
    for same in norms.values():
        longest = sorted(same, key=len, reverse=True)[0]
        normalized.append(ExactScore(longest, len(same)))

    return sorted(normalized, key=lambda s: s.count, reverse=True)


def top_partial_ratio(strings):
    """Return the best partial ratio match from fuzzywuzzy module."""
    scores = []
    for c0, c1 in combinations(strings, 2):
        score = fuzz.partial_ratio(c0, c1)
        value = c0 if len(c0) >= len(c1) else c1
        scores.append(FuzzyRatioScore(score, value))

    scores = sorted(scores, reverse=True, key=lambda s: (s.score, len(s)))
    return scores[0] if scores else None


def top_token_set_ratio(strings):
    """Return the best token set ratio match from fuzzywuzzy module."""
    scores = []
    for c0, c1 in combinations(strings, 2):
        score = fuzz.token_set_ratio(c0, c1)
        tokens_0 = len(c0.split())
        tokens_1 = len(c1.split())
        if tokens_0 > tokens_1:
            value = c0
            tokens = tokens_0
        elif tokens_0 < tokens_1:
            value = c1
            tokens = tokens_1
        else:
            value = c0 if len(c0) <= len(c1) else c1
            tokens = tokens_0
        scores.append(FuzzySetScore(score, value, tokens))

    ordered = sorted(
        scores, reverse=True, key=lambda s: (s.score, s.tokens, -len(s.value))
    )
    return ordered[0]
