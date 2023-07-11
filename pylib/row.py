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
    fields: dict[str, AnyField] = field_default(default_factory=dict)
    suffixes: dict[str, int] = field_default(default_factory=lambda : defaultdict(int))

    def __getitem__(self, key) -> Union[AnyField, None]:
        return self.fields.get(key)

    def __iter__(self):
        yield from self.fields.values()

    def __len__(self):
        return len(self.fields)

    def add(self, field: Union[AnyField, list[AnyField]]):
        fields = field if isinstance(field, list) else [field]
        for field in fields:
            if isinstance(field, TaskField):
                self.suffixes[field.name_group] += 1
                field.suffix = self.suffixes[field.name_group]
            self.fields[field.field_name] = field

    @property
    def tasks(self):
        return [f for f in self.fields.values() if isinstance(f, TaskField)]

    def to_dict(self, add_note=False, reconciled=False) -> dict[str, Any]:

        row_dict = {}

        for field in self.fields.values():

            field_dict = field.to_dict(reconciled)

            if add_note:
                field.decorate_dict(field_dict)

            row_dict |= field_dict

        return row_dict
