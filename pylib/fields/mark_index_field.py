from dataclasses import dataclass
from typing import Any

from pylib.fields.base_field import BaseField, controlled_vocab


@dataclass(kw_only=True)
class MarkIndexField(BaseField):
    value: str = ""
    index: int = -1

    def to_unreconciled_dict(self) -> dict[str, Any]:
        return {self.name: self.value}

    def to_reconciled_dict(self, add_note=False) -> dict[str, Any]:
        as_dict = self.to_unreconciled_dict()
        return self.add_note(as_dict, add_note)

    @classmethod
    def reconcile(cls, group, _=None):
        return controlled_vocab(cls, group)
