"""Reconcile points.

Note: I am assuming that point notations are required. This may not always be the case.
      In that case we need to edit this class.
"""
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
        count = len(group)

        note = f'There {P("is", count)} {count} point {P("record", count)}'

        x = round(stats.mean([ln.x for ln in group]))
        y = round(stats.mean([ln.y for ln in group]))

        return cls(note=note, x=x, y=y, result=Result.OK)

    @staticmethod
    def results():
        return sort_results(Result.ALL_BLANK, Result.OK)
