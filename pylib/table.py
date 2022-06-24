"""A table of reconciled or unreconciled data."""
import json
from dataclasses import dataclass
from dataclasses import field
from itertools import groupby

import pandas as pd

from pylib.fields.base_field import BaseField
from pylib.fields.noop_field import NoOpField
from pylib.fields.same_field import SameField
from pylib.result import GOOD
from pylib.row import Row


@dataclass
class Table:
    rows: list[Row[BaseField]] = field(default_factory=list)
    is_reconciled: bool = False

    def __iter__(self):
        return iter(self.rows)

    def __len__(self):
        return len(self.rows)

    def append(self, row):
        self.rows.append(row)

    @property
    def has_rows(self):
        return bool(self.rows)

    def to_csv(self, path):
        if self.is_reconciled:
            rows = self.to_reconciled_records()
        else:
            rows = self.to_unreconciled_records()
        df = pd.DataFrame(rows).fillna("")
        df.to_csv(path, index=False)

    def to_reconciled_records(self):
        """Exclude No Op fields from reconciled output."""
        rows = []
        for row in self.rows:
            data = {}
            for field_ in (f for f in row.values() if not isinstance(f, NoOpField)):
                data |= field_.to_dict()
            rows.append(data)
        return rows

    def to_unreconciled_records(self):
        rows = []
        for row in self.rows:
            data = {}
            for field_ in row.values():
                data |= field_.to_dict()
            rows.append(data)
        return rows

    def to_explanations(self, group_by):
        """Convert field notes into a row of data that holds data about the field."""
        rows = []
        for row in self.rows:
            data = {}
            for field_ in (f for f in row.values()):
                if field_.label == group_by:
                    data[group_by] = field_.value
                else:
                    keys = list(field_.to_dict())
                    value = json.dumps(
                        {
                            "note": field_.note,
                            "span": len(keys),
                            "result": field_.result.value,
                            "good": field_.result in GOOD,
                            "base_label": field_.base_label,
                        }
                    )
                    data[keys[0]] = value
            rows.append(data)
        return rows

    def get_all_keys(self):
        """Return a list of all keys in a possibly ragged group of rows."""
        keys = {}  # Dicts preserve order, sets do not
        for row in self.rows:
            keys |= {k: 1 for k in row.keys()}
        return keys

    def get_all_field_types(self):
        """Return a set of all field types used by the rows."""
        field_types = set()
        for row in self.rows:
            for cell in row.values():
                field_types.add(type(cell))
        return field_types

    def get_column_types(self) -> dict:
        column_types = {}
        for row in self.rows:
            for cell in row.values():
                field_type = type(cell)
                if field_type not in [NoOpField, SameField]:
                    column_types[cell.base_label] = field_type
        return column_types

    @classmethod
    def reconcile(cls, unreconciled: "Table", args):
        """Reconcile a data frame and return a new one."""
        rows = sorted(
            unreconciled.rows,
            key=lambda r: (r[args.group_by].value, r[args.row_key].value),
        )
        groups = groupby(rows, key=lambda r: r[args.group_by].value)
        reconciled = cls(is_reconciled=True)

        all_keys = unreconciled.get_all_keys()
        all_field_types = unreconciled.get_all_field_types()

        for subject_id, row_group in groups:
            row = Row()
            row_group = list(row_group)

            # This loop builds a reconciled row
            for key in all_keys:
                field_group = [g[key] for g in row_group if g[key]]
                field_type = type(field_group[0])
                cell = field_type.reconcile(field_group, len(row_group), args)
                cell.is_reconciled = True
                row.add_field(key, cell)

            # This loop tweaks a row for fields that depend on each other
            for field_type in all_field_types:
                field_type.reconcile_row(row, args)

            reconciled.append(row)

        return reconciled
