import unittest

from pylib.fields.select_field import SelectField
from pylib.fields.base_field import Flag


class TestSelectField(unittest.TestCase):
    def test_reconcile_01(self):
        """It handles an empty group."""
        group = [SelectField(), SelectField(), SelectField()]
        self.assertEqual(
            SelectField.reconcile(group, row_count=len(group)),
            SelectField(note="All 3 records are blank", flag=Flag.ALL_BLANK),
        )

    def test_reconcile_02(self):
        """It handles a unanimous match."""
        group = [
            SelectField(value="Is same"),
            SelectField(value="Is same"),
            SelectField(value="Is same"),
        ]
        self.assertEqual(
            SelectField.reconcile(group, row_count=len(group)),
            SelectField(
                note="Unanimous match, 3 of 3 records 0 blanks",
                value="Is same",
                flag=Flag.UNANIMOUS,
            ),
        )

    def test_reconcile_03(self):
        """It handles a tied match."""
        group = [
            SelectField(value="Are same"),
            SelectField(value="Is same"),
            SelectField(value="Are same"),
            SelectField(value="Is same"),
        ]
        self.assertEqual(
            SelectField.reconcile(group, row_count=len(group)),
            SelectField(
                note="Match is a tie, 2 of 4 records with 0 blanks",
                value="Are same",
                flag=Flag.MAJORITY,
            ),
        )

    def test_reconcile_04(self):
        """It reports a majority match."""
        group = [
            SelectField(value="Are same"),
            SelectField(value="Is same"),
            SelectField(value=""),
            SelectField(value="Are same"),
        ]
        self.assertEqual(
            SelectField.reconcile(group, row_count=len(group)),
            SelectField(
                note="Match 2 of 4 records with 1 blank",
                value="Are same",
                flag=Flag.MAJORITY,
            ),
        )

    def test_reconcile_05(self):
        """It reports a majority match."""
        group = [
            SelectField(value=" "),
            SelectField(value="Is value"),
        ]
        self.assertEqual(
            SelectField.reconcile(group, row_count=len(group)),
            SelectField(
                note="Only 1 transcript in 2 records with 1 blank",
                value="Is value",
                flag=Flag.ONLY_ONE,
            ),
        )

    def test_reconcile_06(self):
        """It reports a majority match."""
        group = [
            SelectField(value=" "),
            SelectField(value="Is value"),
            SelectField(value="Different"),
        ]
        self.assertEqual(
            SelectField.reconcile(group, row_count=len(group)),
            SelectField(
                note="No match on 3 records with 1 blank",
                flag=Flag.NO_MATCH,
                value="Is value",
            ),
        )
