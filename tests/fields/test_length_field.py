import unittest

from pylib.fields.length_field import LengthField
from pylib.fields.base_field import Flag


class TestLengthField(unittest.TestCase):
    def test_reconcile_01(self):
        """It handles the happy case."""
        group = [
            [LengthField(name="len", x1=0, y1=0, x2=0, y2=0)],
            [LengthField(name="len", x1=10, y1=40, x2=40, y2=80)],
            [LengthField(name="len", x1=20, y1=80, x2=80, y2=160)],
        ]
        self.assertEqual(
            LengthField.reconcile(group, row_count=len(group)),
            [
                LengthField(
                    name="len",
                    note="There are 3 of 3 length records",
                    flag=Flag.OK,
                    x1=10,
                    y1=40,
                    x2=40,
                    y2=80,
                    pixel_length=50.0,
                )
            ],
        )

    def test_reconcile_02(self):
        """It handles the happy case for a ruler."""
        group = [
            [LengthField(name="1 mm", x1=0, y1=0, x2=0, y2=0)],
            [LengthField(name="1 mm", x1=10, y1=40, x2=40, y2=80)],
            [LengthField(name="1 mm", x1=20, y1=80, x2=80, y2=160)],
        ]
        expect = [
            LengthField(
                name="1 mm",
                note="There are 3 of 3 length records",
                flag=Flag.OK,
                x1=10,
                y1=40,
                x2=40,
                y2=80,
                pixel_length=50.0,
                factor=0.02,
                units="mm",
                is_scale=True,
            )
        ]
        actual = LengthField.reconcile(group, row_count=len(group))
        self.assertEqual(actual, expect)

    def test_reconcile_03(self):
        """It calculates length from ruler units & factor."""
        group = [
            [
                LengthField(name="Length", x1=0.0, y1=0.0, x2=20.0, y2=0.0),
                LengthField(name="1 mm", x1=0.0, y1=0.0, x2=10.0, y2=0.0),
            ],
            [
                LengthField(name="Length", x1=0.0, y1=0.0, x2=20.0, y2=0.0),
                LengthField(name="1 mm", x1=0.0, y1=0.0, x2=10.0, y2=0.0),
            ],
        ]
        actual = LengthField.reconcile(group, row_count=len(group))
        expect = [
            LengthField(
                name="Length",
                note="There are 2 of 2 length records",
                flag=Flag.OK,
                x1=0,
                y1=0,
                x2=20,
                y2=0,
                pixel_length=20.0,
                length=2.0,
                units="mm",
            ),
            LengthField(
                name="1 mm",
                note="There are 2 of 2 length records",
                x1=0,
                y1=0,
                x2=10,
                y2=0,
                pixel_length=10.0,
                flag=Flag.OK,
                factor=0.1,
                units="mm",
                is_scale=True,
            ),
        ]
        self.assertEqual(actual, expect)
