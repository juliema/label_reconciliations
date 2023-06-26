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
    BoxField,
    HighlightField,
    LengthField,
    MarkIndexField,
    PolygonField,
    PointField,
    SelectField,
    TextField,
]
AnyField = Union[NoOpField, SameField, TaskField]


@dataclass
class Row:
    fields: list[AnyField] = field_default(default_factory=list)

    def __getitem__(self, key):
        return next(f for f in self.fields if f.field_name == key)

    def __iter__(self):
        yield from self.fields

    def __iadd__(self, other):
        self.fields += other.fields if isinstance(other, Row) else other
        return self

    def __len__(self):
        return len(self.fields)

    def append(self, field: AnyField):
        self.fields.append(field)

    @property
    def tasks(self):
        return [f for f in self.fields if isinstance(f, TaskField)]

    def to_dict(self, add_note=False, reconciled=False) -> dict[str, Any]:
        suffixes = defaultdict(int)

        row_dict = {}

        for field in self.fields:
            if isinstance(field, TaskField) and not field.freeze:
                suffixes[field.name_group] += 1
                field.suffix = suffixes[field.name_group]

            field_dict = field.to_dict(reconciled)

            if add_note:
                field.decorate_dict(field_dict)

            row_dict |= field_dict

        return row_dict
