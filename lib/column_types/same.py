"""
Reconcile a group where all values are the same.

We first check that this is true. If it is then we return the one item. If it
isn't then we return a blank.
"""


def reconcile(group, args=None):  # pylint: disable=unused-argument
    """Reconcile the data."""
    values = [g for g in group]
    count = len(values)

    if count == 1:
        value = values[0]
        reason = 'There is only one record'
    elif all(v == values[0] for v in values):
        value = values[0]
        reason = 'All {} records are identical'.format(count)
    else:
        value = ''
        reason = 'All {} records are not identical'.format(count)

    return reason, value
