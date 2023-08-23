from collections import defaultdict

from pylib.flag import Flag
from pylib.utils import P

PLACEHOLDERS = ["placeholder"]


def controlled_vocab(cls, group, row_count):
    filled = [
        f for f in group
        if f and f.value and f.value.strip() and f.value.lower not in PLACEHOLDERS
    ]
    count = len(filled)
    blanks = row_count - count

    by_value = defaultdict(list)
    for field in filled:
        by_value[field.value].append(field)
    counters = sorted(by_value.values(), key=lambda v: -len(v))

    match counters:
        # Nobody chose a value
        case []:
            note = (
                f"All {row_count} {P('record', row_count)} {P('is', row_count)} blank"
            )
            return cls.like(group, note=note, flag=Flag.ALL_BLANK)

        # Everyone chose the same value
        case [c0] if len(c0) > 1 and len(c0) == row_count:
            note = (
                f"Unanimous match, {len(c0)} of {row_count} {P('record', row_count)} "
                f"{blanks} {P('blank', blanks)}"
            )
            return cls.like(c0, note=note, value=c0[0].value, flag=Flag.UNANIMOUS)

        # It was a tie for the values chosen
        case [c0, c1, *_] if len(c0) > 1 and len(c0) == len(c1):
            note = (
                f"Match is a tie, {len(c0)} "
                f"of {row_count} {P('record', row_count)} with "
                f"{blanks} {P('blank', blanks)}"
            )
            return cls.like(c0, note=note, value=c0[0].value, flag=Flag.MAJORITY)

        # We have a winner
        case [c0, *_] if len(c0) > 1:
            note = (
                f"Match {len(c0)} of {row_count} {P('record', row_count)} "
                f"with {blanks} {P('blank', blanks)}"
            )
            return cls.like(c0, note=note, value=c0[0].value, flag=Flag.MAJORITY)

        # Only one person chose a value
        case [c0] if len(c0) == 1:
            note = (
                f"Only 1 transcript in {row_count} {P('record', row_count)} "
                f"with {blanks} {P('blank', blanks)}"
            )
            return cls.like(c0, note=note, value=c0[0].value, flag=Flag.ONLY_ONE)

        # Everyone picked a different value
        case [c0, *_] if len(c0) == 1:
            note = (
                f"No match on {row_count} {P('record', row_count)} "
                f"with {blanks} {P('blank', blanks)}"
            )
            return cls.like(c0, note=note, flag=Flag.NO_MATCH, value=c0[0].value)
