from dataclasses import dataclass, field as field_default
from collections import defaultdict
from typing import Any, Union

from pylib.fields.box_field import BoxField
from pylib.fields.highlighter_field import HighlightField
from pylib.fields.length_field import LengthField
from pylib.fields.mark_index_field import MarkIndexField
from pylib.fields.noop_field import NoOpField
from pylib.fields.point_field import PointField
from pylib.fields.polygon_field import PolygonField
from pylib.fields.same_field import SameField
from pylib.fields.select_field import SelectField
from pylib.fields.text_field import TextField

TaskField = Union[
    BoxField, HighlightField, LengthField, MarkIndexField, PolygonField, PointField,
    SelectField, TextField
]
AnyField = Union[NoOpField, SameField, TaskField]


@dataclass
class Row:
    counts: dict[str, int] = field_default(default_factory=lambda : defaultdict(int))
    fields: dict[str, AnyField] = field_default(default_factory=dict)

    def append(self, field: AnyField):
        self.counts[field.name_group] += 1
        field.suffix = self.counts[field.name_group]
        self.fields[field.field_name] = field

    def to_dict(self, add_note=False, reconciled=False) -> dict[str, Any]:
        row_dict = {}

        for field_name, field in self.fields.items():
            field_dict = field.to_dict(reconciled)
            if add_note:
                field.add_note(field_dict)
            row_dict |= field_dict

        return row_dict
