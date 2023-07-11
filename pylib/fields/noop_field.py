from dataclasses import dataclass
from typing import Any

from pylib.fields.base_field import BaseField


@dataclass(kw_only=True)
class NoOpField(BaseField):
    value: str = ""

    def to_dict(self, reconciled=False) -> dict[str, Any]:
        field_dict = {} if reconciled else {self.header(): self.value}
        return field_dict

    @classmethod
    def reconcile(cls, group, row_count, args=None):
        return cls.like(group)
