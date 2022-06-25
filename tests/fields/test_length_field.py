import unittest

from pylib.fields.length_field import LengthField
from pylib.result import Result


class TestLengthField(unittest.TestCase):
    def test_reconcile_01(self):
        """It handles the happy case."""
        group = [
            LengthField(x1=0, y1=0, x2=30, y2=30),
            LengthField(x1=10, y1=10, x2=40, y2=40),
            LengthField(x1=20, y1=20, x2=50, y2=50),
        ]
        self.assertEqual(
            LengthField.reconcile(group),
            LengthField(
                note="There are 3 length records",
                result=Result.OK,
                x1=10,
                y1=10,
                x2=40,
                y2=40,
                pixel_length=42.43,
            ),
        )
