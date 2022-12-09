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
    use: bool = True

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
        use = [g for g in group if g.use]

        note = f'There {P("is", count)} {count} length {P("record", count)}'

        x1 = round(stats.mean([ln.x1 for ln in use]))
        y1 = round(stats.mean([ln.y1 for ln in use]))
        x2 = round(stats.mean([ln.x2 for ln in use]))
        y2 = round(stats.mean([ln.y2 for ln in use]))

        pix_len = round(math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2), 2)

        if match := SCALE_RE.search(use[0].key):
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

    @classmethod
    def pad_group(cls, group, length):
        while len(group) < length:
            group.append(cls(use=False))
        return group

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
