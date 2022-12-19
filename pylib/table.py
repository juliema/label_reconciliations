"""A table of reconciled or unreconciled data."""
import re
import dataclasses
from argparse import Namespace
from itertools import groupby

import pandas as pd

from pylib import utils
from pylib.flag import Flag
from pylib.row import Row
from pylib.fields.field_types import FIELD_TYPES


@dataclasses.dataclass
class Table:
    headers: dict[str, FIELD_TYPES] = dataclasses.field(default_factory=dict)
    rows: list[Row] = dataclasses.field(default_factory=list)
    reconciled: bool = False

    def __len__(self) -> int:
        return len(self.rows)

    def append_row(self, row: Row) -> None:
        for name, field in row.fields.items():
            if name not in self.headers:
                self.headers[name] = field
            else:
                old_type = type(self.headers[name])
                if not isinstance(field, old_type):
                    utils.error_exit(
                        f"Field type {name} changed from {old_type} to {type(field)}"
                    )
        self.rows.append(row)

    def to_csv(self, args: Namespace, path, add_note=False) -> None:
        df = self.to_df(args, add_note)
        df.to_csv(path, index=False)

    def to_df(self, args: Namespace, add_note=False) -> pd.DataFrame:
        records = self.to_records(add_note)
        self.headers = self.sort_headers(args)
        df = pd.DataFrame(records)
        headers = []
        for h in self.headers:
            headers += [c for c in df.columns if c.startswith(h)]
        df = df[headers]
        return df

    def to_records(self, add_note=False) -> list[dict]:
        records = []
        for row in self.rows:
            rec = {}
            for header, field in row.fields.items():
                if self.reconciled:
                    rec |= row[header].to_reconciled_dict(add_note)
                else:
                    rec |= row[header].to_unreconciled_dict()
            records.append(rec)
        return records

    def reconcile(self, args) -> "Table":
        rows = sorted(self.rows, key=lambda r: r[args.group_by].value)
        groups = groupby(rows, key=lambda r: r[args.group_by].value)
        reconciled = Table(reconciled=True)

        for _, row_group in groups:
            row = Row()
            row_group = list(row_group)

            for header, field in self.headers.items():  # In sorted order
                cls = type(field)

                field_group = [g[header] for g in row_group if header in g]
                field_group = cls.pad_group(field_group, len(row_group))

                if all(f.is_padding for f in field_group):
                    n = len(row_group)
                    field = cls(note=f"All {n} records are blank", flag=Flag.ALL_BLANK)
                else:
                    field = cls.reconcile(field_group, args)

                row.add_field(header, field)

            # This loop tweaks a row for fields that depend on each other
            for field in self.headers.values():
                field.reconcile_row(row, args)

            reconciled.append_row(row)

        return reconciled

    def sort_headers(self, args):
        """A hack to workaround Zooniverse random-ish column ordering."""
        first = [args.group_by, args.row_key, args.user_column]

        order: [int, int, str] = [(0, 0, args.group_by)]

        if args.row_key in self.headers:
            order.append((0, 1, args.row_key))

        if args.user_column in self.headers:
            order.append((0, 2, args.user_column))

        for i, header in enumerate(self.headers.keys()):
            if header in first:
                continue
            if match := re.match(r"[Tt](\d+)", header):
                task_no = int(match.group(1))
                order.append((1, task_no, header))
            else:
                order.append((2, i, header))
        order = [o[2] for o in sorted(order)]
        return {o: self.headers[o] for o in order}
