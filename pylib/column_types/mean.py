"""Get mean and range for the group. Handle non-numeric characters."""
import statistics as stats

from pylib import cell
from pylib.utils import P


def reconcile(group, args=None):  # noqa pylint: disable=unused-argument
    values = list(group)
    numbers = []
    for value in values:
        try:
            numbers.append(float(value))
        except ValueError:
            pass

    if not numbers:
        note = f"There are no numbers in {len(values)} {P('record', len(values))}"
        return cell.empty(note=note)

    note = (
        f"There {P('is', len(numbers))} {len(numbers)} {P('number', len(numbers))} "
        f"in {len(values)} {P('record', len(values))}"
    )

    mean = stats.mean(numbers)

    return cell.ok(note=note, mean=mean, min=min(numbers), max=max(numbers))
