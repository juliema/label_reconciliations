from dataclasses import dataclass
from typing import Any

from pylib.flag import Flag

EXPLAIN_SUFFIX = ": Explanation"


@dataclass(kw_only=True)
class BaseField:
    name: str = ""
    note: str = ""
    flag: Flag = Flag.NO_FLAG
    is_padding: bool = False
    reconcilable: bool = True

    def header(self, attr: str) -> str:
        return f"{self.name}: {attr}"

    def to_unreconciled_dict(self) -> dict[str, Any]:
        raise NotImplementedError()

    def to_reconciled_dict(self, add_note=False) -> dict[str, Any]:
        raise NotImplementedError()

    def add_note(self, as_dict: dict[str, Any], add_note: bool) -> dict[str, Any]:
        if add_note:
            as_dict[f"{self.name}{EXPLAIN_SUFFIX}"] = self.note
        return as_dict

    @classmethod
    def reconcile(cls, group, args=None):
        raise NotImplementedError()

    @classmethod
    def pad_group(cls, group, length):
        while len(group) < length:
            group.append(cls(is_padding=True))
        return group

    @staticmethod
    def reconcile_row(reconciled_row, args=None):
        return


