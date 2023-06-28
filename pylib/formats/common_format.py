import json
import warnings

from pylib import utils
from pylib.fields.box_field import BoxField
from pylib.fields.length_field import LengthField
from pylib.fields.noop_field import NoOpField
from pylib.fields.point_field import PointField
from pylib.fields.same_field import SameField
from pylib.fields.select_field import SelectField
from pylib.fields.text_field import TextField
from pylib.row import Row
from pylib.table import Table


def validate_columns(args, df):
    column_types = {}
    if not args.column_types:
        warnings.warn("\nMissing column types for a CSV or JSON file.")

    types = ",".join(args.column_types)

    errors = []

    if args.group_by not in df.columns:
        f"Column '{args.group_by}' not in the input columns"

    for arg in types.split(","):
        try:
            col_name, col_type = arg.split(":")

            if col_name not in df.columns:
                raise ValueError(f"Column '{col_name}' not in the input columns")

            if col_type not in """ select text same box point noop length """.split():
                raise ValueError(f"'{col_type}' is not a valid column type")

            column_types[col_name] = col_type

        except Exception as e:
            errors.append(e)

    if errors:
        utils.error_exit(errors)

    return column_types


def read_table(args, df):
    df = df.fillna("")

    column_types = validate_columns(args, df)

    df = df.sort_values([args.group_by])

    records = df.to_dict("records")

    table = Table()

    for raw_row in records:
        row = Row()

        row.add(
            SameField(
                name=args.group_by,
                value=raw_row[args.group_by],
            )
        )

        for name, value in raw_row.items():
            if name == args.group_by:
                continue

            field_type = column_types.get(name, "noop")

            match field_type:
                case "box":
                    if value:
                        value = json.loads(value)
                    else:
                        value = {"x": 0, "y": 0, "width": 0, "height": 0}
                    row.add(
                        BoxField(
                            name=name,
                            left=round(value["x"]),
                            right=round(value["x"] + value["width"]),
                            top=round(value["y"]),
                            bottom=round(value["y"] + value["height"]),
                        )
                    )
                case "length":
                    if value:
                        value = json.loads(value)
                    else:
                        value = {"x1": 0, "y1": 0, "x2": 0, "y2": 0}
                    row.add(
                        LengthField(
                            name=name,
                            x1=round(value["x1"]),
                            y1=round(value["y1"]),
                            x2=round(value["x2"]),
                            y2=round(value["y2"]),
                        )
                    )
                case "noop":
                    value = value if value else ""
                    row.add(NoOpField(name=name, value=value))
                case "point":
                    value = json.loads(value) if value else {"x": 0, "y": 0}
                    row.add(
                        PointField(
                            name=name,
                            x=round(value["x"]),
                            y=round(value["y"]),
                        )
                    )
                case "same":
                    value = value if value else ""
                    row.add(SameField(name=name, value=value))
                case "select":
                    value = value if value else ""
                    row.add(SelectField(name=name, value=value))
                case "text":
                    value = value if value else ""
                    row.add(TextField(name=name, value=value))

        table.add(row)

    return table
