"""Reconcile points."""
import json
import statistics as stats

from ..util import P


def reconcile(group, args=None):  # noqa
    raw_points = [json.loads(ln) for ln in group]

    points = [ln for ln in raw_points if ln.get("x")]

    raw_count = len(raw_points)
    count = len(points)

    if not count:
        return f'There are no points in {raw_count} {P("records", raw_count)}.', {}

    x = round(stats.mean([ln["x"] for ln in points]))
    y = round(stats.mean([ln["y"] for ln in points]))

    reason = (
        f'There {P("was", count)} {count} '
        f'{P("point", raw_count)} in {raw_count} {P("record", raw_count)}'
    )
    line = {"x": x, "y": y}

    return reason, json.dumps(line)
