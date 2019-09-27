"""Reconcile a box annotation."""

import json
from functools import partial
from statistics import mean
import inflect


P = inflect.engine().plural


def reconcile(group, args=None):  # pylint: disable=unused-argument
    """Reconcile the data."""
    raw_boxes = [json.loads(b) for b in group]

    overlaps = [0] * len(raw_boxes)
    for i, box1 in enumerate(raw_boxes[:-1]):
        for j, box2 in enumerate(raw_boxes[1:], 1):
            if overlaps_2d(box1, box2):
                overlaps[i] = 1
                overlaps[j] = 1
    boxes = [b for i, b in enumerate(raw_boxes) if overlaps[i]]

    if not boxes:
        reason = 'There are no overlapping boxes in {} {}'.format(
            len(raw_boxes), P('record', len(raw_boxes)))
        return reason, {}

    count = len(boxes)

    reason = 'There {} {} overlapping {} in {} {}'.format(
        P('was', count), len(boxes), P('box', count),
        len(raw_boxes), P('record', len(raw_boxes)))

    box = {
        'left': round(mean(b['left'] for b in boxes)),
        'right': round(mean(b['right'] for b in boxes)),
        'top': round(mean(b['top'] for b in boxes)),
        'bottom': round(mean(b['bottom'] for b in boxes))}

    return reason, json.dumps(box)


def overlaps_2d(box1, box2):
    """Check if the boxes overlap."""
    return overlaps_1d(box1, box2, 'left', 'right') \
        and overlaps_1d(box1, box2, 'top', 'bottom')


def overlaps_1d(seg1, seg2, min_edge, max_edge):
    """Check if the line segments overlap."""
    return seg1[min_edge] <= seg2[max_edge] \
        and seg2[min_edge] <= seg1[max_edge]


def adjust_reconciled_columns(reconciled, column_types):
    """Split reconciled results into separate x, y, height, & width columns."""
    columns = {c for c in reconciled.columns
               if column_types.get(c, {'type': ''})['type'] == 'box'}
    for column in columns:
        reconciled[column] = reconciled[column].apply(json.loads)
        for i, edge in enumerate(['left', 'right', 'top', 'bottom'], 1):
            column_name = '{} {}'.format(column, edge)
            column_types[column_name] = {
                'type': 'box',
                'order': column_types[column]['order'] + i,
                'name': column_name}
            reconciled[column_name] = reconciled[column].apply(
                partial(_get_edge, edge=edge))
        reconciled[column] = reconciled[column].apply(json.dumps)
    return reconciled


def _get_edge(box, edge=None):
    return box[edge]
