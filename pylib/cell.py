"""Functions for working with reconciled data."""
from enum import Enum


class Flag(Enum):
    OK = 0
    EMPTY = 1
    ERROR = 2
    WARNING = 3


def cell(*, note="", flag=Flag.OK, **kwargs):
    obj = {"note": note, "flag": flag}
    obj |= kwargs
    return obj


def ok(*, note, **kwargs):
    return cell(note=note, flag=Flag.OK, **kwargs)


def empty(*, note, **kwargs):
    return cell(note=note, flag=Flag.EMPTY, **kwargs)


def error(*, note, **kwargs):
    return cell(note=note, flag=Flag.ERROR, **kwargs)


def warning(*, note, **kwargs):
    return cell(note=note, flag=Flag.WARNING, **kwargs)


def rename(*, prefix, fields):
    return {f"{prefix}: {k}": v for k, v in fields.items()}


def get_prefix(field):
    return field.split(":")[0]


def format_data_frame(columns, df, column_types):
    """Sort and rename column headers."""
    other, same = [], []

    for col in df.columns:
        key = get_prefix(col)

        if key in column_types and column_types[key] != "same":
            other.append(col)

        elif key in column_types:
            same.append(col)

    columns += other
    columns += same

    columns += [c for c in df.columns if c not in columns]

    df = df[columns]
    return df
