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

    def to_dict(self) -> dict[str, Any]:
        return {
            self.name("left"): round(self.left, 0),
            self.name("right"): round(self.right, 0),
            self.name("top"): round(self.top, 0),
            self.name("bottom"): round(self.bottom, 0),
        }

    def to_unreconciled_dict(self) -> dict[str, Any]:
        return self.to_dict()

    def to_reconciled_dict(self, add_note=False) -> dict[str, Any]:
        as_dict = self.to_dict()
        return self.add_note(as_dict, add_note)

    @classmethod
    def reconcile(cls, group, _=None):
        count = len(group)
        use = [g for g in group if not g.is_padding]

        note = f"There {P('is', count)} {count} box {P('record', count)}"

        return cls(
            note=note,
            flag=Flag.OK,
            left=round(mean(b.left for b in use)),
            right=round(mean(b.right for b in use)),
            top=round(mean(b.top for b in use)),
            bottom=round(mean(b.bottom for b in use)),
        )
