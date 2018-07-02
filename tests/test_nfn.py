"""Test functions in lib/formats/nfn.py."""

from argparse import Namespace
import unittest
from unittest.mock import patch
import pandas as pd
import lib.formats.nfn as nfn


class TestAtramPreprocessor(unittest.TestCase):

    def setUp(self):
        self.df1 = pd.read_csv('tests/data/nfn1.csv', dtype=str)
        self.df2 = pd.read_csv('tests/data/nfn2.csv', dtype=str)

    def test_get_workflow_id_given(self):
        args = Namespace(workflow_id='1001')

        workflow_id = nfn.get_workflow_id(self.df2, args)

        assert workflow_id == '1001'

    def test_get_workflow_id_unique(self):
        args = Namespace(workflow_id=None)

        workflow_id = nfn.get_workflow_id(self.df1, args)

        assert workflow_id == '1001'

    @patch('lib.util.error_exit')
    def test_get_workflow_id_error(self, error_exit):
        args = Namespace(workflow_id=None)

        nfn.get_workflow_id(self.df2, args)

        error_exit.assert_called_once_with(
            ('There are multiple workflows in this file. '
             'You must provide a workflow ID as an argument.'))
