"""Test functions in lib/formats/nfn.py."""

# pylama: ignore=D103

from argparse import Namespace
import lib.util as util
import lib.formats.nfn as nfn
import tests.mock as mock
import pandas as pd


def get_df1():
    return pd.read_csv('tests/data/nfn1.csv', dtype=str)


# Some mock dataframes can be reused
DF1 = get_df1()
DF2 = pd.read_csv('tests/data/nfn2.csv', dtype=str)


def test_get_workflow_id_given():
    args = Namespace(workflow_id='1001')

    workflow_id = nfn.get_workflow_id(DF2, args)

    assert workflow_id == '1001'


def test_get_workflow_id_unique():
    args = Namespace(workflow_id=None)

    workflow_id = nfn.get_workflow_id(DF1, args)

    assert workflow_id == '1001'


def test_get_workflow_id_error():
    args = Namespace(workflow_id=None)
    mock.it(util, 'error_exit')

    nfn.get_workflow_id(DF2, args)

    assert mock.history == [
        {'module': 'lib.util', 'func': 'error_exit',
         'msg': 'There are multiple workflows in this file. '
                'You must provide a workflow ID as an argument.'}]


def test_remove_rows_not_in_workflow_1(monkeypatch):
    pass
