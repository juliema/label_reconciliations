"""Test functions in lib/formats/nfn.py."""

from argparse import Namespace
from unittest.mock import patch
import pandas as pd
import lib.formats.nfn as nfn


def set_up():
    """Setup mock dataframes."""
    df1 = pd.read_csv('tests/data/nfn1.csv', dtype=str)
    df2 = pd.read_csv('tests/data/nfn2.csv', dtype=str)
    return df1, df2

def test_get_workflow_id_01():
    """It handles returns a given workflow ID."""
    _, df2 = set_up()
    args = Namespace(workflow_id='1001')

    workflow_id = nfn.get_workflow_id(df2, args)

    assert workflow_id == '1001'

def test_get_workflow_id_unique():
    """It finds a unique workflow ID."""
    df1, _ = set_up()
    args = Namespace(workflow_id=None)

    workflow_id = nfn.get_workflow_id(df1, args)

    assert workflow_id == '1001'

@patch('lib.util.error_exit')
def test_get_workflow_id_error(error_exit):
    """It errors when there are multiple workflow IDs to choose."""
    _, df2 = set_up()
    args = Namespace(workflow_id=None)

    nfn.get_workflow_id(df2, args)

    error_exit.assert_called_once_with(
        ('There are multiple workflows in this file. '
         'You must provide a workflow ID as an argument.'))
