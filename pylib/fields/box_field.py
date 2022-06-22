"""Reconcile a box annotation."""
from dataclasses import dataclass
from statistics import mean

from pylib.fields.base_field import BaseField
from pylib.fields.base_field import Flag
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
    def reconcile(cls, group, row_count, _=None):
        if not group:
            note = f"There are no boxes in {row_count} {P('record', len(group))}"
            return cls(note=note, flag=Flag.ALL_BLANK)

        overlaps = [0] * len(group)
        for i, box1 in enumerate(group[:-1]):
            for j, box2 in enumerate(group[1:], 1):
                if overlaps_2d(box1, box2):
                    overlaps[i] = 1
                    overlaps[j] = 1
        boxes = [b for i, b in enumerate(group) if overlaps[i]]

        if not boxes:
            note = (
                f"There are no overlapping boxes in {len(group)} "
                f"{P('record', len(group))}"
            )
            return cls(note=note, flag=Flag.NO_MATCH)

        count = len(boxes)

        note = (
            f"There {P('was', count)} {count} overlapping {P('box', count)} "
            f"in {len(group)} {P('record', len(group))}"
        )

        return cls(
            note=note,
            flag=Flag.OK,
            left=round(mean(b["left"] for b in boxes)),
            right=round(mean(b["right"] for b in boxes)),
            top=round(mean(b["top"] for b in boxes)),
            bottom=round(mean(b["bottom"] for b in boxes)),
        )


def overlaps_2d(box1, box2):
    """Check if the boxes overlap."""
    return overlaps_1d(box1.left, box1.right, box2.left, box2.right) and overlaps_1d(
        box1.top, box1.bottom, box2.top, box2.bottom
    )


def overlaps_1d(seg1_lo, seg1_hi, seg2_lo, seg2_hi):
    """Check if the line segments overlap."""
    return seg1_lo <= seg2_hi and seg2_lo <= seg1_hi
