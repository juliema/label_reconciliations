"""Reconcile a group where all values are supposed to be the same."""
from dataclasses import dataclass

from pylib.fields.base_field import BaseField
from pylib.result import Result
from pylib.result import sort_results


@dataclass(kw_only=True)
class SameField(BaseField):
    value: str = ""

    def to_dict(self):
        return {self.label: self.value}

    @classmethod
    def reconcile(cls, group, _=None):
        if all(g.value == group[0].value for g in group):
            value = group[0].value
            result = Result.OK
            note = ""
        else:
            value = ",".join(g.value for g in group)
            result = Result.ERROR
            note = f"Not all values are the same {value}"

        return cls(value=value, result=result, note=note, is_reconciled=True)

    @classmethod
    def pad_group(cls, group, length):
        while len(group) < length:
            group.append(cls())
        return group

    @staticmethod
    def results():
        return sort_results(Result.OK, Result.ERROR)
