import unittest

from pylib.fields.highlighter_field import HighlightField
from pylib.fields.base_field import Flag


class TestHighlighterField(unittest.TestCase):
    def test_reconcile_01(self):
        """It handles a unanimous match."""
        group = [
            [
                HighlightField(
                    name="highlighter",
                    task_id="T01",
                    field_set="set",
                    start=0,
                    end=4,
                    text="text",
                    label="field",
                )
            ],
            [
                HighlightField(
                    name="highlighter",
                    task_id="T01",
                    field_set="set",
                    start=0,
                    end=4,
                    text="text",
                    label="field",
                )
            ],
            [
                HighlightField(
                    name="highlighter",
                    task_id="T01",
                    field_set="set",
                    start=0,
                    end=4,
                    text="text",
                    label="field",
                )
            ],
        ]
        actual = HighlightField.reconcile(group, row_count=len(group))
        self.assertEqual(
            actual,
            [
                HighlightField(
                    name="highlighter",
                    note="Exact unanimous match, 3 of 3 records with 0 blanks",
                    flag=Flag.UNANIMOUS,
                    field_set="set",
                    suffix=1,
                    task_id="T01",
                    start=0,
                    end=4,
                    text="text",
                    label="field",
                    span=1,
                )
            ],
        )

    def test_reconcile_02(self):
        """It handles a unanimous across two highlights."""
        group = [
            [
                HighlightField(
                    name="highlighter",
                    task_id="T01",
                    field_set="set",
                    start=0,
                    end=4,
                    text="text1",
                    label="field",
                ),
                HighlightField(
                    name="highlighter",
                    task_id="T01",
                    field_set="set",
                    start=10,
                    end=14,
                    text="text2",
                    label="field",
                ),
            ],
            [
                HighlightField(
                    name="highlighter",
                    task_id="T01",
                    field_set="set",
                    start=0,
                    end=4,
                    text="text1",
                    label="field",
                ),
                HighlightField(
                    name="highlighter",
                    task_id="T01",
                    field_set="set",
                    start=10,
                    end=14,
                    text="text2",
                    label="field",
                ),
            ],
            [
                HighlightField(
                    name="highlighter",
                    task_id="T01",
                    field_set="set",
                    start=0,
                    end=4,
                    text="text1",
                    label="field",
                )
            ],
        ]
        actual = HighlightField.reconcile(group, row_count=len(group))
        self.assertEqual(
            actual,
            [
                HighlightField(
                    name="highlighter",
                    task_id="T01",
                    note="Exact unanimous match, 3 of 3 records with 0 blanks",
                    flag=Flag.UNANIMOUS,
                    field_set="set",
                    suffix=1,
                    start=0,
                    end=4,
                    text="text1",
                    label="field",
                    span=1,
                ),
                HighlightField(
                    name="highlighter",
                    task_id="T01",
                    note="Exact unanimous match, 2 of 3 records with 1 blank",
                    flag=Flag.UNANIMOUS,
                    field_set="set",
                    suffix=2,
                    start=10,
                    end=14,
                    text="text2",
                    label="field",
                    span=1,
                ),
            ],
        )

    def test_reconcile_03(self):
        """It handles field overlap."""
        group = [
            [
                HighlightField(
                    name="highlighter",
                    task_id="T01",
                    field_set="set",
                    start=0,
                    end=4,
                    text="text1",
                    label="field",
                )
            ],
            [
                HighlightField(
                    name="highlighter",
                    task_id="T01",
                    field_set="set",
                    start=1,
                    end=5,
                    text="ext11",
                    label="field",
                )
            ],
            [
                HighlightField(
                    name="highlighter",
                    task_id="T01",
                    field_set="set",
                    start=10,
                    end=14,
                    text="text2",
                    label="field",
                )
            ],
        ]
        actual = HighlightField.reconcile(group, row_count=len(group))
        self.assertEqual(
            actual,
            [
                HighlightField(
                    name="highlighter",
                    task_id="T01",
                    note="No match on 2 records with 1 blank",
                    flag=Flag.NO_MATCH,
                    field_set="set",
                    suffix=1,
                    start=0,
                    end=4,
                    text="text1",
                    label="field",
                    span=1,
                ),
                HighlightField(
                    name="highlighter",
                    task_id="T01",
                    note="Only 1 highlight in 1 record with 2 blanks",
                    flag=Flag.ONLY_ONE,
                    field_set="set",
                    suffix=2,
                    start=10,
                    end=14,
                    text="text2",
                    label="field",
                    span=1,
                ),
            ],
        )
