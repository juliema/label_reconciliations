import re
import dataclasses
from argparse import Namespace
from collections import namedtuple
from itertools import groupby
from pprint import pp

import pandas as pd

from pylib.fields.base_field import Flag
from pylib.row import Row
from pylib.utils import P

FieldType = namedtuple("FieldType", "cls field_set")


@dataclasses.dataclass
class Table:
    rows: list[Row] = dataclasses.field(default_factory=list)
    types: dict[str, FieldType] = dataclasses.field(default_factory=dict)
    reconciled: bool = False

    def __len__(self) -> int:
        return len(self.rows)

    def add(self, row):
        self.rows.append(row)
        for field in row.fields.values():
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

    def field_order(self, df, args):
        """A hack to workaround Zooniverse random-ish column ordering."""
        first = (args.group_by, args.row_key, args.user_column)

        temp = [(i, c) for i, c in enumerate(first) if c in df.columns]
        headers = [o[1] for o in temp]

        temp = [c for c in df.columns if re.match(r"^[Tt](\d+)", c)]
        headers += sorted(temp, key=self.sort_key)

        headers += [c for c in df.columns if c and c not in headers]

        return headers

    @staticmethod
    def sort_key(header: str) -> tuple[str, float]:
        field_name = header.rsplit(":", 1)[0]
        field_name, suffix = field_name.rsplit("_", 1)
        return field_name, float(suffix)

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
                    group = [r[field_name] for r in row_group if r[field_name]]

                if not group:
                    self.all_blank(new_row, cls, row_count)
                    continue

                fields = cls.reconcile(group, row_count, args)
                pp(fields)

                if fields is None:
                    self.all_blank(new_row, cls, row_count)
                    continue

                new_row.add(fields)

            table.add(new_row)

        return table

    @staticmethod
    def all_blank(new_row, cls, row_count):
        note = (
            f"{P('The', row_count)} {row_count} {P('record', row_count)} "
            f"{P('is', row_count)} blank"
        )
        new_row.add(
            cls(
                note=note,
                flag=Flag.ALL_BLANK,
            )
        )

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
