from dataclasses import dataclass
from typing import Any

from pylib.flag import Flag


@dataclass(kw_only=True)
class BaseField:
    header: str = ""
    note: str = ""
    flag: Flag = Flag.NO_FLAG
    is_padding: bool = False

    def name(self, attr: str) -> str:
        return f"{self.header}: {attr}"

    def to_unreconciled_dict(self) -> dict[str, Any]:
        raise NotImplementedError()

    def to_reconciled_dict(self, add_note=False) -> dict[str, Any]:
        raise NotImplementedError()

    def add_note(self, as_dict: dict[str, Any], add_note: bool) -> dict[str, Any]:
        if add_note:
            as_dict[f"{self.header}: Explanation"] = self.note
        return as_dict

    @classmethod
    def pad_group(cls, group, length) -> "BaseField":
        while len(group) < length:
            group.append(cls(is_padding=False))
        return group

    @classmethod
    def reconcile(cls, group, args=None):
        raise NotImplementedError()

    @staticmethod
    def reconcile_row(reconciled_row, args=None):
        return
