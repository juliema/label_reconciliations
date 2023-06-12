from dataclasses import dataclass
from typing import Any

from pylib.fields.base_field import BaseField
from pylib.fields.controlled_vocab import controlled_vocab


@dataclass(kw_only=True)
class SelectField(BaseField):
    value: str = ""

    def to_unreconciled_dict(self) -> dict[str, Any]:
        return {self.name: self.value}

    def to_reconciled_dict(self, add_note=False) -> dict[str, Any]:
        as_dict = self.to_unreconciled_dict()
        return self.add_note(as_dict, add_note)

    @classmethod
    def reconcile(cls, group, row_count, _=None):
        return controlled_vocab(cls, group, row_count)
