"""Reconcile free for text fields."""
import re
from collections import defaultdict, namedtuple
from dataclasses import dataclass
from itertools import combinations
from typing import Any

from fuzzywuzzy import fuzz  # pylint: disable=import-error

from pylib.fields.base_field import BaseField
from pylib.flag import Flag
from pylib.utils import P

FuzzyRatioScore = namedtuple("FuzzyRatioScore", "score field")
FuzzySetScore = namedtuple("FuzzySetScore", "score tokens field")


@dataclass(kw_only=True)
class TextField(BaseField):
    value: str = ""

    def to_dict(self, reconciled=False, add_note=False) -> dict[str, Any]:
        field_dict = {self.header(): self.value}
        return field_dict

    @classmethod
    def reconcile(cls, group, row_count, args=None):

        count, blanks, exact = exact_matches(group, row_count)

        match exact:
            # No matches
            case []:
                note = (
                    f"The {row_count} "
                    f"{P('record', row_count)} {P('is', row_count)} blank"
                )
                return cls.like(group, note=note, flag=Flag.ALL_BLANK)

            # Only one selected
            case [c0] if len(c0) == 1:
                note = f"Only 1 transcript in {row_count} {P('record', row_count)}"
                return cls.like(c0, note=note, value=c0[0].value, flag=Flag.ONLY_ONE)

            # Everyone chose the same value
            case [c0] if len(c0) > 1 and len(c0) == row_count:
                note = (
                    f"Exact unanimous match, {len(c0)} of {row_count} "
                    f"{P('record', row_count)}"
                )
                return cls.like(c0, note=note, value=c0[0].value, flag=Flag.UNANIMOUS)

            # It was a tie for the text chosen
            case [c0, c1, *_] if len(c0) > 1 and len(c0) == len(c1):
                note = (
                    f"Exact match is a tie, {len(c0)} of {row_count} "
                    f"{P('record', row_count)} with {blanks} {P('blank', blanks)}"
                )
                return cls.like(c0, note=note, value=c0[0].value, flag=Flag.MAJORITY)

            # We have a winner
            case [c0, *_] if len(c0) > 1:
                note = (
                    f"Exact match, {len(c0)} of {row_count} "
                    f"{P('record', row_count)} with {blanks} {P('blank', blanks)}"
                )
                return cls.like(c0, note=note, value=c0[0].value, flag=Flag.MAJORITY)

        # Look for normalized exact matches
        count, blanks, norm = normalized_exact_matches(group, row_count)

        match norm:
            # No matches
            case []:
                note = (
                    f"The {row_count} normalized "
                    f"{P('record', row_count)} {P('is', row_count)} blank"
                )
                return cls.like(group, note=note, flag=Flag.NO_MATCH)

            # Everyone chose the same value
            case [c0] if len(c0) > 1 and len(c0) == row_count:
                note = (
                    f"Normalized unanimous match, {len(c0)} of {row_count} "
                    f"{P('record', row_count)}"
                )
                return cls.like(c0, note=note, value=c0[0].value, flag=Flag.UNANIMOUS)

            # The winners are a tie
            case [c0, c1, *_] if len(c0) > 1 and len(c0) == len(c1):
                note = (
                    f"Normalized match is a tie, {len(c0)} of {row_count} "
                    f"{P('record', row_count)} with {blanks} {P('blank', blanks)}"
                )
                return cls.like(c0, note=note, value=c0[0].value, flag=Flag.MAJORITY)

            # We have a winner
            case [c0, *_] if len(c0) > 1:
                note = (
                    f"Normalized match, {len(c0)} of {row_count} "
                    f"{P('record', row_count)} "
                    f"with {blanks} {P('blank', blanks)}"
                )
                return cls.like(c0, note=note, value=c0[0].value, flag=Flag.MAJORITY)

        # Check for simple in-place fuzzy matches
        top = top_partial_ratio(group)
        if top and top.score >= args.fuzzy_ratio_threshold:
            note = (
                f"Partial ratio match on {row_count} "
                f"{P('record', row_count)} with {blanks} "
                f"{P('blank', blanks)}, score={top.score}"
            )
            return cls.like(
                top.field, note=note, value=top.field.value, flag=Flag.FUZZY
            )

        # Now look for the best token match
        top = top_token_set_ratio(group)
        if top.score >= args.fuzzy_set_threshold:
            note = (
                f"Token set ratio match on {row_count} "
                f"{P('record', row_count)} with {blanks} "
                f"{P('blank', blanks)}, score={top.score}"
            )
            return cls.like(
                top.field, note=note, value=top.field.value, flag=Flag.FUZZY
            )

        # Nothing matches
        note = (
            f"No text match on {row_count} {P('record', row_count)} with {blanks} "
            f"{P('blank', blanks)}"
        )
        return cls.like(exact[0], note=note, flag=Flag.NO_MATCH, value="")


def exact_matches(group, row_count) -> tuple[int, int, list[list]]:
    # Sort the fields by values
    filled = defaultdict(list)
    for field in group:
        field.value = field.value if field.value else ""
        if key := " ".join(field.value.split()):
            filled[key].append(field)

    counters = sorted(filled.values(), key=lambda f: -len(f))

    count = sum(len(f) for f in filled.values())
    blanks = row_count - count

    return count, blanks, counters


def normalized_exact_matches(group, row_count) -> tuple[int, int, list[list]]:
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
    # Sort the fields by normalized values
    filled = defaultdict(list)
    for field in group:
        field.value = field.value if field.value else ""
        if key := re.sub(r"\W+", "", field.value).lower():
            filled[key].append(field)

    # Bring the field with the longest value to the front of the list
    new = {v: sorted(f, key=lambda x: -len(x.value)) for v, f in filled.items()}

    counters = sorted(new.values(), key=lambda f: -len(f))

    count = sum(len(f) for f in filled.values())
    blanks = row_count - count

    return count, blanks, counters


def top_partial_ratio(group):
    """Return the best partial ratio match from fuzzywuzzy module."""
    scores = []
    for c0, c1 in combinations(group, 2):
        score = fuzz.partial_ratio(c0.value, c1.value)
        field = c0 if len(c0.value) >= len(c1.value) else c1
        scores.append(FuzzyRatioScore(score, field))

    scores = sorted(scores, reverse=True, key=lambda s: (s.score, len(s.field.value)))
    return scores[0] if scores else None


def top_token_set_ratio(group):
    """Return the best token set ratio match from fuzzywuzzy module."""
    scores = []
    for c0, c1 in combinations(group, 2):
        score = fuzz.token_set_ratio(c0.value, c1.value)
        tokens_0 = len(c0.value.split())
        tokens_1 = len(c1.value.split())
        if tokens_0 > tokens_1:
            field = c0
            tokens = tokens_0
        elif tokens_0 < tokens_1:
            field = c1
            tokens = tokens_1
        else:
            field = c0 if len(c0.value) <= len(c1.value) else c1
            tokens = tokens_0
        scores.append(FuzzySetScore(score, tokens, field))

    ordered = sorted(
        scores, reverse=True, key=lambda s: (s.score, s.tokens, -len(s.field.value))
    )
    return ordered[0]
