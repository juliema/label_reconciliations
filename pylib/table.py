"""A table of reconciled or unreconciled data."""
import re
import dataclasses
from argparse import Namespace
from itertools import groupby
from typing import Any

import pandas as pd

from pylib.flag import Flag
from pylib.row import Row


@dataclasses.dataclass
class Table:
    rows: list[Row] = dataclasses.field(default_factory=list)
    reconciled: bool = False

    def __len__(self) -> int:
        return len(self.rows)

    @property
    def headers(self) -> dict[str, Any]:
        field_types = {}
        for row in self.rows:
            for header, field in row.fields.items():
                if header not in field_types:
                    field_types[header] = type(field)
        return field_types

    def to_csv(self, args: Namespace, path, add_note=False) -> None:
        df = self.to_df(args, add_note)
        df.to_csv(path, index=False)

    def to_df(self, args: Namespace, add_note=False) -> pd.DataFrame:
        records = self.to_records(add_note)
        df = pd.DataFrame(records)
        headers = self.sort_headers(df, args)
        df = df[headers]
        return df

    def to_records(self, add_note=False) -> list[dict]:
        records = []
        for row in self.rows:
            rec = {}
            for field in row.fields.values():
                if self.reconciled:
                    rec |= field.to_reconciled_dict(add_note)
                else:
                    rec |= field.to_unreconciled_dict()
            records.append(rec)
        return records

    @staticmethod
    def sort_headers(df, args):
        """A hack to workaround Zooniverse random-ish column ordering."""
        order: [int, int, str] = [(0, 0, args.group_by)]

        if args.row_key in df.columns:
            order.append((0, 1, args.row_key))

        if args.user_column in df.columns:
            order.append((0, 2, args.user_column))

        first = [o[2] for o in order]

        for i, header in enumerate(df.columns):
            if header in first:
                continue
            if match := re.match(r"[Tt](\d+)", header):
                task_no = int(match.group(1))
                order.append((1, task_no, header))
            else:
                order.append((2, i, header))
        return [o[2] for o in sorted(order)]

    def reconcile(self, args) -> "Table":
        unrec_rows = sorted(self.rows, key=lambda r: r.fields[args.group_by].value)
        groups = groupby(unrec_rows, key=lambda r: r.fields[args.group_by].value)
        table = Table(reconciled=True)

        for _, row_group in groups:
            row = Row()
            row_group = list(row_group)
            row_count = len(row_group)

            for header, cls in self.headers.items():
                group = [r.fields[header] for r in row_group if header in r.fields]

                if not group:
                    field = cls(
                        note=f"All {row_count} records are blank", flag=Flag.ALL_BLANK
                    )
                    row.add_field(header, field)
                    continue

                field = cls.reconcile(group, row_count, args)
                field = field if isinstance(field, list) else [field]
                for fld in field:
                    name = f"{header} {fld.name}" if fld.name else header
                    row.add_field(name, fld)

            # This loop tweaks a row for fields that depend on each other
            for field in self.headers.values():
                field.adjust_reconciled(row, args)

            table.rows.append(row)

        return table

    def to_flag_df(self, args):
        """Get reconciliation flags, notes, & spans for the summary report."""
        rows = []
        for row in self.rows:
            exp_row = {args.group_by: row.fields[args.group_by].value}
            for header, field in row.fields.items():
                if field.reconcilable:
                    exp_dict = field.to_reconciled_dict()
                    for i, key in enumerate(exp_dict.keys()):
                        exp_row[key] = {
                            "flag": field.flag.value,
                            "note": field.note,
                            "span": len(exp_dict),
                            "offset": i,
                        }
            rows.append(exp_row)
        df = pd.DataFrame(rows)
        return df
