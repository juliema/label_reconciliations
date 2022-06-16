"""
Reconcile select lists.

Classifications are chosen from a controlled vocabulary.
"""
from collections import Counter

from ..util import P

PLACEHOLDERS = ["placeholder"]


def reconcile(group, args=None):  # noqa
    values = [str(g) if str(g).lower() not in PLACEHOLDERS else "" for g in group]

    filled = Counter([v for v in values if v.strip()]).most_common()

    count = len(values)
    blanks = count - sum(f[1] for f in filled)

    if not filled:
        reason = "{} {} {} {} blank".format(
            P("The", count), count, P("record", count), P("is", count)
        )
        return reason, ""

    if filled[0][1] > 1 and filled[0][1] == count:
        reason = "Unanimous match, {} of {} {}".format(
            filled[0][1], count, P("record", count)
        )
        return reason, filled[0][0]

    if len(filled) > 1 and filled[0][1] > 1 and filled[0][1] == filled[1][1]:
        reason = "Match is a tie, {} of {} {} with {} {}".format(
            filled[0][1], count, P("record", count), blanks, P("blank", blanks)
        )
        return reason, filled[0][0]

    if filled[0][1] > 1:
        reason = "Match, {} of {} {} with {} {}".format(
            filled[0][1], count, P("record", count), blanks, P("blank", blanks)
        )
        return reason, filled[0][0]

    if len(filled) == 1:
        reason = "Only 1 transcript in {} {}".format(count, P("record", count))
        return reason, filled[0][0]

    reason = "No select match on {} {} with {} {}".format(
        count, P("record", count), blanks, P("blank", blanks)
    )
    return reason, ""
