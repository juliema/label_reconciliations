from enum import IntEnum


class Result(IntEnum):
    NO_FLAG = 0
    OK = 1
    UNANIMOUS = 2
    MAJORITY = 3
    FUZZY = 4
    ALL_BLANK = 5
    ONLY_ONE = 6
    NO_MATCH = 7
    ERROR = 8


BAD = {Result.ERROR, Result.ALL_BLANK, Result.ONLY_ONE, Result.NO_MATCH}
GOOD = {Result.NO_FLAG, Result.OK, Result.UNANIMOUS, Result.MAJORITY, Result.FUZZY}


def sort_results(*args):
    return sorted(args, key=lambda f: f.value)


def result_dict():
    return {r.value: str(r).split(".", 1)[1] for r in Result if r > Result.NO_FLAG}
