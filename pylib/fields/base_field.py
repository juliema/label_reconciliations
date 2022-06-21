from dataclasses import dataclass
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


BAD = {
    Flag.NO_FLAG.value,
    Flag.ERROR.value,
    Flag.ALL_BLANK.value,
    Flag.ONLY_ONE.value,
    Flag.NO_MATCH.value,
}
GOOD = {
    Flag.OK.value,
    Flag.WARNING.value,
    Flag.UNANIMOUS.value,
    Flag.MAJORITY.value,
    Flag.FUZZY.value,
}


@dataclass(kw_only=True)
class BaseField:
    label: str = ""
    note: str = ""
    flag: int = Flag.NO_FLAG.value
    is_reconciled: bool = False

    def header(self, attr):
        return f"{self.label}: {attr}"

    def round(self, *args, digits=0):
        return {self.header(a): round(self.__dict__[a], digits) for a in args}

    def to_dict(self):
        raise NotImplementedError()

    # @classmethod
    # def reconcile(cls, group, args=None):
    #     raise NotImplementedError()
