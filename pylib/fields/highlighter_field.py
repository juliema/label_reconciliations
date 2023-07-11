import re
import sys
from collections import defaultdict
from dataclasses import dataclass, replace
from typing import Any

from pylib.fields.base_field import BaseField
from pylib.flag import Flag
from pylib.utils import P


@dataclass(kw_only=True)
class HighlightField(BaseField):
    start: int = -1
    end: int = -1
    text: str = ""
    label: str = ""

    @property
    def name_group(self) -> str:
        return f"{self.task_id}_{self.name}_{self.label}"

    @classmethod
    def unreconciled_list(
        cls, task: dict[str, Any], task_id: str, args, text: str = ""
    ) -> list["HighlightField"]:
        """Create an unreconciled list from the values list."""
        highlights = []
        for value in task["value"]:
            field = HighlightField(
                name=task["taskType"],
                task_id=task_id,
                label=value["labelInformation"]["label"],
                text=value["text"],
                start=value["start"],
                end=value["end"] + 1,
            )
            field.field_set = field.name_group
            highlights.append(field)

        highlights = HighlightField._join(highlights, args.join_distance, text)
        HighlightField._strip(highlights)
        return highlights

    def to_dict(self, reconciled=False) -> dict[str, Any]:
        field_dict = {
            self.header("text"): self.text,
            self.header("position"): f"({self.start}, {self.end})",
        }
        return field_dict

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
    def reconcile(cls, group, row_count, args=None):
        fields: list[HighlightField] = []

        aligned = HighlightField.align_json_fields(group)

        for _, highlights in aligned.items():
            count = len(highlights)
            blanks = row_count - count

            by_value = defaultdict(list)
            for hi in highlights:
                by_value[(hi.text, hi.start, hi.end)].append(hi)
            counters = sorted(by_value.values(), key=lambda highs: -len(highs))

            match counters:
                # Nobody chose a value
                case []:
                    note = (
                        f"The {row_count} {P('record', row_count)} "
                        f"{P('is', row_count)} blank"
                    )
                    fields.append(cls(note=note, flag=Flag.ALL_BLANK))

                # Only one selected
                case [c0] if len(c0) == 1:
                    note = (
                        f"Only 1 highlight in {count} {P('record', count)} "
                        f"with {blanks} {P('blank', blanks)}"
                    )
                    fields.append(replace(c0[0], flag=Flag.ONLY_ONE, note=note))

                # Everyone chose the same value
                case [c0] if len(c0) == count and len(c0) > 1:
                    note = (
                        f"Exact unanimous match, "
                        f"{len(c0)} of {row_count} {P('record', row_count)} "
                        f"with {blanks} {P('blank', blanks)}"
                    )
                    fields.append(replace(c0[0], flag=Flag.UNANIMOUS, note=note))

                # It was a tie for the text chosen
                case [c0, c1, *_] if len(c0) > 1 and len(c0) == len(c1):
                    note = (
                        f"Match is a tie, {len(c0)} "
                        f"of {row_count} {P('record', row_count)} "
                        f"with {blanks} {P('blank', blanks)}"
                    )
                    fields.append(replace(c0[0], flag=Flag.MAJORITY, note=note))

                # We have a winner
                case [c0, *_] if len(c0) > 1:
                    note = (
                        f"Match {len(c0)} of {row_count} {P('record', row_count)} "
                        f"with {blanks} {P('blank', blanks)}"
                    )
                    fields.append(replace(c0[0], flag=Flag.MAJORITY, note=note))

                # They're all different
                case [c0, *_] if len(c0) == 1:
                    note = (
                        f"No match on {row_count} {P('record', row_count)} "
                        f"with {blanks} {P('blank', blanks)}"
                    )
                    fields.append(replace(c0[0], flag=Flag.NO_MATCH, note=note))

                case _:
                    sys.exit(f"Unknown pattern {highlights}")

        return fields

    @staticmethod
    def align_json_fields(group) -> dict[str, list["HighlightField"]]:
        aligned = defaultdict(list)

        all_highlights = [h for row in group for h in row]

        # Get the extremes of the highlighted field
        start = min([h.start for h in all_highlights], default=0)
        end = max([h.end for h in all_highlights], default=0)

        # Mark where the highlights are in the string
        hits = bytearray(end - start)
        for hi in all_highlights:
            for i in range(hi.start, hi.end):
                hits[i - start] = 1

        # Get all contiguous matches
        contigs = [
            (m.start() + start, m.end() + start) for m in re.finditer(b"(\x01+)", hits)
        ]

        for i, (start, end) in enumerate(contigs, 1):
            for row in group:
                parts: list[HighlightField] = [h for h in row if start <= h.start < end]

                if not parts:
                    continue

                parts = sorted(parts, key=lambda p: p.start)

                # Update unreconciled suffixes to match the reconciled span
                for j, part in enumerate(parts):
                    part.suffix = i if j == 0 else float(f"{i}.{j}")

                # Add a reconciled record, one for each set of parts
                high = HighlightField(
                    name=parts[0].name,
                    task_id=parts[0].task_id,
                    start=min(p.start for p in parts),
                    end=max(p.end for p in parts),
                    text=" ".join(p.text for p in parts),  # TODO when strings
                    label=parts[0].label,
                    field_set=parts[0].field_set,
                    suffix=i,
                )
                aligned[(start, end)].append(high)

        return aligned
