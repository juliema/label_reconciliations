"""Get the mean median and mode for the group. Handle blanks and non-numerics.
"""

import numpy as np
import scipy.stats as stats
import inflect

P = inflect.engine().plural


def reconcile(group, args=None):  # pylint: disable=unused-argument
    """Reconcile the data."""

    values = [g for g in group]

    numbers = []
    for value in values:
        try:
            numbers.append(float(value))
        except ValueError:
            pass

    mean = np.mean(numbers)
    median = np.median(numbers)
    mode = stats.mode(numbers)

    value = 'mean={}, median={}, mode={} (occurs {} {})'.format(
        mean, median, mode.mode[0], mode.count[0], P('time', mode.count[0]))

    reason = 'There were {} {} out of {} {}'.format(
        len(numbers), P('number', len(numbers)),
        len(values), P('value', len(values)))

    return reason, value
