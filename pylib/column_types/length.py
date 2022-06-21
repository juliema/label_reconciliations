"""Reconcile line lengths."""
# noqa pylint: disable=invalid-name
import json
import math
import re
import statistics as stats

from pylib import cell
from pylib.utils import P

RAW_DATA_TYPE = "json"
DATA_WIDTH = 5

SCALE_RE = re.compile(
    r"(?P<scale> [0-9.]+ ) \s* (?P<units> (mm|cm|dm|m) ) \b",
    flags=re.VERBOSE | re.IGNORECASE,
)


def reconcile(group, args=None):  # noqa pylint: disable=unused-argument
    raw_lines = [json.loads(ln) for ln in group]

    lines = [ln for ln in raw_lines if ln.get("x1")]

    raw_count = len(raw_lines)
    count = len(lines)

    if not count:
        note = f'There are no lines in {raw_count} {P("records", raw_count)}.'
        return cell.all_blank(note=note)

    note = (
        f'There {P("was", count)} {count} '
        f'{P("line", raw_count)} in {raw_count} {P("record", raw_count)}'
    )

    x1 = round(stats.mean([ln["x1"] for ln in lines]))
    y1 = round(stats.mean([ln["y1"] for ln in lines]))
    x2 = round(stats.mean([ln["x2"] for ln in lines]))
    y2 = round(stats.mean([ln["y2"] for ln in lines]))

    return cell.ok(
        note=note,
        x1=x1,
        y1=y1,
        x2=x2,
        y2=y2,
        length_pixels=round(math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2), 2),
    )


def reconcile_row(reconciled_row, args=None):  # noqa pylint: disable=unused-argument
    """Calculate lengths using units and pixel_lengths."""
    units, factor = None, None
    for field, value in reconciled_row.items():
        if field.find("length_pixels") > -1 and (match := SCALE_RE.search(field)):
            units = match.group("units")
            factor = float(match.group("scale")) / value
            break

    if not units:
        return

    new_field = {}
    for key, value in reconciled_row.items():
        if key.find("length_pixels") > -1 and not SCALE_RE.search(key):
            field = key.replace("pixels", units)
            new_field[field] = round(value * factor, 2)

    reconciled_row |= new_field
