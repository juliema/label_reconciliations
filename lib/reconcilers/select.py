"""Reconcile select lists. classifications are chosen from a controlled
vocabulary."""

from collections import Counter
import inflect

HAS_EXPLANATIONS = True

PLACEHOLDERS = ['placeholder']
E = inflect.engine()
E.defnoun('The', 'All')
P = E.plural


def reconcile(group, args=None):
    """Reconcile the data."""

    values = [str(g) if str(g).lower() not in PLACEHOLDERS else ''
              for g in group]

    filled = Counter([v for v in values if v.strip()]).most_common()

    count = len(values)
    blanks = count - sum([f[1] for f in filled])

    if not filled:
        reason = [P('The', count), str(count), P('record', count),
                  P('is', count), 'blank']
        return ' '.join(reason), ''

    if filled[0][1] > 1:
        reason = ['Exact match,', filled[0][1], 'of', str(count),
                  P('record', count), 'with', str(blanks), P('blank', blanks)]
        return ' '.join(reason), filled[0][0]

    if filled[0][1] == 1:
        reason = ['Only 1 transcript in', str(count), P('record', count)]
        return ' '.join(reason), filled[0][0]

    reason = ['No exact match on', str(count), P('record', count),
              'with', str(blanks), P('blank', blanks)]
    return ' '.join(reason), ''
