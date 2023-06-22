from dataclasses import dataclass
from typing import Any

from pylib.fields.base_field import BaseField
from pylib.flag import Flag


@dataclass(kw_only=True)
class SameField(BaseField):
    value: str = ""

    def to_dict(self, reconciled=False, add_note=False) -> dict[str, Any]:
        field_dict = {self.name: self.value}
        return self.decorate_dict(field_dict, add_note)

    def add_note(self, field_dict: dict[str, Any]) -> dict[str, Any]:
        if self.flag != Flag.OK:
            field_dict = self.add_note(field_dict)
        return field_dict

    @classmethod
    def reconcile(cls, group, row_count, args=None):
        use = [g for g in group if g is not None]

        if all(g.value == group[0].value for g in use):
            value = group[0].value
            flag = Flag.OK
            note = ""
        else:
            value = ",".join(g.value for g in use)
            flag = Flag.ERROR
            note = f"Not all values are the same: {value}"

        return cls(value=value, flag=flag, note=note)
