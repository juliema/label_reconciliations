import sys
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict, astuple
from typing import Any

from pylib.fields.base_field import BaseField
from pylib.flag import Flag
from pylib.utils import P

SKIPS = "start end label".split()


@dataclass(order=True)
class Highlight:
    start: int = -1
    end: int = -1
    text: str = ""
    label: str = ""

    @classmethod
    def fixup(cls, start: int, end: int, text: str, label: str):
        """Remove leading and trailing spaces before creating this object."""
        text_len = len(text)

        if (strip_len := len(text.rstrip())) != text_len:
            end -= text_len - strip_len
            text = text.rstrip()
            text_len = len(text)

        if (strip_len := len(text.lstrip())) != text_len:
            start += text_len - strip_len
            text = text.lstrip()

        return cls(text=text, start=start, end=end, label=label)


@dataclass(kw_only=True)
class HighlighterField(BaseField):
    highlights: list[Highlight] = field(default_factory=list)

    def to_unreconciled_dict(self) -> dict[str, Any]:
        values = []
        for val in self.highlights:
            values.append(asdict(val))
        return {self.header("highlights"): values}

    def to_reconciled_dict(self, add_note=False) -> dict[str, Any]:
        raw = asdict(self.highlights[0]) if self.highlights else {}
        out = {f"{self.name}: {k}": v for k, v in raw.items() if k not in SKIPS}
        return self.add_note(out, add_note)

    def rename(self, old):
        return "_".join([old, self.highlights[0].label]) if self.highlights else old

    @classmethod
    def reconcile(cls, group, row_count, _=None):
        fields: list[HighlighterField] = []

        by_label = HighlighterField.get_by_labels(group)

        for label, highlights in by_label.items():
            count = len(highlights)

            match Counter([astuple(h) for h in highlights]).most_common():

                # Only one selected
                case [c0] if c0[1] == 1:
                    start, end, text, label = c0[0]
                    note = f"Only 1 highlight in {count} {P('record', count)}"
                    lit = Highlight(start=start, end=end, text=text, label=label)
                    fields.append(
                        cls(name=label, note=note, highlights=[lit], flag=Flag.ONLY_ONE)
                    )

                # Everyone chose the same value
                case [c0] if c0[1] == count and c0[1] > 1:
                    start, end, text, label = c0[0]
                    note = (
                        f"Exact unanimous match, {c0[1]} of {count} "
                        f"{P('record', count)}"
                    )
                    lit = Highlight(start=start, end=end, text=text, label=label)
                    fields.append(
                        cls(name=label, note=note, highlights=[lit], flag=Flag.UNANIMOUS)
                    )

                # It was a tie for the text chosen
                case [c0, c1, *_] if c0[1] > 1 and c0[1] == c1[1]:
                    start, end, text, label = c0[0]
                    note = (
                        f"Exact match is a tie, {c0[1]} of {count} {P('record', count)}"
                    )
                    lit = Highlight(start=start, end=end, text=text, label=label)
                    fields.append(
                        cls(name=label, note=note, highlights=[lit], flag=Flag.MAJORITY)
                    )

                # We have a winner
                case [c0, *_] if c0[1] > 1:
                    start, end, text, label = c0[0]
                    note = f"Exact match, {c0[1]} of {count} {P('record', count)}"
                    lit = Highlight(start=start, end=end, text=text, label=label)
                    fields.append(
                        cls(name=label, note=note, highlights=[lit], flag=Flag.MAJORITY)
                    )

                # They're all different
                case [c0, *_] if c0[1] == 1:
                    start, end, text, label = c0[0]
                    note = f"No text match on {count} {P('record', count)}"
                    lit = Highlight(start=start, end=end, text=text, label=label)
                    fields.append(
                        cls(name=label, note=note, highlights=[lit], flag=Flag.NO_MATCH)
                    )

                case _:
                    sys.exit(f"Unknown count pattern {highlights}")

        return fields

    @staticmethod
    def get_by_labels(use):
        by_label = defaultdict(list)

        for highlights in use:
            for lit in highlights.highlights:
                by_label[lit.label].append(lit)

        by_label = {k: sorted(v) for k, v in by_label.items()}

        return by_label
