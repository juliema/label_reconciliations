import re
import sys
from collections import defaultdict, Counter
from dataclasses import dataclass, astuple
from itertools import groupby
from typing import Any

from pylib.fields.base_field import BaseField
from pylib.flag import Flag
from pylib.utils import P


@dataclass(kw_only=True)
class HighlightField(BaseField):
    """I'm converting to & from a tuple (astuple) so field order is important."""
    start: int = -1
    end: int = -1
    text: str = ""
    label: str = ""

    @classmethod
    def unreconciled_list(
        cls, values: list[dict], args, text: str = ""
    ) -> list["HighlightField"]:
        """Create an unreconciled list from the values list."""
        highlights = []
        for value in values:
            label = value["labelInformation"]["label"]
            highlights.append(
                HighlightField(
                    text=value["text"],
                    label=label,
                    start=value["start"],
                    end=value["end"] + 1,
                )
            )

        highlights = HighlightField._join(highlights, args.join_distance, text)
        HighlightField._strip(highlights)
        return highlights

    def to_unreconciled_dict(self) -> dict[str, Any]:
        return {
            self.header("text"): self.text,
            self.header("start"): self.start,
            self.header("end"): self.end,
        }

    def to_reconciled_dict(self, add_note=False) -> dict[str, Any]:
        as_dict = self.to_unreconciled_dict()
        return self.add_note(as_dict, add_note)

    @staticmethod
    def _join(
        highlights: list["HighlightField"], dist: int, text: str = ""
    ) -> list["HighlightField"]:
        """Join highlights that are within the given distance from each other."""
        highlights = sorted(highlights, key=lambda h: (h.label, h.start))

        if not highlights:
            return []

        prev = highlights[0]
        new_highlights = []

        for curr in highlights[1:]:
            if prev.label == curr.label and (curr.start - prev.end) <= dist:
                prev.end = curr.end
                # TODO: Use the next line when Zooniverse adds text
                # prev.text = text[prev.start:curr.end]
                prev.text += " " + curr.text  # TODO DELETE ME when text is available
            else:
                new_highlights.append(prev)
                prev = curr

        new_highlights.append(prev)

        return new_highlights

    @staticmethod
    def _strip(highlights: list["HighlightField"]) -> None:
        """Strip leading and trailing spaces from the text."""
        for hi in highlights:
            text_len = hi.end - hi.start

            stripped = hi.text.rstrip()
            if (strip_len := len(stripped)) != text_len:
                hi.end -= text_len - strip_len
                hi.text = stripped
                text_len = len(stripped)

            stripped = hi.text.lstrip()
            if (strip_len := len(stripped)) != text_len:
                hi.start += text_len - strip_len
                hi.text = hi.text.lstrip()

    @classmethod
    def reconcile(cls, group, row_count, _=None):
        fields: list[HighlightField] = []

        aligned = HighlightField.align_json_fields(group)

        for suffix, highlights in aligned:
            count = len(highlights)
            blanks = row_count - count

            match Counter([astuple(h) for h in highlights]).most_common():

                # Nobody chose a value
                case []:
                    note = (
                        f"The {row_count} {P('record', row_count)} "
                        f"{P('is', row_count)} blank"
                    )
                    return cls(note=note, flag=Flag.ALL_BLANK)

                # Only one selected
                case [c0] if c0[1] == 1:
                    start, end, text, label = c0[0]
                    label = f"{label}_{suffix}"
                    note = (
                        f"Only 1 highlight in {count} {P('record', count)} "
                        f"with {blanks} {P('blank', blanks)}"
                    )
                    fields.append(
                        cls(
                            name=label,
                            note=note,
                            start=start,
                            end=end,
                            text=text,
                            label=label,
                            flag=Flag.ONLY_ONE,
                        )
                    )

                # Everyone chose the same value
                case [c0] if c0[1] == count and c0[1] > 1:
                    start, end, text, label = c0[0]
                    label = f"{label}_{suffix}"
                    note = (
                        f"Exact unanimous match, {c0[1]} "
                        f"of {count} {P('record', count)} "
                        f"with {blanks} {P('blank', blanks)}"
                    )
                    fields.append(
                        cls(
                            name=label,
                            note=note,
                            start=start,
                            end=end,
                            text=text,
                            label=label,
                            flag=Flag.UNANIMOUS,
                        )
                    )

                # It was a tie for the text chosen
                case [c0, c1, *_] if c0[1] > 1 and c0[1] == c1[1]:
                    start, end, text, label = c0[0]
                    label = f"{label}_{suffix}"
                    note = (
                        f"Match is a tie, {c0[1]} "
                        f"of {row_count} {P('record', row_count)} "
                        f"with {blanks} {P('blank', blanks)}"
                    )
                    fields.append(
                        cls(
                            name=label,
                            note=note,
                            start=start,
                            end=end,
                            text=text,
                            label=label,
                            flag=Flag.MAJORITY,
                        )
                    )

                # We have a winner
                case [c0, *_] if c0[1] > 1:
                    start, end, text, label = c0[0]
                    label = f"{label}_{suffix}"
                    note = (
                        f"Match {c0[1]} of {row_count} {P('record', row_count)} "
                        f"with {blanks} {P('blank', blanks)}"
                    )
                    fields.append(
                        cls(
                            name=label,
                            note=note,
                            start=start,
                            end=end,
                            text=text,
                            label=label,
                            flag=Flag.MAJORITY,
                        )
                    )

                # They're all different
                case [c0, *_] if c0[1] == 1:
                    start, end, text, label = c0[0]
                    label = f"{label}_{suffix}"
                    note = (
                        f"No match on {row_count} {P('record', row_count)} "
                        f"with {blanks} {P('blank', blanks)}"
                    )
                    fields.append(
                        cls(
                            name=label,
                            note=note,
                            start=start,
                            end=end,
                            text=text,
                            label=label,
                            flag=Flag.NO_MATCH,
                        )
                    )

                case _:
                    sys.exit(f"Unknown pattern {highlights}")

        return fields

    @staticmethod
    def align_json_fields(group) -> list["HighlightField"]:
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
