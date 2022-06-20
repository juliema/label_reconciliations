"""Reconcile select lists.

Classifications are chosen from a controlled vocabulary.
"""
# noqa pylint: disable=invalid-name
from collections import Counter

from pylib import cell
from pylib.utils import P

PLACEHOLDERS = ["placeholder"]


def reconcile(group, args=None):  # noqa pylint: disable=unused-argument
    values = [str(g) if str(g).lower() not in PLACEHOLDERS else "" for g in group]

    filled = Counter([v for v in values if v.strip()]).most_common()

    count = len(values)
    blanks = count - sum(f[1] for f in filled)

    match filled:
        # Nobody chose a value
        case []:
            note = (
                f"{P('The', count)} {count} {P('record', count)} "
                f"{P('is', count)} blank"
            )
            return cell.empty(note=note)

        # Everyone chose the same value
        case [f0] if f0[1] > 1 and f0[1] == count:
            note = f"Unanimous match, {f0[1]} of {count} {P('record', count)}"
            return cell.ok(note=note, value=f0[0])

        # It was a tie for the values chosen
        case [f0, f1, *_] if f0[1] > 1 and f0[1] == f1[1]:
            note = (
                f"Match is a tie, {f0[1]} of {count} {P('record', count)} with "
                f"{blanks} {P('blank', blanks)}"
            )
            return cell.ok(note=note, value=f0[0])

        # We have a winner
        case [f0, *_] if f0[1] > 1:
            note = (
                f"Match, {f0[1]} of {count} {P('record', count)} with {blanks} "
                f"{P('blank', blanks)}"
            )
            return cell.ok(note=note, value=f0[0])

        # Only one person chose a value
        case [f0] if f0[1] == 1:
            note = "Only 1 transcript in {count} {P('record', count)}"
            return cell.warning(note=note, value=f0[0])

        # Everyone picked a different value
        case _:
            note = (
                f"No select match on {count} {P('record', count)} with {blanks} "
                f"{P('blank', blanks)}"
            )
            return cell.error(note=note)
