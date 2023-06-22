from dataclasses import dataclass
from typing import Any

from pylib.fields.base_field import BaseField


@dataclass(kw_only=True)
class NoOpField(BaseField):
    value: str = ""

    def to_dict(self, reconciled=False, add_note=False) -> dict[str, Any]:
        field_dict = {} if reconciled else {self.name: self.value}
        return self.decorate_dict(field_dict, add_note)

    @classmethod
    def reconcile(cls, group, row_count, args=None):
        return cls.copy(group)
