from collections import Counter
from dataclasses import dataclass
from typing import Any

from pylib.flag import Flag
from pylib.utils import P

EXPLAIN_SUFFIX = ": Explanation"
PLACEHOLDERS = ["placeholder"]


@dataclass(kw_only=True)
class BaseField:
    name: str = ""
    note: str = ""
    flag: Flag = Flag.NO_FLAG
    is_padding: bool = False

    def header(self, attr: str) -> str:
        return f"{self.name}: {attr}"

    def to_unreconciled_dict(self) -> dict[str, Any]:
        raise NotImplementedError()

    def to_reconciled_dict(self, add_note=False) -> dict[str, Any]:
        raise NotImplementedError()

    def add_note(self, as_dict: dict[str, Any], add_note: bool) -> dict[str, Any]:
        if add_note:
            as_dict[f"{self.name}{EXPLAIN_SUFFIX}"] = self.note
        return as_dict

    @classmethod
    def reconcile(cls, group, args=None):
        raise NotImplementedError()

    @classmethod
    def pad_group(cls, group, length):
        while len(group) < length:
            group.append(cls(is_padding=True))
        return group

    @staticmethod
    def reconcile_row(reconciled_row, args=None):
        return


def controlled_vocab(cls, group):
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
            return cls(note=note, flag=Flag.ALL_BLANK)

        # Everyone chose the same value
        case [f0] if f0[1] > 1 and f0[1] == count:
            note = f"Unanimous match, {f0[1]} of {count} {P('record', count)}"
            return cls(note=note, value=f0[0], flag=Flag.UNANIMOUS)

        # It was a tie for the values chosen
        case [f0, f1, *_] if f0[1] > 1 and f0[1] == f1[1]:
            note = (
                f"Match is a tie, {f0[1]} of {count} {P('record', count)} with "
                f"{blanks} {P('blank', blanks)}"
            )
            return cls(note=note, value=f0[0], flag=Flag.MAJORITY)

        # We have a winner
        case [f0, *_] if f0[1] > 1:
            note = (
                f"Match {f0[1]} of {count} {P('record', count)} with {blanks} "
                f"{P('blank', blanks)}"
            )
            return cls(note=note, value=f0[0], flag=Flag.MAJORITY)

        # Only one person chose a value
        case [f0] if f0[1] == 1:
            note = f"Only 1 transcript in {count} {P('record', count)}"
            return cls(note=note, value=f0[0], flag=Flag.ONLY_ONE)

        # Everyone picked a different value
        case _:
            note = (
                f"No match on {count} {P('record', count)} with {blanks} "
                f"{P('blank', blanks)}"
            )
            return cls(note=note, flag=Flag.NO_MATCH)
