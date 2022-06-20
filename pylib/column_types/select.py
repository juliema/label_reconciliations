"""Reconcile select lists.

Classifications are chosen from a controlled vocabulary.
"""
from collections import Counter

from .. import cell
from ..util import P

PLACEHOLDERS = ["placeholder"]


def reconcile(group, args=None):  # noqa
    values = [str(g) if str(g).lower() not in PLACEHOLDERS else "" for g in group]

    filled = Counter([v for v in values if v.strip()]).most_common()

    count = len(values)
    blanks = count - sum(f[1] for f in filled)

    match filled:
        # Nobody chose a value
        case []:
            note = "{} {} {} {} blank".format(
                P("The", count), count, P("record", count), P("is", count)
            )
            return cell.empty(note=note)

        # Everyone chose the same value
        case [f0] if f0[1] > 1 and f0[1] == count:
            note = "Unanimous match, {} of {} {}".format(
                f0[0][1], count, P("record", count)
            )
            return cell.ok(note=note, value=f0[0])

        # It was a tie for the values chosen
        case [f0, f1, *_] if f0[1] > 1 and f0[1] == f1[1]:
            note = "Match is a tie, {} of {} {} with {} {}".format(
                f0[1], count, P("record", count), blanks, P("blank", blanks)
            )
            return cell.ok(note=note, value=f0[0])

        # We have a winner
        case [f0, *_] if f0[1] > 1:
            note = "Match, {} of {} {} with {} {}".format(
                filled[0][1], count, P("record", count), blanks, P("blank", blanks)
            )
            return cell.ok(note=note, value=f0[0])

        # Only one person chose a value
        case [f0] if f0[1] == 1:
            note = "Only 1 transcript in {} {}".format(count, P("record", count))
            return cell.warning(note=note, value=f0[0])

        # Everyone picked a different value
        case _:
            note = "No select match on {} {} with {} {}".format(
                count, P("record", count), blanks, P("blank", blanks)
            )
            return cell.error(note=note)
