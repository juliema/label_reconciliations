import re
import sys
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict, astuple
from itertools import groupby
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

        aligned = HighlighterField.align_json_fields(group)

        for suffix, highlights in aligned:
            count = len(highlights)

            match Counter([astuple(h) for h in highlights]).most_common():

                # Only one selected
                case [c0] if c0[1] == 1:
                    start, end, text, label = c0[0]
                    label = f"{label}_{suffix}"
                    note = f"Only 1 highlight in {count} {P('record', count)}"
                    lit = Highlight(start=start, end=end, text=text, label=label)
                    fields.append(
                        cls(name=label, note=note, highlights=[lit], flag=Flag.ONLY_ONE)
                    )

                # Everyone chose the same value
                case [c0] if c0[1] == count and c0[1] > 1:
                    start, end, text, label = c0[0]
                    label = f"{label}_{suffix}"
                    note = (
                        f"Exact unanimous match, {c0[1]} of {count} "
                        f"{P('record', count)}"
                    )
                    lit = Highlight(start=start, end=end, text=text, label=label)
                    fields.append(
                        cls(
                            name=label,
                            note=note,
                            highlights=[lit],
                            flag=Flag.UNANIMOUS,
                        )
                    )

                # It was a tie for the text chosen
                case [c0, c1, *_] if c0[1] > 1 and c0[1] == c1[1]:
                    start, end, text, label = c0[0]
                    label = f"{label}_{suffix}"
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
                    label = f"{label}_{suffix}"
                    note = f"Exact match, {c0[1]} of {count} {P('record', count)}"
                    lit = Highlight(start=start, end=end, text=text, label=label)
                    fields.append(
                        cls(name=label, note=note, highlights=[lit], flag=Flag.MAJORITY)
                    )

                # They're all different
                case [c0, *_] if c0[1] == 1:
                    start, end, text, label = c0[0]
                    label = f"{label}_{suffix}"
                    note = f"No text match on {count} {P('record', count)}"
                    lit = Highlight(start=start, end=end, text=text, label=label)
                    fields.append(
                        cls(name=label, note=note, highlights=[lit], flag=Flag.NO_MATCH)
                    )

                case _:
                    sys.exit(f"Unknown pattern {highlights}")

        return fields

    @staticmethod
    def align_json_fields(group):
        tie = defaultdict(int)

        by_label = [(i, rec) for i, fld in enumerate(group) for rec in fld.highlights]
        by_label = sorted(by_label, key=lambda h: (h[1].label, h[0], h[1].start))
        by_label = groupby(by_label, key=lambda h: h[1].label)

        aligned = []

        for label, label_hi in by_label:
            label_hi = list(label_hi)

            start = min(h[1].start for h in label_hi)
            end = max(h[1].end for h in label_hi)

            # Find where the highlights overlap
            hits = bytearray(end - start)
            for hi in label_hi:
                for i in range(hi[1].start, hi[1].end):
                    hits[i - start] = 1

            # Get all contiguous matches
            frags = [
                (m.start() + start, m.end() + start)
                for m in re.finditer(b"(\x01+)", hits)
            ]

            # Match highlights to the fragments
            highlights = defaultdict(list)
            for hi in label_hi:
                for frag in frags:
                    if frag[0] <= hi[1].start < frag[1]:
                        key = label, frag[0], frag[1]
                        highlights[key].append(hi)
                        break

            # Merge disjointed highlights
            for key, highs in highlights.items():
                joined = []
                by_user = groupby(highs, key=lambda h: h[0])
                for user, parts in by_user:
                    parts = [p[1] for p in parts]
                    if len(parts) == 1:
                        joined.append(parts[0])
                    else:
                        joined.append(Highlight(
                            start=min(p.start for p in parts),
                            end=max(p.end for p in parts),
                            text=" ".join(p.text for p in parts),
                            label=label,
                        ))

                tie[label] += 1
                aligned.append((f"{label}_{tie[label]}", joined))

        return aligned
