"""Reconcile a box annotation."""
import json
from statistics import mean

from pylib import cell
from pylib.utils import P

RAW_DATA_TYPE = "json"
DATA_WIDTH = 4


def reconcile(group, args=None):  # noqa pylint: disable=unused-argument
    raw_boxes = [json.loads(b) for b in group]

    overlaps = [0] * len(raw_boxes)
    for i, box1 in enumerate(raw_boxes[:-1]):
        for j, box2 in enumerate(raw_boxes[1:], 1):
            if overlaps_2d(box1, box2):
                overlaps[i] = 1
                overlaps[j] = 1
    boxes = [b for i, b in enumerate(raw_boxes) if overlaps[i]]

    if not boxes:
        note = (
            f"There are no overlapping boxes in {len(raw_boxes)} "
            f"{P('record', len(raw_boxes))}"
        )
        return cell.all_blank(note=note)

    count = len(boxes)

    note = (
        f"There {P('was', count)} {count} overlapping {P('box', count)} "
        f"in {len(raw_boxes)} {P('record', len(raw_boxes))}"
    )

    return cell.ok(
        note=note,
        left=round(mean(b["left"] for b in boxes)),
        right=round(mean(b["right"] for b in boxes)),
        top=round(mean(b["top"] for b in boxes)),
        bottom=round(mean(b["bottom"] for b in boxes)),
    )


def overlaps_2d(box1, box2):
    """Check if the boxes overlap."""
    return overlaps_1d(box1, box2, "left", "right") and overlaps_1d(
        box1, box2, "top", "bottom"
    )


def overlaps_1d(seg1, seg2, min_edge, max_edge):
    """Check if the line segments overlap."""
    return seg1[min_edge] <= seg2[max_edge] and seg2[min_edge] <= seg1[max_edge]
