from dataclasses import dataclass

from pylib.result import Result


@dataclass(kw_only=True)
class BaseField:
    key: str = ""
    note: str = ""
    result: Result = Result.NO_FLAG
    is_reconciled: bool = False

    @property
    def label(self):
        splits = self.key.split(maxsplit=1)
        return splits[-1] if splits and self.key and self.key[0] == "~" else self.key

    def header(self, attr):
        return f"{self.label}: {attr}"

    def round(self, *args, digits=0):
        return {self.header(a): round(self.__dict__[a], digits) for a in args}

    def to_dict(self):
        raise NotImplementedError()

    @classmethod
    def reconcile(cls, group, args=None):
        raise NotImplementedError()

    @classmethod
    def pad_group(cls, group, length):
        raise NotImplementedError()

    @staticmethod
    def results():
        raise NotImplementedError()

    @staticmethod
    def reconcile_row(reconciled_row, args=None):
        return
