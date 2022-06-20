"""Reconcile a group where all values are supposed to be the same."""
from .. import cell


def reconcile(group, args=None):  # noqa
    values = [g for g in group]
    count = len(values)

    if count == 1:
        return cell.ok(note="There is only one record", value=values[0])

    if all(v == values[0] for v in values):
        return cell.ok(note=f"All {count} records are identical", value=values[0])

    value = ",".join(values)
    return cell.error(note="All {count} records are not identical", value=value)
