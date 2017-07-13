"""Reconcile a group where all values are the same. We just pick an arbitrary
value; in this case, the first one."""

HAS_EXPLANATIONS = False


def reconcile(group, args=None):
    """Reconcile the data. We return an arbitrary value from the group."""

    values = [g for g in group]
    return values[0]
