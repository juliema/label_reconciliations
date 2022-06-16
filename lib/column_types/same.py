"""
Reconcile a group where all values are the same.

We first check that this is true. If it is then we return the one item. If it
isn't then we return a blank.
"""


def reconcile(group, args=None):  # noqa
    values = [g for g in group]
    count = len(values)

    if count == 1:
        value = values[0]
        reason = "There is only one record"
    elif all(v == values[0] for v in values):
        value = values[0]
        reason = f"All {count} records are identical"
    else:
        value = ""
        reason = f"All {count} records are not identical"

    return reason, value
