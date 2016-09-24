import os
import re
import sys
import json
import pandas as pd
from collections import Counter
from itertools import combinations
from fuzzywuzzy import process, fuzz

# PLACE_HOLDERS = ['placeholder']


def reconcile_select(group):
    counts = Counter(group)
    common = counts.most_common()
    # if common[0][0]:
    #     return common[0][0]
    # return common[0][0] if len(counts) == 1 else common[1][0]
    return common[0][0]


def reconcile_text(group):
    counts = Counter(group)
    common = counts.most_common()
    if common[0][1] > 1:
        return common[0][0]
    return ''


def reconcile(raw_extracts_file):
    df = pd.read_csv(raw_extracts_file)
    # df = df.loc[:9, :]
    select_cols = {c: reconcile_select for c in df.columns if re.match(r'T\d+s:', c)}
    text_cols = {c: reconcile_text for c in df.columns if re.match(r'T\d+t:', c)}
    aggregate_cols = dict(list(select_cols.items()) + list(text_cols.items()))
    grouped = df.fillna('').groupby('subject_ids').aggregate(aggregate_cols)
    grouped.sort(axis=1, inplace=True)
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
