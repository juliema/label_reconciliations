"""Reconcile line lengths."""
# noqa pylint: disable=invalid-name
import math
import re
import statistics as stats
from dataclasses import dataclass

from pylib.fields.base_field import BaseField
from pylib.result import Result
from pylib.result import sort_results
from pylib.utils import P

PIX_LEN = "length pixels"

SCALE_RE = re.compile(
    r"(?P<scale> [0-9.]+ ) \s* (?P<units> (mm|cm|dm|m) ) \b",
    flags=re.VERBOSE | re.IGNORECASE,
)


@dataclass(kw_only=True)
class LengthField(BaseField):
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    pixel_length: float = 0.0
    length: float = 0.0
    factor: float = 0.0
    units: str = ""
    is_scale: bool = False

    def to_dict(self):
        dict_ = self.round("x1", "y1", "x2", "y2")
        if self.is_reconciled:
            dict_ |= self.round("pixel_length", digits=2)
            if not self.is_scale:
                dict_[self.header(f"length {self.units}")] = round(self.length, 2)
        return dict_

    @classmethod
    def reconcile(cls, group, row_count, _=None):
        if not group:
            note = f'There are no lines in {row_count} {P("records", row_count)}.'
            return cls(note=note, result=Result.ALL_BLANK)

        note = (
            f'There {P("was", len(group))} {len(group)} '
            f'{P("line", len(group))} in {row_count} {P("record", row_count)}'
        )

        x1 = round(stats.mean([ln.x1 for ln in group]))
        y1 = round(stats.mean([ln.y1 for ln in group]))
        x2 = round(stats.mean([ln.x2 for ln in group]))
        y2 = round(stats.mean([ln.y2 for ln in group]))

        pix_len = round(math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2), 2)

        if match := SCALE_RE.search(group[0].key):
            units = match.group("units")
            factor = float(match.group("scale")) / pix_len
            is_scale = True
        else:
            units = ""
            factor = 0.0
            is_scale = False

        return cls(
            note=note,
            result=Result.OK,
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            pixel_length=pix_len,
            factor=factor,
            units=units,
            is_scale=is_scale,
        )

    @staticmethod
    def reconcile_row(reconciled_row, args=None):
        """Calculate lengths using units and pixel_lengths."""
        ruler = None

        for key, field in reconciled_row.items():
            if isinstance(field, LengthField) and field.is_scale:
                ruler = field
                break

        if not ruler:
            return

        for key, field in reconciled_row.items():
            if isinstance(field, LengthField) and not field.is_scale:
                field.length = round(field.pixel_length * ruler.factor, 2)
                field.units = ruler.units

    @staticmethod
    def results():
        return sort_results(Result.ALL_BLANK, Result.OK)
