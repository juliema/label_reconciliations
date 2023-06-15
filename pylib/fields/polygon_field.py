from dataclasses import dataclass, field
from typing import Any

from pylib.fields.base_field import BaseField
# from pylib.flag import Flag
# from pylib.utils import P


@dataclass()
class PolygonPoint:
    x: float = 0.0
    y: float = 0.0


@dataclass(kw_only=True)
class PolygonField(BaseField):
    points: list[PolygonPoint] = field(default_factory=list)

    def to_unreconciled_dict(self) -> dict[str, Any]:
        return {}

    def to_reconciled_dict(self, add_note=False) -> dict[str, Any]:
        return {}

    @classmethod
    def reconcile(cls, group, row_count, _=None):
        return
