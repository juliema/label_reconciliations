"""A table of reconciled or unreconciled data."""
from dataclasses import dataclass
from dataclasses import field
from itertools import groupby

import pandas as pd

from pylib.fields.base_field import BaseField
from pylib.row import Row


@dataclass
class Table:
    rows: list[Row[BaseField]] = field(default_factory=list)
    is_reconciled: bool = False

    def append(self, row):
        self.rows.append(row)

    @property
    def has_rows(self):
        return bool(self.rows)

    def to_unreconciled_csv(self, path):
        rows = []
        for row in self.rows:
            data = {}
            for field_ in row.values():
                data |= field_.to_dict()
            rows.append(data)
        df = pd.DataFrame(rows)
        df.to_csv(path, index=False)

    @classmethod
    def reconcile(cls, unreconciled, args):
        """Reconcile a data frame and return a new one."""
        rows = sorted(
            unreconciled.rows,
            key=lambda r: (r[args.group_by].value, r[args.row_key].value),
        )
        groups = groupby(rows, key=lambda r: r[args.group_by].value)
        reconciled = cls(is_reconciled=True)
        for subject_id, row_group in groups:
            row = Row()
            row_group = list(row_group)
            print(len(row_group))
            for key in Row.all_keys(row_group):
                field_group = [g[key] for g in row_group if g[key]]
                field_type = type(field_group[0])
                cell = field_type.reconcile(field_group, len(row_group), args)
                cell.is_reconciled = True
                row.add_field(key, cell)
            reconciled.append(row)

        return reconciled
