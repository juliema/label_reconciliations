import unittest

from pylib.fields.text_field import TextField
from pylib.formats import nfn
from pylib.result import Result
from pylib.row import Row


class TestFlattenAnnotation(unittest.TestCase):
    def test_flatten_annotation_01(self):
        """It handles a list annotation."""
        workflow_strings = nfn.WorkflowStrings()
        row = Row()
        anno = {
            "task": "T1",
            "value": ["val1", "val2"],
            "task_label": "testing",
            "other1": 1,
            "other2": 2,
        }
        nfn.flatten_task(anno, row, workflow_strings)
        self.assertEqual(
            row,
            {
                "T1_1 testing": TextField(
                    key="T1_1 testing",
                    note="",
                    result=Result.NO_FLAG,
                    is_reconciled=False,
                    value="val1 val2",
                )
            },
        )
