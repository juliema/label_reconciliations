"""Reconcile a group where all values are the same. We first check that this
is true If it is then we return the one item. If it isn't then we return
a blank."""

HAS_EXPLANATIONS = False


def reconcile(group, args=None):
    """Reconcile the data."""

    values = [g for g in group]

    return values[0] if all([v == values[0] for v in values]) else ''
