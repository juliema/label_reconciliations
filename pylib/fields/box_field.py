from dataclasses import dataclass
from statistics import mean
from typing import Any

from pylib.fields.base_field import BaseField
from pylib.flag import Flag
from pylib.utils import P


@dataclass(kw_only=True)
class BoxField(BaseField):
    left: float = 0.0
    right: float = 0.0
    top: float = 0.0
    bottom: float = 0.0

    def to_unreconciled_dict(self) -> dict[str, Any]:
        return {
            self.header("left"): int(round(self.left)),
            self.header("right"): int(round(self.right)),
            self.header("top"): int(round(self.top)),
            self.header("bottom"): int(round(self.bottom)),
        }

    def to_reconciled_dict(self, add_note=False) -> dict[str, Any]:
        as_dict = self.to_unreconciled_dict()
        return self.add_note(as_dict, add_note)

    @classmethod
    def reconcile(cls, group, row_count, _=None):
        use = [g for g in group if g is not None]

        note = f"There {P('is', row_count)} {row_count} box {P('record', row_count)}"

        return cls(
            note=note,
            flag=Flag.OK,
            left=round(mean(b.left for b in use)),
            right=round(mean(b.right for b in use)),
            top=round(mean(b.top for b in use)),
            bottom=round(mean(b.bottom for b in use)),
        )
