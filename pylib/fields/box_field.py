"""Reconcile a box annotation.

Note: I am assuming that box notations are required. If this is no longer the case you
      will need to edit this file.
"""
from dataclasses import dataclass
from statistics import mean

from pylib.fields.base_field import BaseField
from pylib.result import Result
from pylib.result import sort_results
from pylib.utils import P


@dataclass(kw_only=True)
class BoxField(BaseField):
    left: float = 0.0
    right: float = 0.0
    top: float = 0.0
    bottom: float = 0.0
    use: bool = True

    def to_dict(self):
        return self.round("left", "right", "top", "bottom")

    @classmethod
    def reconcile(cls, group, _=None):
        count = len(group)
        use = [g for g in group if g.use]

        note = f"There {P('is', count)} {count} box {P('record', count)}"

        return cls(
            note=note,
            result=Result.OK,
            left=round(mean(b.left for b in use)),
            right=round(mean(b.right for b in use)),
            top=round(mean(b.top for b in use)),
            bottom=round(mean(b.bottom for b in use)),
        )

    @staticmethod
    def results():
        return sort_results(Result.ALL_BLANK, Result.NO_MATCH, Result.OK)

    @classmethod
    def pad_group(cls, group, length):
        while len(group) < length:
            group.append(cls(use=False))
        return group


def overlaps_2d(box1, box2):
    """Check if the boxes overlap."""
    horiz = box1.right >= box2.left and box2.right >= box1.left
    vert = box1.bottom >= box2.top and box2.bottom >= box1.top
    return horiz and vert
