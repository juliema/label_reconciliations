"""Reconcile line lengths.

Note: I am assuming that length notations are required. If this is no longer the case
      you will need to edit this file.
"""
import math
import re
import statistics as stats
from dataclasses import dataclass

from pylib import result
from pylib.fields.base_field import BaseField
from pylib.result import Result
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
            dict_ = self.round("pixel_length", digits=2)
            if not self.is_scale:
                dict_[self.header(f"length {self.units}")] = round(self.length, 2)
        return dict_

    @classmethod
    def reconcile(cls, group, _=None):
        count = len(group)

        note = f'There {P("is", count)} {count} length {P("record", count)}'

        pix = [math.sqrt((ln.x1 - ln.x2) ** 2 + (ln.y1 - ln.y2) ** 2) for ln in group]
        pix = round(stats.mean(pix), 2)

        if match := SCALE_RE.search(group[0].key):
            units = match.group("units")
            factor = float(match.group("scale")) / pix
            is_scale = True
        else:
            units = ""
            factor = 0.0
            is_scale = False

        return cls(
            note=note,
            result=Result.OK,
            pixel_length=pix,
            factor=factor,
            units=units,
            is_scale=is_scale,
        )

    @staticmethod
    def reconcile_row(reconciled_row, args=None):
        """Calculate lengths using units and pixel_lengths."""
        ruler = LengthField.find_ruler(reconciled_row)

        if not ruler:
            return

        LengthField.calculate_lengths(reconciled_row, ruler)

    @staticmethod
    def calculate_lengths(reconciled_row, ruler):
        for field in reconciled_row.values():
            if isinstance(field, LengthField) and not field.is_scale:
                field.length = round(field.pixel_length * ruler.factor, 2)
                field.units = ruler.units

    @staticmethod
    def find_ruler(reconciled_row):
        return next(
            (f for f in reconciled_row.values() if getattr(f, "is_scale", False)),
            None,
        )

    @staticmethod
    def results():
        return result.sort_results(Result.ALL_BLANK, Result.OK)
