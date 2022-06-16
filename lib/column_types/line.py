"""Reconcile line lengths."""
import json
import math
import re
import statistics as stats

from ..util import P


SCALE_RE = re.compile(
    r"(?P<scale> [0-9.]+ ) \s* (?P<units> (mm|cm|dm|m) ) \b",
    flags=re.VERBOSE | re.IGNORECASE,
)


def reconcile(group, args=None):  # noqa
    raw_lines = [json.loads(ln) for ln in group]

    lines = [ln for ln in raw_lines if ln.get("x1")]

    raw_count = len(raw_lines)
    count = len(lines)

    if not count:
        return f'There are no lines in {raw_count} {P("records", raw_count)}.', {}

    x1 = round(stats.mean([ln["x1"] for ln in lines]))
    y1 = round(stats.mean([ln["y1"] for ln in lines]))
    x2 = round(stats.mean([ln["x2"] for ln in lines]))
    y2 = round(stats.mean([ln["y2"] for ln in lines]))

    reason = (
        f'There {P("was", count)} {count} '
        f'{P("line", raw_count)} in {raw_count} {P("record", raw_count)}'
    )
    line = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}

    return reason, json.dumps(line)


def adjust_reconciled_columns(reconciled, column_types):
    """Split line results into separate Mean & Length columns."""
    columns = {
        c
        for c in reconciled.columns
        if column_types.get(c, {"type": ""})["type"] == "line"
    }

    scale = [c for c in columns if re.search(SCALE_RE, c)]

    if len(scale) != 1:
        return reconciled

    scale = scale[0]
    match = re.search(SCALE_RE, scale)
    factor = float(match.group("scale"))
    if factor != 1.0:
        factor = 1.0 / factor

    units = match.group("units")

    reconciled[f"{scale} Length per {units}"] = reconciled[scale].apply(
        lambda x: _get_len(x, factor)
    )
    for col in [c for c in columns if not re.search(SCALE_RE, c)]:
        reconciled[f"{col} Length"] = reconciled[col].apply(
            lambda x: _get_len(x, factor)
        )

    reconciled = reconciled.drop(columns, axis="columns")
    return reconciled


def _get_len(value, factor):
    obj = json.loads(value)

    x = obj["x1"] - obj["x2"]
    x *= x

    y = obj["y1"] - obj["y2"]
    y *= y

    dist = math.sqrt(x + y)
    return round(dist * factor)
