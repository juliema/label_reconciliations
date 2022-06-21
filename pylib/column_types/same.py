"""Reconcile a group where all values are supposed to be the same."""
from pylib import cell


def reconcile(group, args=None):  # noqa pylint: disable=unused-argument
    values = list(group.astype(str))

    if all(v == values[0] for v in values):
        return cell.no_flag(no_label=values[0])

    value = ",".join(values)
    return cell.error(no_label=value)
