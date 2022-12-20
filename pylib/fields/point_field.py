import statistics as stats
from dataclasses import dataclass
from typing import Any

from pylib.fields.base_field import BaseField
from pylib.flag import Flag
from pylib.utils import P


@dataclass(kw_only=True)
class PointField(BaseField):
    x: float = 0.0
    y: float = 0.0

    def to_unreconciled_dict(self) -> dict[str, Any]:
        return {
            self.header("x"): int(round(self.x)),
            self.header("y"): int(round(self.y)),
        }

    def to_reconciled_dict(self, add_note=False) -> dict[str, Any]:
        as_dict = self.to_unreconciled_dict()
        return self.add_note(as_dict, add_note)

    @classmethod
    def reconcile(cls, group, _=None):
        count = len(group)
        use = [g for g in group if not g.is_padding]

        note = (
            f'There {P("is", len(use))} {len(use)} of {count}'
            f'point {P("record", count)}'
        )

        x = round(stats.mean([ln.x for ln in use]))
        y = round(stats.mean([ln.y for ln in use]))

        return cls(note=note, x=x, y=y, flag=Flag.OK)
