from dataclasses import dataclass
from typing import Any

from pylib.fields.base_field import BaseField
from pylib.flag import Flag


@dataclass(kw_only=True)
class SameField(BaseField):
    value: str = ""
    reconcilable: bool = False

    def to_unreconciled_dict(self) -> dict[str, Any]:
        return {self.name: self.value}

    def to_reconciled_dict(self, add_note=False) -> dict[str, Any]:
        as_dict = self.to_unreconciled_dict()
        if self.flag != Flag.OK:
            as_dict = self.add_note(as_dict, add_note)
        return as_dict

    @classmethod
    def reconcile(cls, group, _=None):
        use = [g for g in group if not g.is_padding]

        if all(g.value == group[0].value for g in use):
            value = group[0].value
            flag = Flag.OK
            note = ""
        else:
            value = ",".join(g.value for g in use)
            flag = Flag.ERROR
            note = f"Not all values are the same: {value}"

        return cls(value=value, flag=flag, note=note)
