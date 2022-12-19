from collections import Counter
from dataclasses import dataclass
from typing import Any

from pylib.fields.base_field import BaseField
from pylib.flag import Flag
from pylib.utils import P

PLACEHOLDERS = ["placeholder"]


@dataclass(kw_only=True)
class SelectField(BaseField):
    value: str = ""

    def to_unreconciled_dict(self) -> dict[str, Any]:
        return {self.name: self.value}

    def to_reconciled_dict(self, add_note=False) -> dict[str, Any]:
        as_dict = self.to_unreconciled_dict()
        return self.add_note(as_dict, add_note)

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
                    f"No select match on {count} {P('record', count)} with {blanks} "
                    f"{P('blank', blanks)}"
                )
                return cls(note=note, flag=Flag.NO_MATCH)
