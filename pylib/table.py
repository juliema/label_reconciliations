"""A table of reconciled or unreconciled data."""
import json
import re
from dataclasses import dataclass
from dataclasses import field
from itertools import groupby

import pandas as pd

from pylib.fields.base_field import BaseField
from pylib.fields.noop_field import NoOpField
from pylib.fields.same_field import SameField
from pylib.result import GOOD, Result
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
    def get_note(obj):
        try:
            notes = json.loads(obj)["note"]
        except TypeError:
            notes = ""
        return notes

    @staticmethod
    def get_result(obj):
        try:
            return json.loads(obj)["result"]
        except TypeError:
            return Result.ALL_BLANK.value

    def to_df(self, args):
        df = pd.DataFrame(self.to_records())
        df = df.set_index(args.group_by, drop=False)
        df = self.sort_columns(args, df)
        df = df.fillna("")
        return df

    def explanation_df(self, args, unreconciled=None):
        df = pd.DataFrame(self.to_explanations(args.group_by))
        df = df.set_index(args.group_by, drop=False)
        columns = [c for c in df.columns if c != args.group_by]
        df[columns] = df[columns].applymap(self.get_note)
        self.fix_empty_explanations(args, df, unreconciled)
        df = self.sort_columns(args, df)
        return df

    def problem_df(self, args):
        df = pd.DataFrame(self.to_explanations(args.group_by))
        df = df.set_index(args.group_by, drop=False)
        columns = [c for c in df.columns if c != args.group_by]
        df[columns] = df[columns].applymap(self.get_result)
        df = self.sort_columns(args, df)
        return df

    def to_csv(self, args, path, unreconciled=None):
        df = self.to_df(args)

        if args.explanations and self.is_reconciled:
            df2 = self.explanation_df(args, unreconciled)
            df = df.join(df2, rsuffix=" Explanation")
            df = self.sort_columns(args, df)
            df = df.fillna("")

        df.to_csv(path, index=False)

    def fix_empty_explanations(self, args, df, unreconciled):
        """A hack to workaround Zooniverse missing data."""
        df3 = pd.DataFrame(
            [
                {args.group_by: r[args.group_by], 'n': 1}
                for r in unreconciled.to_records()
            ]
        )
        counts = df3.groupby(args.group_by).count()
        e = list(self.get_column_types().keys())
        for n in counts.n.unique():
            idx = counts.loc[counts.n == n].index
            replace = f"All {n} records are blank"
            df.update(df.loc[idx, e].replace(r"^\s*$", replace, regex=True))

    @staticmethod
    def sort_columns(args, df):
        """A hack to workaround Zooniverse random-ish column ordering."""
        order = [(0, 0, args.group_by)]
        skips = [args.group_by]
        if hasattr(args, "row_key") and args.row_key and args.row_key in df.columns:
            order.append((0, 1, args.row_key))
            skips.append(args.row_key)
        if (hasattr(args, "user_column") and args.user_column
                and args.user_column in df.columns):
            order.append((0, 2, args.user_column))
            skips.append(args.user_column)

        for i, col in enumerate(df.columns):
            if col in skips:
                continue
            if match := re.match(r"[Tt](\d+)", col):
                task_no = int(match.group(1))
                order.append((1, task_no, col))
            else:
                order.append((2, i, col))
        order = [o[2] for o in sorted(order)]
        df = df[order]
        return df

    @staticmethod
    def natural_column_sort(df, order=None):
        """A hack to workaround Zooniverse random-ish column ordering."""
        order = order if order else []
        for i, col in enumerate(df.columns):
            if match := re.match(r"[Tt](\d+)", col):
                task_no = int(match.group(1))
                order.append((1, task_no, col))
            else:
                order.append((2, i, col))
        order = [o[2] for o in sorted(order)]
        df = df[order]
        return df

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
                            "result": field_.result.value,
                            "good": field_.result in GOOD,
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
                    column_types[cell.label] = field_type
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
                field_group = field_type.pad_group(field_group, len(row_group))
                cell = field_type.reconcile(field_group, args)
                cell.is_reconciled = True
                row.add_field(key, cell)

            # This loop tweaks a row for fields that depend on each other
            for field_type in all_field_types:
                field_type.reconcile_row(row, args)

            reconciled.append(row)

        return reconciled
