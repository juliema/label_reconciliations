"""A table of reconciled or unreconciled data."""
from dataclasses import dataclass
from dataclasses import field

import pandas as pd

from pylib.fields.base_field import BaseField


@dataclass
class Table:
    rows: list[list[BaseField]] = field(default_factory=list)
    is_reconciled: bool = False

    def append(self, row):
        self.rows.append(row)

    @property
    def has_rows(self):
        return bool(self.rows)

    def to_csv(self, path):
        rows = []
        for row in self.rows:
            data = {}
            for field_ in row:
                data |= field_.to_dict()
            rows.append(data)
        df = pd.DataFrame(rows)
        df.to_csv(path, index=False)

    @classmethod
    def reconcile(cls, args):
        return cls()
