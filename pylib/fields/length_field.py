import math
import re
import statistics as stats
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from pylib.fields.base_field import BaseField
from pylib.flag import Flag
from pylib.utils import P

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

    def to_dict(self, reconciled=False) -> dict[str, Any]:
        field_dict = {
            self.header("x1"): int(round(self.x1)),
            self.header("y1"): int(round(self.y1)),
            self.header("x2"): int(round(self.x2)),
            self.header("y2"): int(round(self.y2)),
        }

        if reconciled:
            field_dict[self.header("pixel_length")] = round(self.pixel_length, 2)
            if not self.is_scale:
                name = self.header(f"length {self.units}")
                field_dict[name] = round(self.length, 2)

        return field_dict

    @classmethod
    def reconcile(cls, group, row_count, _=None):
        per_column = defaultdict(list)
        for row in group:
            for field in row:
                per_column[field.field_name].append(field)

        reconciled = []

        for field_name, fields in per_column.items():
            reconciled.append(cls.reconcile_column(fields, row_count, field_name))

        cls.adjust_reconciled(reconciled)

        return reconciled

    @classmethod
    def reconcile_column(cls, group, row_count, field_name):
        note = (
            f'There {P("is", len(group))} {len(group)} of {row_count} '
            f'length {P("record", row_count)}'
        )

        x1 = round(stats.mean([ln.x1 for ln in group]))
        y1 = round(stats.mean([ln.y1 for ln in group]))
        x2 = round(stats.mean([ln.x2 for ln in group]))
        y2 = round(stats.mean([ln.y2 for ln in group]))

        pix_len = round(math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2), 2)

        if match := SCALE_RE.search(field_name):
            units = match.group("units")
            factor = float(match.group("scale")) / pix_len if pix_len != 0 else 0.0
            is_scale = True
        else:
            units = ""
            factor = 0.0
            is_scale = False

        return cls.like(
            group,
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
    def adjust_reconciled(reconciled):
        """Calculate lengths using units and pixel_lengths."""
        ruler = next((f for f in reconciled if f.is_scale), None)

        if not ruler:
            return

        for field in reconciled:
            if not field.is_scale:
                field.length = round(field.pixel_length * ruler.factor, 2)
            field.units = ruler.units
