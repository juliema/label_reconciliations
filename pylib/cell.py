"""Functions for working with reconciled cells."""
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
