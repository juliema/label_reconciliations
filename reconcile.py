import re
import sys
import json
import argparse
import dateutil
import pandas as pd
from collections import Counter, namedtuple
from itertools import combinations
from fuzzywuzzy import fuzz

PLACE_HOLDERS = ['placeholder']  # Replace these placeholders with an empty string
NO_MATCHES = '<NO MATCHES>'      # A flag for unmatched data
GROUP_BY = 'subject_id'          # We group on this column
SEPARATOR = ':'                  # Used to separate match flags from values

# Type of matching
EXACT_MATCH = 'Exact match'
NORMALIZED_EXACT_MATCH = 'Normalized exact match'
PARTIAL_RATIO_MATCH = 'Partial ratio match'
TOKEN_SET_RATIO_MATCH = 'Token set ratio match'
SELECT_NO_MATCH = '<No match on select>'
TEXT_NO_MATCH = '<No match on text>'
NOT_ENOUGH_TO_MATCH = '<Only one transcript>'

# Useful for naming tuple items, rather than using indexes into tuples
ExactScore = namedtuple('ExactScore', 'value count')
FuzzyRatioScore = namedtuple('FuzzyRatioScore', 'score value')
FuzzySetScore = namedtuple('FuzzySetScore', 'score value tokens')

UNWANTED_COLUMNS = ['subject_data', 'subject_retired', 'subject_subjectId']
COLUMNS_WITH_BAD_DATA = {}  # Subject_* columns with non-identical values in a group
ARGS = None


def extract_json_value(subject_json, column=''):
    if column in list(subject_json.values())[0]:
        return list(subject_json.values())[0][column]


def extract_json_date(metadata_json, column=''):
    return dateutil.parser.parse(metadata_json[column]).strftime('%d-%b-%Y %H:%M:%S')


def header_label(task_id, label, task_type):
    return '{}{:0>3}{}: {}'.format(task_id[0], task_id[1:], task_type, label)


def extract_an_annotaion(df, task, task_id, index):
    if isinstance(task.get('value'), list):
        for subtask in task['value']:
            subtask_id = subtask.get('task', task_id)
            extract_an_annotaion(df, subtask, subtask_id, index)
    elif task.get('select_label'):
        header = header_label(task_id, task['select_label'], 's')
        value = task.get('label')
        df.loc[index, header] = value
    elif task.get('task_label'):
        header = header_label(task_id, task['task_label'], 't')
        value = task.get('value')
        df.loc[index, header] = value
    else:
        print('Error: Could not parse the annotations.')
        sys.exit()


def extract_annotations_json(df):
    df['annotation_json'] = df['annotations'].map(lambda x: json.loads(x))
    for index, row in df.iterrows():
        for task in row['annotation_json']:
            task_id = task['task']
            extract_an_annotaion(df, task, task_id, index)
    df.drop('annotation_json', axis=1, inplace=True)


def extract_subject_json(df):
    df['subject_json'] = df['subject_data'].map(lambda x: json.loads(x))
    subject_keys = {}
    for subj in df['subject_json']:
        for val in iter(subj.values()):
            for k in val.keys():
                subject_keys[k] = 1
    for k in subject_keys.keys():
        df['subject_' + k] = df['subject_json'].apply(extract_json_value, column=k)
    df.drop('subject_json', axis=1, inplace=True)


def extract_metata_json(df):
    df['metadata_json'] = df['metadata'].map(lambda x: json.loads(x))
    df['classification_started_at'] = df['metadata_json'].apply(extract_json_date, column='started_at')
    df['classification_finished_at'] = df['metadata_json'].apply(extract_json_date, column='finished_at')
    df.drop('metadata_json', axis=1, inplace=True)


def expand():
    global ARGS
    subjects_df = pd.read_csv(ARGS.input_subjects)
    df = pd.read_csv(ARGS.input_classifications)

    # We need to do this by workflow because each one's annotations have a different structure
    df = df.loc[df.workflow_id == ARGS.workflow_id, :]

    # bring the last column to be the first
    cols = df.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    df = df[cols]

    # Make key data types match in the two data frames
    df['subject_ids'] = df.subject_ids.map(lambda x: int(str(x).split(';')[0]))

    # Get subject info we need from the subjects_df
    df = pd.merge(df, subjects_df[['subject_id', 'locations']], how='left',
                  left_on='subject_ids', right_on='subject_id')

    extract_metata_json(df)
    extract_annotations_json(df)
    extract_subject_json(df)

    df.drop(['user_id', 'user_ip', 'subject_id'], axis=1, inplace=True)
    df.rename(columns={'subject_ids': 'subject_id'}, inplace=True)
    df.sort_values(['subject_id', 'classification_id'], inplace=True)

    if ARGS.unreconciled:
        df.to_csv(ARGS.unreconciled, sep=',', index=False, encoding='utf-8')


def output(best, match_type, count=None, total=None, score=None):
    if match_type in [EXACT_MATCH, NORMALIZED_EXACT_MATCH]:
        return '{} {}/{}{}{}'.format(match_type, count, total, SEPARATOR, best)
    elif match_type in [PARTIAL_RATIO_MATCH, TOKEN_SET_RATIO_MATCH]:
        return '{} score={}{}{}'.format(match_type, score, SEPARATOR, best)
    return '{}{}{}'.format(match_type, SEPARATOR, best)


def normalize_text(group):
    return ['\n'.join([' '.join(ln.split()) for ln in g.splitlines()]) for g in group]


def top_exact(values):
    counts = [ExactScore(c[0], c[1]) for c in Counter(values).most_common()]
    return counts[0] if counts[0].count > 1 else None


def top_partial_ratio(group):
    scores = []
    for c in combinations(group, 2):
        score = fuzz.partial_ratio(c[0], c[1])
        value = c[0] if len(c[0]) >= len(c[1]) else c[1]
        scores.append(FuzzyRatioScore(score, value))
    scores = sorted(scores, reverse=True, key=lambda s: '{:0>6} {:0>6}'.format(s.score, len(s.value)))
    return scores[0]


def top_token_set_ratio(group):
    scores = []
    for c in combinations(group, 2):
        score = fuzz.token_set_ratio(c[0], c[1])
        tokens_0 = len(c[0].split())
        tokens_1 = len(c[1].split())
        if tokens_0 > tokens_1:
            value = c[0]
            tokens = tokens_0
        elif tokens_0 < tokens_1:
            value = c[1]
            tokens = tokens_1
        else:
            tokens = tokens_0
            value = c[0] if len(c[0]) <= len(c[1]) else c[1]
        scores.append(FuzzySetScore(score, value, tokens))
    ordered = sorted(scores, reverse=True,
                     key=lambda s: '{:0>6} {:0>6} {:0>6}'.format(s.score, s.tokens, 1000000 - len(s.value)))
    return ordered[0]


def reconcile_same(group):
    values = [g for g in group]
    counts = Counter(values)
    # Remove columns where we expect identical values but do not get them
    if len(counts) > 1:
        COLUMNS_WITH_BAD_DATA[group.name] = 1
        return ''
    return values[0]


def reconcile_select(group):
    values = [str(g) if str(g).lower() not in PLACE_HOLDERS else '' for g in group]
    if len(values) < 2:
        return output(NO_MATCHES, NOT_ENOUGH_TO_MATCH)
    top = top_exact(values)
    if top:
        return output(top.value, EXACT_MATCH, count=top.count, total=len(values))
    return output(NO_MATCHES, SELECT_NO_MATCH)


def reconcile_text(group):
    global ARGS

    values = normalize_text(group)
    if len(values) < 2:
        return output(NO_MATCHES, NOT_ENOUGH_TO_MATCH)

    # Look for identical matches and order them by how common they are
    counts = [ExactScore(c[0], c[1]) for c in Counter(values).most_common()]
    if (not counts[0].value and len(counts) == 1) or (counts[0].count > 1):
        return output(counts[0].value, NORMALIZED_EXACT_MATCH, count=counts[0].count, total=len(values))

    # Check for simple inplace fuzzy matches
    top = top_partial_ratio(group)
    if top.score >= ARGS.fuzzy_ratio_threshold:
        return output(top.value, PARTIAL_RATIO_MATCH, score=top.score)

    # Now look for the best token match
    top = top_token_set_ratio(group)
    if top.score >= ARGS.fuzzy_set_threshold:
        return output(top.value, TOKEN_SET_RATIO_MATCH, score=top.score)
    return output(NO_MATCHES, TEXT_NO_MATCH)


def reconcile(unreconciled_df):
    global ARGS

    # How to aggregate the columns based on each column's type which is determined by the column name
    select_cols = {c: reconcile_select for c in unreconciled_df.columns if re.match(r'T\d+s:', c)}
    text_cols = {c: reconcile_text for c in unreconciled_df.columns if re.match(r'T\d+t:', c)}
    subject_cols = {c: reconcile_same for c in unreconciled_df.columns if c.startswith('subject_') and c != GROUP_BY}
    aggregate_cols = dict(list(select_cols.items()) + list(text_cols.items()) + list(subject_cols.items()))
    aggregate_cols['locations'] = reconcile_same
    aggregate_cols = {k: v for k, v in aggregate_cols.items() if k not in UNWANTED_COLUMNS}

    # Aggregate using the per column functions setup above
    grouped_df = unreconciled_df.fillna('').groupby(GROUP_BY).aggregate(aggregate_cols)

    grouped_df.drop(COLUMNS_WITH_BAD_DATA.keys(), axis=1, inplace=True)

    # Split the combined reconciled value and flag into separate columns
    for c in list(text_cols.keys()) + list(select_cols.keys()):
        grouped_df[c + '_explanation'], grouped_df[c] = grouped_df[c].str.split(SEPARATOR, n=1).str

    grouped_df = grouped_df.reindex_axis(sorted(grouped_df.columns), axis=1)

    # Make the sidecar explanations file -- DELETE these lines if we want one file for this
    explanations = grouped_df.loc[:, [c for c in grouped_df.columns if c.endswith('_explanation')]]
    grouped_df.drop([c for c in grouped_df.columns if c.endswith('_explanation')], axis=1, inplace=True)
    if ARGS.explanations:
        explanations.to_csv(ARGS.explanations, sep=',', encoding='utf-8')

    grouped_df.to_csv(ARGS.reconciled, sep=',', encoding='utf-8')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='''
        This takes raw Notes from Nature classifications and subjects files and creates a reconciliation
        of the classifications for a particular workflow. That is, it reduces n classifications per
        subject to the "best" values along with explanations of how these best values were determined.
    ''')
    parser.add_argument('-w', '--workflow-id', type=int, required=True,
                        help='The workflow to extract (required).')
    parser.add_argument('-c', '--input-classifications', required=True,
                        help='The Notes from Nature classifications CSV input file (required).')
    parser.add_argument('-s', '--input-subjects', required=True,
                        help='The Notes from Nature subjects CSV input file (required).')
    parser.add_argument('-r', '--reconciled',
                        help='Write the reconciled classifications to this CSV file '
                             '(default=reconciled_<workflow-id>.csv).')
    parser.add_argument('-R', '--no-reconciled', action='store_true',
                        help='Do not write either a reconciled classifications file or an explanations file and '
                        'stop further processing. This requires the "-u" option.')
    parser.add_argument('-u', '--unreconciled',
                        help='Write the unreconciled workflow classifications to this CSV file.')
    parser.add_argument('-f', '--fuzzy-ratio-threshold', default=90, type=int,
                        help='Sets the cutoff for fuzzy ratio matching (0-100, default=90). '
                             'See https://github.com/seatgeek/fuzzywuzzy.')
    parser.add_argument('-F', '--fuzzy-set-threshold', default=50, type=int,
                        help='Sets the cutoff for fuzzy set matching (0-100, default=50). '
                             'See https://github.com/seatgeek/fuzzywuzzy.')
    parser.add_argument('-e', '--explanations',
                        help='Write reconciliation explanations to this file '
                             '(default=reconciled_<workflow-id>_explanations.csv).')
    parser.add_argument('-E', '--no-explanations', action='store_true',
                        help='Do not create a reconciliation explanations file.')
    parser.add_argument('-m', '--summary',
                        help='Write a summary of the reconciliation to this file. '
                             '(default=reconciled_<workflow-id>_summary.txt).')
    parser.add_argument('-M', '--no-summary', action='store_true',
                        help='Do not write a summary file.')
    ARGS = parser.parse_args()
    if not ARGS.reconciled:
        ARGS.reconciled = 'reconciled_{}.csv'.format(ARGS.workflow_id)
    if not ARGS.explanations:
        ARGS.explanations = 'reconciled_{}_explanations.csv'.format(ARGS.workflow_id)
    if not ARGS.summary:
        ARGS.explanations = 'reconciled_{}_summary.txt'.format(ARGS.workflow_id)
    if ARGS.no_reconciled and not ARGS.unreconciled:
        print('The --no-reconciled option (-R) requires the --unreconciled (-u) option.')
        sys.exit()

    unreconciled_df = expand()
    if not ARGS.no_reconciled:
        reconcile(unreconciled_df)
