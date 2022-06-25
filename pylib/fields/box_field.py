"""Reconcile a box annotation."""
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

    def to_dict(self):
        return self.round("left", "right", "top", "bottom")

    @classmethod
    def reconcile(cls, group, _=None):
        row_count = len(group)
        count = row_count

        note = (
            f"There {P('is', count)} {count} {P('box', count)} "
            f"in {row_count} {P('record', row_count)}"
        )

        print(
            cls(
                note=note,
                result=Result.OK,
                left=round(mean(b.left for b in group)),
                right=round(mean(b.right for b in group)),
                top=round(mean(b.top for b in group)),
                bottom=round(mean(b.bottom for b in group)),
            )
        )

        return cls(
            note=note,
            result=Result.OK,
            left=round(mean(b.left for b in group)),
            right=round(mean(b.right for b in group)),
            top=round(mean(b.top for b in group)),
            bottom=round(mean(b.bottom for b in group)),
        )

    @staticmethod
    def results():
        return sort_results(Result.ALL_BLANK, Result.NO_MATCH, Result.OK)


def overlaps_2d(box1, box2):
    """Check if the boxes overlap."""
    horiz = box1.right >= box2.left and box2.right >= box1.left
    vert = box1.bottom >= box2.top and box2.bottom >= box1.top
    return horiz and vert
