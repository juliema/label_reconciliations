from typing import Union

from pylib.fields.box_field import BoxField
from pylib.fields.length_field import LengthField
from pylib.fields.noop_field import NoOpField
from pylib.fields.point_field import PointField
from pylib.fields.same_field import SameField
from pylib.fields.select_field import SelectField
from pylib.fields.text_field import TextField


ALL_FIELDS = Union[
    BoxField, LengthField, NoOpField, PointField, SameField, SelectField, TextField
]

RECONCILABLE_FIELDS = Union[
    BoxField, LengthField, PointField, SelectField, TextField
]


def reconcilable_field(field):
    return isinstance(field, RECONCILABLE_FIELDS)
