from dataclasses import dataclass
from typing import Any

from pylib.fields.base_field import BaseField


@dataclass(kw_only=True)
class NoOpField(BaseField):
    value: str = ""

    def to_unreconciled_dict(self) -> dict[str, Any]:
        return {self.name: self.value}

    def to_reconciled_dict(self, add_note=False) -> dict[str, Any]:
        return {self.name: ""}

    @classmethod
    def reconcile(cls, group, args=None):
        return cls()
