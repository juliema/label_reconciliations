import unittest

from pylib.fields.length_field import LengthField
from pylib.fields.noop_field import NoOpField
from pylib.flag import Flag
from pylib.row import Row


class TestLengthField(unittest.TestCase):
    def test_reconcile_01(self):
        """It handles the happy case."""
        group = [
            LengthField(x1=0, y1=0, x2=0, y2=0),
            LengthField(x1=10, y1=40, x2=40, y2=80),
            LengthField(x1=20, y1=80, x2=80, y2=160),
        ]
        self.assertEqual(
            LengthField.reconcile(group),
            LengthField(
                note="There are 3 length records",
                flag=Flag.OK,
                x1=10,
                y1=40,
                x2=40,
                y2=80,
                pixel_length=50.0,
            ),
        )

    def test_reconcile_02(self):
        """It handles the happy case."""
        group = [
            LengthField(key="1 mm", x1=0, y1=0, x2=0, y2=0),
            LengthField(key="1 mm", x1=10, y1=40, x2=40, y2=80),
            LengthField(key="1 mm", x1=20, y1=80, x2=80, y2=160),
        ]
        self.assertEqual(
            LengthField.reconcile(group),
            LengthField(
                note="There are 3 length records",
                flag=Flag.OK,
                x1=10,
                y1=40,
                x2=40,
                y2=80,
                pixel_length=50.0,
                factor=0.02,
                units="mm",
                is_scale=True,
            ),
        )

    def test_reconcile_row_01(self):
        self.maxDiff = None
        row = Row()
        row.add_field("nothing", NoOpField())
        row.add_field("Length", LengthField(pixel_length=200))
        row.add_field("Ruler", LengthField(factor=0.01, units="LY", is_scale=True))
        LengthField.reconcile_row(row)
        self.assertEqual(
            row["Length"],
            LengthField(key="Length", pixel_length=200.0, length=2.0, units="LY"),
        )
