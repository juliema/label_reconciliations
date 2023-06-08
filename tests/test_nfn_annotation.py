import unittest

from pylib.fields.text_field import TextField
from pylib.formats import nfn
from pylib.flag import Flag
from pylib.row import Row


class TestFlattenAnnotation(unittest.TestCase):
    def test_flatten_annotation_01(self):
        """It handles a list annotation."""
        anno = {
            "task": "T1",
            "value": ["val1", "val2"],
            "task_label": "testing",
            "other1": 1,
            "other2": 2,
        }
        expect = Row()
        expect.add_field(
            "T1_1 testing",
            TextField(
                name="T1_1 testing",
                note="",
                flag=Flag.NO_FLAG,
                is_padding=False,
                value="val1 val2",
            )
        )
        actual = Row()
        nfn.flatten_task(anno, actual, {}, {})
        self.assertEqual(actual, expect)
