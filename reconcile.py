import os
import re
import sys
import json
import difflib
import pandas as pd
from collections import Counter, namedtuple
from itertools import combinations
from fuzzywuzzy import fuzz

PLACE_HOLDERS = ['placeholder']

# For working with Counter's arrray of tuples
Count = namedtuple('Count', 'value count')

# For working with simple inplace fuzzy matches
PartialRatio = namedtuple('PartialRatio', 'score longer_value shorter_value')


def reconcile_select(group):
    # Replace placeholders with blanks
    group = [g if g.lower() not in PLACE_HOLDERS else '' for g in group]

    # Look for identical matches and order them by how common they are
    counts = [Count(c[0], c[1]) for c in Counter(group).most_common()]

    # Look at the counts for the non-blank entries
    filled = [c for c in counts if c.value]

    # Return the first non-blank entry or blank if they're all blank
    return filled[0].value if len(filled) else ''


def top_partial_ratio(group):
    # Create a list of tuples [(score, longer_value, shorter_value)]
    ratios = []
    for c in combinations(group, 2):
        score = fuzz.partial_ratio(c[0], c[1])
        (longer_value, shorter_value) = (c[0], c[1]) if len(c[0]) >= len(c[1]) else (c[1], c[0])
        ratios.append(PartialRatio(score, longer_value, shorter_value))

    # Sort by score descending, then by length of the longer_value descending
    ordered = sorted(ratios, key=lambda r: '{:0>6} {:0>6}'.format(r.score, len(r.longer_value)), reverse=True)
    return ordered[0]


def top_token_set_ratio(group):
    ratios = []
    # for c in combinations


def reconcile_text(group):
    # Normalize spaces and EOLs
    group = ['\n'.join([' '.join(ln.split()) for ln in g.splitlines()]) for g in group]

    # Look for identical matches and order them by how common they are
    counts = [Count(c[0], c[1]) for c in Counter(group).most_common()]

    # Look at the counts for the non-blank entries
    filled = [c for c in counts if c.value]

    # If everything is blank we're done
    if not len(filled):
        return ''

    # If the most common value is not blank and its count > 1 then return it
    # Or if there is only one non-blank value
    if filled[0].count > 1 or len(filled) == 1:
        return filled[0].value

    # Check for simple inplace fuzzy matches
    top = top_partial_ratio(group)
    if top.score == 100:  # The threshold could be tweaked here. Maybe make it an argument?
        return top.longer_value

    # Now look for the best token match take the longest token length with with the shortest string length

    return None


def reconcile(raw_extracts_file):
    df = pd.read_csv(raw_extracts_file)
    # df = df.loc[:9, :]
    select_cols = {c: reconcile_select for c in df.columns if re.match(r'T\d+s:', c)}
    text_cols = {c: reconcile_text for c in df.columns if re.match(r'T\d+t:', c)}
    aggregate_cols = dict(list(select_cols.items()) + list(text_cols.items()))
    grouped = df.fillna('').groupby('subject_ids').aggregate(aggregate_cols)
    grouped.sort_index(axis=1, inplace=True)
    print(grouped.head())
    # Reconcile dates
    # Output reconciled data


def args():
    if len(sys.argv) < 2:
        help()
    if not os.path.isfile(sys.argv[1]):
        help('Cannot read raw extracts file "{}".'.format(sys.argv[1]))
    return sys.argv[1]


def help(msg=''):
    print('Usage: python reconcile.py <raw extracts file>')
    if msg:
        print(msg)
    sys.exit()


if __name__ == "__main__":
    raw_extracts_file = args()
    reconcile(raw_extracts_file)
