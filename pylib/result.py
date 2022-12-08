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


RESULT_END = Result.ERROR + 1
PROBLEM = {Result.ERROR, Result.ALL_BLANK, Result.ONLY_ONE, Result.NO_MATCH}
BAD = {Result.ERROR, Result.ALL_BLANK, Result.ONLY_ONE, Result.NO_MATCH}
GOOD = {Result.NO_FLAG, Result.OK, Result.UNANIMOUS, Result.MAJORITY, Result.FUZZY}


def sort_results(*args):
    return sorted(args, key=lambda f: f.value)


def result_labels():
    return {
        Result.OK.value: "OK",
        Result.UNANIMOUS.value: "Unanimous Matches",
        Result.MAJORITY.value: "Majority Matches",
        Result.FUZZY.value: "Fuzzy Matches",
        Result.ALL_BLANK.value: "All Blank",
        Result.ONLY_ONE.value: "One Transcript",
        Result.NO_MATCH.value: "No Matches",
        Result.ERROR.value: "Errors",
    }
