"""Reconcile points."""
import json
import statistics as stats

from .. import cell
from ..util import P


def reconcile(group, args=None):  # noqa
    raw_points = [json.loads(ln) for ln in group]

    points = [ln for ln in raw_points if ln.get("x")]

    raw_count = len(raw_points)
    count = len(points)

    if not count:
        note = f'There are no points in {raw_count} {P("records", raw_count)}.'
        return cell.empty(note=note)

    note = (
        f'There {P("was", count)} {count} '
        f'{P("point", raw_count)} in {raw_count} {P("record", raw_count)}'
    )

    x = stats.mean([ln["x"] for ln in points])
    y = stats.mean([ln["y"] for ln in points])

    return cell.ok(note=note, x=x, y=y)
