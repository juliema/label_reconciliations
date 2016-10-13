import re
import sys
import json
import argparse
import dateutil
import pandas as pd
import xml.etree.ElementTree as et
from functools import reduce
from collections import Counter, namedtuple
from itertools import combinations
from fuzzywuzzy import fuzz


PLACE_HOLDERS = ['placeholder']  # Replace these placeholders with an empty string
NO_MATCHES = '<NO MATCHES>'      # A flag for unmatched data
GROUP_BY = 'subject_id'          # We group on this column
SEPARATOR = ':'                  # Used to separate match flags from values


class match_types:
    all_blank = '<All are blank>'
    one_transcript = '<Only one transcript>'

    exact = 'Exact match'
    select_no_match = '<No match on select>'

    normalized_exact = 'Normalized exact match'
    partial_ratio = 'Partial ratio match'
    token_set_ratio = 'Token set ratio match'
    text_no_match = '<No match on text>'

# Useful for naming tuple items, rather than using indexes into tuples
ExactScore = namedtuple('ExactScore', 'value count')
FuzzyRatioScore = namedtuple('FuzzyRatioScore', 'score value')
FuzzySetScore = namedtuple('FuzzySetScore', 'score value tokens')

UNWANTED_COLUMNS = ['subject_data', 'subject_retired', 'subject_subjectId']
# COLUMNS_WITH_BAD_DATA = {}  # Subject_* columns with non-identical values in a group
ARGS = None


def extract_json_value(subject_json, column=''):
    if column in list(subject_json.values())[0]:
        return list(subject_json.values())[0][column]


def extract_json_date(metadata_json, column=''):
    return dateutil.parser.parse(metadata_json[column]).strftime('%d-%b-%Y %H:%M:%S')


def header_label(task_id, label, task_type):
    return '{}{:0>3}{}: {}'.format(task_id[0], task_id[1:], task_type, label)


def extract_an_annotaion(unreconciled_df, task, task_id, index):
    if isinstance(task.get('value'), list):
        for subtask in task['value']:
            subtask_id = subtask.get('task', task_id)
            extract_an_annotaion(unreconciled_df, subtask, subtask_id, index)
    elif task.get('select_label'):
        header = header_label(task_id, task['select_label'], 's')
        value = task.get('label')
        unreconciled_df.loc[index, header] = value
    elif task.get('task_label'):
        header = header_label(task_id, task['task_label'], 't')
        value = task.get('value')
        unreconciled_df.loc[index, header] = value
    else:
        print('Error: Could not parse the annotations.')
        sys.exit()


def extract_annotations_json(unreconciled_df):
    unreconciled_df['annotation_json'] = unreconciled_df['annotations'].map(lambda x: json.loads(x))
    for index, row in unreconciled_df.iterrows():
        for task in row['annotation_json']:
            task_id = task['task']
            extract_an_annotaion(unreconciled_df, task, task_id, index)
    unreconciled_df.drop('annotation_json', axis=1, inplace=True)


def extract_subject_json(unreconciled_df):
    unreconciled_df['subject_json'] = unreconciled_df['subject_data'].map(lambda x: json.loads(x))
    subject_keys = {}
    for subj in unreconciled_df['subject_json']:
        for val in iter(subj.values()):
            for k in val.keys():
                subject_keys[k] = 1
    for k in subject_keys.keys():
        unreconciled_df['subject_' + k] = unreconciled_df['subject_json'].apply(extract_json_value, column=k)
    unreconciled_df.drop('subject_json', axis=1, inplace=True)


def extract_metata_json(unreconciled_df):
    unreconciled_df['metadata_json'] = unreconciled_df['metadata'].map(lambda x: json.loads(x))
    unreconciled_df['classification_started_at'] = unreconciled_df['metadata_json'].apply(extract_json_date, column='started_at')
    unreconciled_df['classification_finished_at'] = unreconciled_df['metadata_json'].apply(extract_json_date, column='finished_at')
    unreconciled_df.drop('metadata_json', axis=1, inplace=True)


def expand(workflow_id, input_classifications, input_subjects):
    subjects_df = pd.read_csv(input_subjects)
    unreconciled_df = pd.read_csv(input_classifications)

    # We need to do this by workflow because each one's annotations have a different structure
    unreconciled_df = unreconciled_df.loc[unreconciled_df.workflow_id == workflow_id, :]

    # bring the last column to be the first
    cols = unreconciled_df.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    unreconciled_df = unreconciled_df[cols]

    # Make key data types match in the two data frames
    unreconciled_df['subject_ids'] = unreconciled_df.subject_ids.map(lambda x: int(str(x).split(';')[0]))

    # Get subject info we need from the subjects_df
    unreconciled_df = pd.merge(unreconciled_df, subjects_df[['subject_id', 'locations']], how='left',
                               left_on='subject_ids', right_on='subject_id')

    extract_metata_json(unreconciled_df)
    extract_annotations_json(unreconciled_df)
    extract_subject_json(unreconciled_df)

    unreconciled_df.drop(['user_id', 'user_ip', 'subject_id'], axis=1, inplace=True)
    unreconciled_df.rename(columns={'subject_ids': 'subject_id'}, inplace=True)
    unreconciled_df.sort_values(['subject_id', 'classification_id'], inplace=True)

    return unreconciled_df


def normalize_text(group):
    return ['\n'.join([' '.join(ln.split()) for ln in g.splitlines()]) for g in group]


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
    # counts = Counter(values)
    # Remove columns where we expect identical values but do not get them
    # if len(counts) > 1:
    #     COLUMNS_WITH_BAD_DATA[group.name] = 1
    #     return ''
    return values[0]


def output(match_type, value, values=None, filled=None, score=None):
    if match_type in [match_types.exact, match_types.normalized_exact]:
        total = len(values)
        blanks = total - reduce((lambda x, y: x + y.count), filled, 0)
        word = 'blank' if blanks == 1 else 'blanks'
        return '{} {}/{} with {} {}{}{}'.format(match_type, filled[0].count, total, blanks, word, SEPARATOR, value)
    elif match_type in [match_types.select_no_match, match_types.text_no_match]:
        total = len(values)
        blanks = total - reduce((lambda x, y: x + y.count), filled, 0)
        return '{} {}/{} with {} blanks{}{}'.format(match_type, 0, total, blanks, SEPARATOR, value)
    elif match_type in [match_types.all_blank]:
        total = len(values)
        return '{} {}/{}{}{}'.format(match_type, total, total, SEPARATOR, value)
    elif match_type in [match_types.one_transcript]:
        total = len(values)
        return '{} {}/{}{}{}'.format(match_type, 1, total, SEPARATOR, value)
    elif match_type in [match_types.partial_ratio, match_types.token_set_ratio]:
        return '{} score={}{}{}'.format(match_type, score, SEPARATOR, value)
    print('Error unknown match type.')
    sys.exit()


def reconcile_select(group):
    values = [str(g) if str(g).lower() not in PLACE_HOLDERS else '' for g in group]
    filled = [ExactScore(c[0], c[1]) for c in Counter([v for v in values if v]).most_common()]

    if not filled:
        return output(match_types.all_blank, '', values=values, filled=filled)

    if filled[0].count > 1:
        return output(match_types.exact, filled[0].value, values=values, filled=filled)

    if len(filled) == 1:
        return output(match_types.one_transcript, filled[0].value, values=values, filled=filled)

    return output(match_types.select_no_match, NO_MATCHES, values=values, filled=filled)


def reconcile_text(group):
    global ARGS

    values = normalize_text(group)
    filled = [ExactScore(c[0], c[1]) for c in Counter([v for v in values if v]).most_common()]

    if not filled:
        return output(match_types.all_blank, '', values=values, filled=filled)

    if filled[0].count > 1:
        return output(match_types.normalized_exact, filled[0].value, values=values, filled=filled)

    if len(filled) == 1:
        return output(match_types.one_transcript, filled[0].value, values=values, filled=filled)

    # Check for simple inplace fuzzy matches
    top = top_partial_ratio(group)
    if top.score >= ARGS.fuzzy_ratio_threshold:
        return output(match_types.partial_ratio, top.value, score=top.score)

    # Now look for the best token match
    top = top_token_set_ratio(group)
    if top.score >= ARGS.fuzzy_set_threshold:
        return output(match_types.token_set_ratio, top.value, score=top.score)

    return output(match_types.text_no_match, NO_MATCHES, values=values, filled=filled)


def reconcile(unreconciled_df):
    # How to aggregate the columns based on each column's type which is determined by the column name
    select_cols = {c: reconcile_select for c in unreconciled_df.columns if re.match(r'T\d+s:', c)}
    text_cols = {c: reconcile_text for c in unreconciled_df.columns if re.match(r'T\d+t:', c)}
    subject_cols = {c: reconcile_same for c in unreconciled_df.columns if c.startswith('subject_') and c != GROUP_BY}
    aggregate_cols = dict(list(select_cols.items()) + list(text_cols.items()) + list(subject_cols.items()))
    aggregate_cols['locations'] = reconcile_same  # We want this column that is not in any of the above categories
    aggregate_cols = {k: v for k, v in aggregate_cols.items() if k not in UNWANTED_COLUMNS}

    # Aggregate using the per column functions setup above
    reconciled_df = unreconciled_df.fillna('').groupby(GROUP_BY).aggregate(aggregate_cols)

    # reconciled_df.drop(COLUMNS_WITH_BAD_DATA.keys(), axis=1, inplace=True)

    # Split the combined reconciled value and flag into separate columns
    for c in list(text_cols.keys()) + list(select_cols.keys()):
        reconciled_df[c + '_explanation'], reconciled_df[c] = reconciled_df[c].str.split(SEPARATOR, n=1).str

    reconciled_df = reconciled_df.reindex_axis(sorted(reconciled_df.columns), axis=1)

    explanations_df = reconciled_df.loc[:, [c for c in reconciled_df.columns if c.endswith('_explanation')]]
    explanations_cols = {c: c.replace('_explanation', '') for c in explanations_df.columns}
    explanations_df.rename(columns=explanations_cols, inplace=True)

    reconciled_df.drop([c for c in reconciled_df.columns if c.endswith('_explanation')], axis=1, inplace=True)

    return reconciled_df, explanations_df


def format_name(name):
    return re.sub(r'^T\d+[st]:\s*', '', name)


def output_dataframe(df, file_name):
    columns = {c: format_name(c) for c in df.columns}
    new_df = df.rename(columns=columns)
    new_df.to_csv(file_name, sep=',', encoding='utf-8')


def summary(unreconciled_df, reconciled_df, explanations_df):
    html = et.fromstring('''
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title />
    <style>
      .hide { display: none; }
    </style>
  </head>
  <body>
    <header>
      <h1 id="title" />
      <div><label>Number of Subjects:</label><span id="subjects" /></div>
      <div><label>Number of Transcripts:</label><span id="transcripts" /></div>
      <div><label>Transcripts per Subject:</label><span id="ratio" /></div>
    </header>
    <section id="stats">
      <h2>Reconciled Data</h2>
      <table>
        <thead>
          <tr>
            <th>Field</th>
            <th>Number Reconciled</th>
            <th>Number with One Transcript</th>
            <th>Number of All Blanks</th>
          </tr>
        </thead>
        <tbody />
      </table>
    </section>
    <section id="problems">
      <h2>Problem Records</h2>
      <table>
        <thead>
          <tr>
            <th>Subject ID</th>
            <th>Field</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody />
      </table>
    </section>
    <footer>
      <div id="date" />
    </footer>
  </body>
</html>
    ''')
    workflow_name = unreconciled_df.loc[0, 'workflow_name'] if 'workflow_name' in unreconciled_df.columns else ''
    workflow_name = re.sub(r'^[^_]*_', '', workflow_name)

    html.find('.head/title').text = 'Summary of {}'.format(ARGS.workflow_id)

    html.find(".//h1[@id='title']").text = 'Summary of "{}" ({})'.format(workflow_name, ARGS.workflow_id)
    html.find(".//span[@id='subjects']").text = '{:,}'.format(reconciled_df.shape[0])
    html.find(".//span[@id='transcripts']").text = '{:,}'.format(unreconciled_df.shape[0])
    html.find(".//span[@id='ratio']").text = '{:.2f}'.format(unreconciled_df.shape[0] / reconciled_df.shape[0])

    tbody = html.find(".//section[@id='stats']/table/tbody")
    for col in [c for c in reconciled_df.columns if re.match(r'T\d+[st]:', c)]:
        tr = et.Element('tr')
        td = et.Element('td')
        td.text = format_name(col)
        tr.append(td)
        td = et.Element('td')
        td.text = '0'
        tr.append(td)
        td = et.Element('td')
        td.text = '0'
        tr.append(td)
        td = et.Element('td')
        td.text = '0'
        tr.append(td)
        tbody.append(tr)

    with open(ARGS.summary, 'wb') as out_file:
        out_file.write('<!DOCTYPE html>\n'.encode())
        out_file.write(et.tostring(html))


def parse_command_line():
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
                             '(default=reconciled_<workflow-id>_summary.html).')
    parser.add_argument('-M', '--no-summary', action='store_true',
                        help='Do not write a summary file.')
    args = parser.parse_args()
    if not args.reconciled:
        args.reconciled = 'reconciled_{}.csv'.format(args.workflow_id)
    if not args.explanations:
        args.explanations = 'reconciled_{}_explanations.csv'.format(args.workflow_id)
    if not args.summary:
        args.summary = 'reconciled_{}_summary.html'.format(args.workflow_id)
    if args.no_reconciled and not args.unreconciled:
        print('The --no-reconciled option (-R) requires the --unreconciled (-u) option.')
        sys.exit()
    args.explanations = '' if args.no_explanations else args.explanations
    args.reconciled = '' if args.no_reconciled else args.reconciled
    args.summary = '' if args.no_summary else args.summary
    return args


if __name__ == "__main__":
    ARGS = parse_command_line()

    unreconciled_df = expand(ARGS.workflow_id, ARGS.input_classifications, ARGS.input_subjects)

    if ARGS.unreconciled:
        output_dataframe(unreconciled_df, ARGS.unreconciled)

    if ARGS.no_reconciled:
        sys.exit()

    reconciled_df, explanations_df = reconcile(unreconciled_df)

    output_dataframe(reconciled_df, ARGS.reconciled)

    if ARGS.explanations:
        output_dataframe(explanations_df, ARGS.explanations)

    if ARGS.summary:
        summary(unreconciled_df, reconciled_df, explanations_df)
