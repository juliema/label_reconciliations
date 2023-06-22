import re
import dataclasses
from argparse import Namespace
from collections import namedtuple
from itertools import groupby

import pandas as pd

from pylib.fields.base_field import Flag
from pylib.row import Row


@dataclasses.dataclass
class Table:
    rows: list[Row] = dataclasses.field(default_factory=list)
    reconciled: bool = False

    def __len__(self) -> int:
        return len(self.rows)

    def to_csv(self, args: Namespace, path, add_note=False) -> None:
        df = self.to_df(args, add_note)
        df.to_csv(path, index=False)

    def to_df(self, args: Namespace, add_note=False) -> pd.DataFrame:
        records = self.to_dict(add_note=add_note)
        df = pd.DataFrame(records)
        headers = self.field_order(df, args)
        df = df[headers]
        return df

    def to_dict(self, add_note=False) -> list[dict]:
        return [r.to_dict(add_note, self.reconciled) for r in self.rows]

    @staticmethod
    def field_order(df, args):
        """A hack to workaround Zooniverse random-ish column ordering."""
        Order = namedtuple("Order", "group major minor column")

        first = (args.group_by, args.row_key, args.user_column)
        order: list[Order] = [
            Order(group=0, major=0, minor=i, column=c)
            for i, c in enumerate(first) if c in df.columns
        ]

        first = [o.column for o in order]

        for i, column in enumerate(df.columns):
            if column in first:
                continue
            if match := re.match(r"^[Tt](\d+)", column):
                task_no = int(match.group(1))
                order.append(Order(group=1, major=task_no, minor=i, column=column))
            else:
                order.append(Order(group=2, major=0, minor=i, column=column))

        ordered = [o.column for o in sorted(order)]
        return ordered

    def reconcile(self, args) -> "Table":
        unrec_rows = sorted(self.rows, key=lambda r: r.group_by.value)
        groups = groupby(unrec_rows, key=lambda r: r.group_by.value)
        table = Table(reconciled=True)

        FieldType = namedtuple("FieldType", "cls field_set")
        field_types = {
            f.header: FieldType(cls=type(f), field_set=f.field_set)
            for r in self.rows for f in r.fields.values()
        }

        for _, row_group in groups:
            row = Row()
            row_group = list(row_group)
            row_count = len(row_group)

            used_field_sets = set()

            for header, (cls, field_set) in field_types.items():
                print(header)
                if field_set and field_set not in used_field_sets:
                    group = []
                    for row in row_group:
                        row_set = [
                            f for f in row.fields.values() if f.field_set == field_set
                        ]
                        group.append(row_set)
                    used_field_sets.add(field_set)
                elif field_set in used_field_sets:
                    continue
                else:
                    group = [r.all_fields[header] for r in row_group]

                if not group:
                    field = cls(
                        note=f"All {row_count} records are blank",
                        flag=Flag.ALL_BLANK,
                    )
                    row.add_field(header, field)
                    continue

                field = cls.reconcile(group, row_count, args)
                field = field if isinstance(field, list) else [field]
                for fld in field:
                    row.add_field(fld.name, fld)

            table.rows.append(row)
        return table

    def to_flag_df(self, args):
        """Get reconciliation flags, notes, & spans for the summary report."""
        rows = []
        for row in self.rows:
            row_dict = {args.group_by: row.group_by.value}
            for field in row.tasks:
                field_dict = field.to_dict(reconciled=True)
                for i, key in enumerate(field_dict.keys()):
                    row_dict[key] = {
                        "flag": field.flag.value,
                        "note": field.note,
                        "span": len(field_dict),
                        "offset": i,
                    }
            rows.append(row_dict)
        df = pd.DataFrame(rows)
        return df
