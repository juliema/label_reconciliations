"""Get mean and range for the group. Handle non-numeric characters."""
import statistics as stats
from dataclasses import dataclass

from pylib import cell
from pylib.fields.base_field import BaseField
from pylib.utils import P


@dataclass(kw_only=True)
class MeanField(BaseField):
    mean: float
    min: float
    max: float

    def to_dict(self):
        return self.round("mean", "min", "max")


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
        return cell.all_blank(note=note)

    note = (
        f"There {P('is', len(numbers))} {len(numbers)} {P('number', len(numbers))} "
        f"in {len(values)} {P('record', len(values))}"
    )

    mean = stats.mean(numbers)

    return cell.ok(note=note, mean=mean, min=min(numbers), max=max(numbers))
