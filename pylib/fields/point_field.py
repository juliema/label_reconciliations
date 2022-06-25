"""Reconcile points."""
import statistics as stats
from dataclasses import dataclass

from pylib.fields.base_field import BaseField
from pylib.result import Result
from pylib.result import sort_results
from pylib.utils import P


@dataclass(kw_only=True)
class PointField(BaseField):
    x: float = 0.0
    y: float = 0.0

    def to_dict(self):
        return self.round("x", "y")

    @classmethod
    def reconcile(cls, group, _=None):
        row_count = len(group)
        if not group:
            note = f"There are no points in {row_count} {P('record', len(group))}"
            return cls(note=note, result=Result.ALL_BLANK)

        count = len(group)

        note = (
            f'There {P("was", count)} {count} '
            f'{P("point", row_count)} in {row_count} {P("record", row_count)}'
        )

        x = round(stats.mean([ln.x for ln in group]))
        y = round(stats.mean([ln.y for ln in group]))

        return cls(note=note, x=x, y=y, result=Result.OK)

    @staticmethod
    def results():
        return sort_results(Result.ALL_BLANK, Result.OK)
