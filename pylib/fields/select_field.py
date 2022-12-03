"""Reconcile select lists.

Classifications are chosen from a controlled vocabulary.
"""
from collections import Counter
from dataclasses import dataclass

from pylib.fields.base_field import BaseField
from pylib.result import Result
from pylib.result import sort_results
from pylib.utils import P

PLACEHOLDERS = ["placeholder"]


@dataclass(kw_only=True)
class SelectField(BaseField):
    value: str = ""

    def to_dict(self):
        return {self.label: self.value}

    @classmethod
    def reconcile(cls, group, _=None):
        values = [
            f.value 
            if f.value and f.value.lower() not in PLACEHOLDERS else ""
            for f in group
        ]

        filled = Counter([v for v in values if v.strip()]).most_common()

        count = len(values)
        blanks = count - sum(f[1] for f in filled)

        match filled:
            # Nobody chose a value
            case []:
                note = (
                    f"{P('The', count)} {count} {P('record', count)} "
                    f"{P('is', count)} blank"
                )
                return cls(note=note, result=Result.ALL_BLANK)

            # Everyone chose the same value
            case [f0] if f0[1] > 1 and f0[1] == count:
                note = f"Unanimous match, {f0[1]} of {count} {P('record', count)}"
                return cls(note=note, value=f0[0], result=Result.UNANIMOUS)

            # It was a tie for the values chosen
            case [f0, f1, *_] if f0[1] > 1 and f0[1] == f1[1]:
                note = (
                    f"Match is a tie, {f0[1]} of {count} {P('record', count)} with "
                    f"{blanks} {P('blank', blanks)}"
                )
                return cls(note=note, value=f0[0], result=Result.MAJORITY)

            # We have a winner
            case [f0, *_] if f0[1] > 1:
                note = (
                    f"Match {f0[1]} of {count} {P('record', count)} with {blanks} "
                    f"{P('blank', blanks)}"
                )
                return cls(note=note, value=f0[0], result=Result.MAJORITY)

            # Only one person chose a value
            case [f0] if f0[1] == 1:
                note = f"Only 1 transcript in {count} {P('record', count)}"
                return cls(note=note, value=f0[0], result=Result.ONLY_ONE)

            # Everyone picked a different value
            case _:
                note = (
                    f"No select match on {count} {P('record', count)} with {blanks} "
                    f"{P('blank', blanks)}"
                )
                return cls(note=note, result=Result.NO_MATCH)

    @classmethod
    def pad_group(cls, group, length):
        while len(group) < length:
            group.append(cls())
        return group

    @staticmethod
    def results():
        return sort_results(
            Result.ALL_BLANK,
            Result.UNANIMOUS,
            Result.MAJORITY,
            Result.ONLY_ONE,
            Result.NO_MATCH,
        )
