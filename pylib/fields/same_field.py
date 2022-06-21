"""Reconcile a group where all values are supposed to be the same."""
from dataclasses import dataclass

from pylib import cell
from pylib.fields.base_field import BaseField


@dataclass(kw_only=True)
class SameField(BaseField):
    value: str = ""

    def to_dict(self):
        return {self.label: self.value}


def reconcile(group, args=None):  # noqa pylint: disable=unused-argument
    values = list(group.astype(str))

    if all(v == values[0] for v in values):
        return cell.no_flag(no_label=values[0])

    value = ",".join(values)
    return cell.error(no_label=value)
