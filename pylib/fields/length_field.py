import math
import re
import statistics as stats
from dataclasses import dataclass
from typing import Any

from pylib.fields.base_field import BaseField
from pylib.flag import Flag
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

    def to_dict(self) -> dict[str, Any]:
        return {
            self.name("x1"): round(self.x1),
            self.name("y1"): round(self.y1),
            self.name("x2"): round(self.x2),
            self.name("y2"): round(self.y2),
        }

    def to_unreconciled_dict(self) -> dict[str, Any]:
        return self.to_dict()

    def to_reconciled_dict(self, add_note=False) -> dict[str, Any]:
        as_dict = self.to_dict()
        as_dict[self.name("pixel_length")] = round(self.pixel_length, 2)
        if not self.is_scale:
            name = self.name(f"length {self.units}")
            as_dict[name] = round(self.length, 2)
        return self.add_note(as_dict, add_note)

    @classmethod
    def reconcile(cls, group, _=None):
        count = len(group)
        use = [g for g in group if not g.is_padding]

        note = (
            f'There {P("is", len(use))} {len(use)} of {count}'
            f'length {P("record", count)}'
        )

        x1 = round(stats.mean([ln.x1 for ln in use]))
        y1 = round(stats.mean([ln.y1 for ln in use]))
        x2 = round(stats.mean([ln.x2 for ln in use]))
        y2 = round(stats.mean([ln.y2 for ln in use]))

        pix_len = round(math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2), 2)

        if match := SCALE_RE.search(use[0].key):
            units = match.group("units")
            factor = float(match.group("scale")) / pix_len
            is_scale = True
        else:
            units = ""
            factor = 0.0
            is_scale = False

        return cls(
            note=note,
            flag=Flag.OK,
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
