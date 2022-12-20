from enum import IntEnum


class Flag(IntEnum):
    NO_FLAG = 0
    OK = 1
    UNANIMOUS = 2
    MAJORITY = 3
    FUZZY = 4
    ALL_BLANK = 5
    ONLY_ONE = 6
    NO_MATCH = 7
    ERROR = 8

    @staticmethod
    def sorter(*args):
        return sorted(args, key=lambda f: f.value)


def flag_labels():
    return {
        Flag.OK.value: "OK",
        Flag.UNANIMOUS.value: "Unanimous Matches",
        Flag.MAJORITY.value: "Majority Matches",
        Flag.FUZZY.value: "Fuzzy Matches",
        Flag.ALL_BLANK.value: "All Blank",
        Flag.ONLY_ONE.value: "One Transcript",
        Flag.NO_MATCH.value: "No Matches",
        Flag.ERROR.value: "Errors",
    }


FLAG_END = Flag.ERROR + 1
PROBLEM = {Flag.ERROR, Flag.ONLY_ONE, Flag.NO_MATCH}
