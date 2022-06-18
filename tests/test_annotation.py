import unittest

from lib.formats import nfn


class TestFlattenAnnotation(unittest.TestCase):
    def test_flatten_annotation_01(self):
        """It handles a list annotation."""
        workflow_strings = nfn.WorkflowStrings()
        column_types, annos, anno_id = {}, {}, ""
        anno = {"value": ["val1", "val2"], "task_label": "T1", "key1": 1, "key2": 2}
        nfn.flatten_annotation(column_types, annos, anno, anno_id, workflow_strings)
        self.assertEqual(column_types, {"T1": "text"})
        self.assertEqual(annos, {"T1": "val1 val2"})
