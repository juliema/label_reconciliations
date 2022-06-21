from enum import Enum


class Flag(Enum):
    NO_FLAG = 0
    OK = 1
    ERROR = 2
    WARNING = 3
    ALL_BLANK = 4
    UNANIMOUS = 5
    MAJORITY = 6
    ONLY_ONE = 7
    NO_MATCH = 8
    FUZZY = 9


BAD = {Flag.ERROR, Flag.ALL_BLANK, Flag.ONLY_ONE, Flag.NO_MATCH}
GOOD = {Flag.OK, Flag.WARNING, Flag.UNANIMOUS, Flag.MAJORITY, Flag.FUZZY}


def cell(*, note="", flag=Flag.NO_FLAG.value, **kwargs):
    obj = kwargs
    if note:
        obj["note"] = note
    if flag:
        obj["flag"] = flag
    return obj


def no_flag(*, note="", **kwargs):
    return cell(note=note, flag=Flag.NO_FLAG.value, **kwargs)


def ok(*, note="", **kwargs):
    return cell(note=note, flag=Flag.OK.value, **kwargs)


def error(*, note="", **kwargs):
    return cell(note=note, flag=Flag.ERROR.value, **kwargs)


def warning(*, note="", **kwargs):
    return cell(note=note, flag=Flag.WARNING.value, **kwargs)


def all_blank(*, note="", **kwargs):
    return cell(note=note, flag=Flag.ALL_BLANK.value, **kwargs)


def unanimous(*, note="", **kwargs):
    return cell(note=note, flag=Flag.UNANIMOUS.value, **kwargs)


def majority(*, note="", **kwargs):
    return cell(note=note, flag=Flag.MAJORITY.value, **kwargs)


def only_one(*, note="", **kwargs):
    return cell(note=note, flag=Flag.ONLY_ONE.value, **kwargs)


def no_match(*, note="", **kwargs):
    return cell(note=note, flag=Flag.NO_MATCH.value, **kwargs)


def fuzzy(*, note="", **kwargs):
    return cell(note=note, flag=Flag.FUZZY.value, **kwargs)


def rename(*, prefix, fields):
    new = {}
    for key, value in fields.items():
        key = f"{prefix}: {key}" if key != "no_label" else prefix
        new[key] = value
    return new


def get_prefix(field):
    return field.split(":")[0]
