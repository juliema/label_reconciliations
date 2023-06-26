import re
import dataclasses
from argparse import Namespace
from collections import namedtuple
from itertools import groupby

import pandas as pd

from pylib.fields.base_field import Flag
from pylib.row import Row

FieldType = namedtuple("FieldType", "cls field_set")


@dataclasses.dataclass
class Table:
    rows: list[Row] = dataclasses.field(default_factory=list)
    types: dict[str, FieldType] = dataclasses.field(default_factory=dict)
    reconciled: bool = False

    def __len__(self) -> int:
        return len(self.rows)

    def append(self, row):
        self.rows.append(row)
        for field in row.fields:
            self.types[field.field_name] = FieldType(
                cls=type(field), field_set=field.field_set
            )

    def to_csv(self, args: Namespace, path, add_note=False) -> None:
        df = self.to_df(args, add_note)
        df.to_csv(path, index=False)

    def to_df(self, args: Namespace, add_note=False) -> pd.DataFrame:
        records = self.to_records(add_note=add_note)
        df = pd.DataFrame(records)
        headers = self.field_order(df, args)
        df = df[headers]
        return df

    def to_records(self, add_note=False) -> list[dict]:
        as_recs = [r.to_dict(add_note, self.reconciled) for r in self.rows]
        return as_recs

    @staticmethod
    def field_order(df, args):
        """A hack to workaround Zooniverse random-ish column ordering."""
        first = (args.group_by, args.row_key, args.user_column)

        temp = [(i, c) for i, c in enumerate(first) if c in df.columns]
        headers = [o[1] for o in temp]

        temp = [c for c in df.columns if re.match(r"^[Tt](\d+)", c)]
        headers += sorted(temp, key=lambda o: o.rsplit(":", 1)[0])

        headers += [c for c in df.columns if c and c not in headers]

        return headers

    def reconcile(self, args) -> "Table":
        unrec_rows = sorted(self.rows, key=lambda r: r[args.group_by].value)
        groups = groupby(unrec_rows, key=lambda r: r[args.group_by].value)
        table = Table(reconciled=True)

        for _, row_group in groups:
            new_row = Row()
            row_group = list(row_group)
            row_count = len(row_group)

            used_field_sets = set()

            for field_name, (cls, field_set) in self.types.items():
                if field_set and field_set not in used_field_sets:
                    group = []
                    for row in row_group:
                        fields = [f for f in row.fields if f.field_set == field_set]
                        group.append(fields)
                    used_field_sets.add(field_set)

                elif field_set in used_field_sets:
                    continue

                else:
                    group = [r[field_name] for r in row_group]

                if not group:
                    new_row.append(
                        cls(
                            note=f"All {row_count} records are blank",
                            flag=Flag.ALL_BLANK,
                        )
                    )
                    continue

                fields = cls.reconcile(group, row_count, args)
                new_row += fields if isinstance(fields, list) else [fields]

            table.rows.append(new_row)

        return table

    def to_flag_df(self, args):
        """Get reconciliation flags, notes, & spans for the summary report."""
        rows = []
        for row in self.rows:
            row_dict = {args.group_by: row[args.group_by].value}
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
