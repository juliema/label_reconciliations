from collections import UserDict
from dataclasses import dataclass
from dataclasses import field

from pylib.fields.base_field import BaseField


@dataclass
class Row:
    cells: dict[str, BaseField] = field(default_factory=dict)

    def add_cell(self, header, cell):
        self.cells[header] = cell


class OldRow(UserDict):
    def add_field(self, key, field_):
        field_.key = key
        self[key] = field_
