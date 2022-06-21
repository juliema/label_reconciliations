"""Reconcile points."""
import json
import statistics as stats

from pylib import cell
from pylib.utils import P

RAW_DATA_TYPE = "json"
DATA_WIDTH = 2


def reconcile(group, args=None):  # noqa pylint: disable=unused-argument
    raw_points = [json.loads(ln) for ln in group]

    points = [ln for ln in raw_points if ln.get("x")]

    raw_count = len(raw_points)
    count = len(points)

    if not count:
        note = f'There are no points in {raw_count} {P("records", raw_count)}.'
        return cell.all_blank(note=note)

    note = (
        f'There {P("was", count)} {count} '
        f'{P("point", raw_count)} in {raw_count} {P("record", raw_count)}'
    )

    x = round(stats.mean([ln["x"] for ln in points]))
    y = round(stats.mean([ln["y"] for ln in points]))

    return cell.ok(note=note, x=x, y=y)
