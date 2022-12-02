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

    @staticmethod
    def get_notes(obj):
        try:
            notes = json.loads(obj)["note"]
        except TypeError:
            notes = ""
        return notes

    def to_csv(self, args, path):
        keys = [args.group_by, "__order__"]

        df1 = pd.DataFrame(self.to_records())
        df1["__order__"] = 1

        dfs = [df1]
        if args.explanations and self.is_reconciled:
            df2 = pd.DataFrame(self.to_explanations(args.group_by))
            columns = [c for c in df2.columns if c != args.group_by]
            df2[columns] = df2[columns].applymap(self.get_notes)
            df2["__order__"] = 2
            df2 = df2[df1.columns]
            dfs.append(df2)

        df = pd.concat(dfs).fillna("")
        df = df.sort_values(keys)
        df = df.drop(["__order__"], axis="columns")
        df.to_csv(path, index=False)

    def to_records(self):
        exclude = NoOpField if self.is_reconciled else type(None)
        rows = []
        for row in self.rows:
            data = {}
            for field_ in (f for f in row.values() if not isinstance(f, exclude)):
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
        return list(keys)

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

        for _, row_group in groups:
            row = Row()
            row_group = list(row_group)

            # This loop builds a reconciled row
            for key in all_keys:
                field_group = [g[key] for g in row_group if g.get(key)]
                if not field_group:
                    continue
                field_type = type(field_group[0])
                cell = field_type.reconcile(field_group, args)
                cell.is_reconciled = True
                row.add_field(key, cell)

            # This loop tweaks a row for fields that depend on each other
            for field_type in all_field_types:
                field_type.reconcile_row(row, args)

            reconciled.append(row)

        return reconciled
