from dataclasses import dataclass
from typing import Any

from pylib.fields.base_field import BaseField
from pylib.fields.controlled_vocab import controlled_vocab


@dataclass(kw_only=True)
class SelectField(BaseField):
    value: str = ""

    def to_dict(self, reconciled=False) -> dict[str, Any]:
        field_dict = {self.header(): self.value}
        return field_dict

    @classmethod
    def reconcile(cls, group, row_count, args=None):
        return controlled_vocab(cls, group, row_count)
