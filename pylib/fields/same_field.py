"""Reconcile a group where all values are supposed to be the same."""
from dataclasses import dataclass

from pylib.fields.base_field import BaseField
from pylib.fields.base_field import Flag


@dataclass(kw_only=True)
class SameField(BaseField):
    value: str = ""

    def to_dict(self):
        return {self.label: self.value}

    @classmethod
    def reconcile(cls, group, args=None):  # noqa pylint: disable=unused-argument
        if all(g.value == group[0].value for g in group):
            value = group[0].value
            flag = Flag.OK
            note = ""
        else:
            value = ",".join(g.value for g in group)
            flag = Flag.ERROR
            note = f"Not all values are the same {value}"

        return cls(value=value, flag=flag, note=note, is_reconciled=True)
