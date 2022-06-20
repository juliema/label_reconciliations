"""Get mean and range for the group. Handle non-numeric characters."""
import statistics as stats

from .. import cell
from ..util import P


def reconcile(group, args=None):  # noqa
    values = [g for g in group]

    numbers = []
    for value in values:
        try:
            numbers.append(float(value))
        except ValueError:
            pass

    if not numbers:
        note = "There are no numbers in {} {}".format(
            len(values), P("record", len(values))
        )
        return cell.empty(note=note)

    note = "There {} {} {} in {} {}".format(
        P("is", len(numbers)),
        len(numbers),
        P("number", len(numbers)),
        len(values),
        P("record", len(values)),
    )

    mean = stats.mean(numbers)

    return cell.ok(note=note, mean=mean, min=min(numbers), max=max(numbers))