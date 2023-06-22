from collections import Counter

from pylib.flag import Flag
from pylib.utils import P

PLACEHOLDERS = ["placeholder"]


def controlled_vocab(cls, group, row_count):
    filled = [
        f.value for f in group
        if f.value.strip() and f.value.lower not in PLACEHOLDERS
    ]
    blanks = row_count - len(filled)

    match Counter([v for v in filled]).most_common():

        # Nobody chose a value
        case []:
            note = (
                f"All {row_count} {P('record', row_count)} {P('is', row_count)} blank"
            )
            return cls(note=note, flag=Flag.ALL_BLANK)

        # Everyone chose the same value
        case [f0] if f0[1] > 1 and f0[1] == row_count:
            note = (
                f"Unanimous match, {f0[1]} of {row_count} {P('record', row_count)} "
                f"{blanks} {P('blank', blanks)}"
            )
            return cls(note=note, value=f0[0], flag=Flag.UNANIMOUS)

        # It was a tie for the values chosen
        case [f0, f1, *_] if f0[1] > 1 and f0[1] == f1[1]:
            note = (
                f"Match is a tie, {f0[1]} of {row_count} {P('record', row_count)} with "
                f"{blanks} {P('blank', blanks)}"
            )
            return cls(note=note, value=f0[0], flag=Flag.MAJORITY)

        # We have a winner
        case [f0, *_] if f0[1] > 1:
            note = (
                f"Match {f0[1]} of {row_count} {P('record', row_count)} "
                f"with {blanks} {P('blank', blanks)}"
            )
            return cls(note=note, value=f0[0], flag=Flag.MAJORITY)

        # Only one person chose a value
        case [f0] if f0[1] == 1:
            note = (
                f"Only 1 transcript in {row_count} {P('record', row_count)} "
                f"with {blanks} {P('blank', blanks)}"
            )
            return cls(note=note, value=f0[0], flag=Flag.ONLY_ONE)

        # Everyone picked a different value
        case _:
            note = (
                f"No match on {row_count} {P('record', row_count)} "
                f"with {blanks} {P('blank', blanks)}"
            )
            return cls(note=note, flag=Flag.NO_MATCH)
