"""Render a summary of the reconciliation process."""

import re
from datetime import datetime
from urllib.parse import urlparse

from jinja2 import Environment, PackageLoader

import lib.util as util

# These depend on the patterns put into explanations
NO_MATCH_PATTERN = r'No (?:select|text) match on'

MAJORITY_MATCH_PATTERN = (
    '^(?:Majority|Normalized majority|Exact) match'
    '|^(?:Exact|Normalized) match is a tie'
    '|^Match is a tie,'
    '|^Match,')

UNANIMOUS_MATCH_PATTERN = (
    r'^(?:Unanimous|Normalized unanimous|Exact unanimous) match')

FUZZ_MATCH_PATTERN = r'^(?:Partial|Token set) ratio match'

ALL_BLANK_PATTERN = (
    r'^(?:(?:All|The) \d+ record|^There (?:was|were) no numbers? in)')

ONESIES_PATTERN = r'Only 1 transcript in|There was 1 number in'

MMR_PATTERN = r'^There (?:was|were) (?:\d+) numbers? in'

# Combine for the problem pattern
PROBLEM_PATTERN = '|'.join([NO_MATCH_PATTERN, ONESIES_PATTERN])


def report(args, unreconciled, reconciled, explanations, column_types):
    """Generate the report."""
    # Everything as strings
    reconciled = reconciled.applymap(str)
    unreconciled = unreconciled.applymap(str)

    # Convert links into anchor elements
    reconciled = reconciled.applymap(create_link)
    unreconciled = unreconciled.applymap(create_link)

    # Get the report template
    env = Environment(loader=PackageLoader('reconcile', '.'))
    template = env.get_template('lib/summary/template.html')

    # Create the group dataset
    groups = get_groups(args, unreconciled, reconciled, explanations)

    # Create filter lists
    filters = get_filters(args, groups, column_types)

    # Get transcriber summary data
    transcribers = user_summary(args, unreconciled)

    # Build the summary report
    summary = template.render(
        args=vars(args),
        header=header_data(args, unreconciled, reconciled, transcribers),
        groups=iter(groups.items()),
        filters=filters,
        columns=util.sort_columns(args, unreconciled, column_types),
        transcribers=transcribers,
        reconciled=reconciled_summary(explanations, column_types),
        problem_pattern=PROBLEM_PATTERN)

    # Output the report
    with open(args.summary, 'w', encoding='utf-8') as out_file:
        out_file.write(summary)


def get_groups(args, unreconciled, reconciled, explanations):
    """Convert the data frames into dictionaries."""
    groups = {}

    # Put reconciled data into the dictionary
    for key, row in reconciled.iterrows():
        groups[str(key)] = {'reconciled': row.to_dict()}

    # Put explanations data into the dictionary
    for key, row in explanations.iterrows():
        groups[str(key)]['explanations'] = row.to_dict()

    # Put unreconciled data into the dictionary
    for _, row in unreconciled.iterrows():
        key = str(row[args.group_by])
        array = groups[key].get('unreconciled', [])
        array.append(row.to_dict())
        groups[key]['unreconciled'] = array

    return groups


def get_filters(args, groups, column_types):
    """Create list of group IDs that will be used to filter group rows."""
    filters = {
        '__select__': ['Show All', 'Show All Problems'],
        'Show All': groups.keys(),
        'Show All Problems': []}

    # Get the remaining filters. They are the columns in the explanations row.
    group = next(iter(groups.values()))
    columns = util.sort_columns(
        args, group['explanations'].keys(), column_types)
    filters['__select__'] += ['Show problems with: ' + c
                              for c in columns
                              if c in group['explanations'].keys()]
    # Initialize the filters
    for name in filters['__select__'][2:]:
        filters[name] = []

    # Get the problems for each group
    all_problems = {}
    for group_by, group in groups.items():
        for column, value in group['explanations'].items():
            if re.search(PROBLEM_PATTERN, value):
                key = 'Show problems with: ' + column
                all_problems[group_by] = 1
                filters[key].append(group_by)

    # Sort by the grouping column
    filters['Show All Problems'] = all_problems.keys()
    for name in filters['__select__']:
        filters[name] = sorted(filters[name])

    return filters


def create_link(value):
    """Convert a link into an anchor element."""
    try:
        url = urlparse(value)
        if url.scheme and url.netloc and url.path:
            return '<a href="{value}" target="_blank">{value}</a>'.format(
                value=value)
    except (ValueError, AttributeError):
        pass
    return value


def user_summary(args, unreconciled):
    """Get a list of users and how many transcriptions they did."""
    # TODO: Delete this

    if not args.user_column:
        return {}

    series = unreconciled.groupby(args.user_column)
    series = series[args.user_column].count()
    series = series.sort_values(ascending=False)
    transcribers = [{'name': name, 'count': count}
                    for name, count in series.iteritems()]
    return transcribers


def header_data(args, unreconciled, reconciled, transcribers):
    """Get data that goes into the report header."""
    # TODO: Delete this

    return {
        'date': datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M'),
        'title': args.title if args.title else args.input_file,
        'ratio': unreconciled.shape[0] / reconciled.shape[0],
        'subjects': reconciled.shape[0],
        'transcripts': unreconciled.shape[0],
        'transcribers': len(transcribers)}


def reconciled_summary(explanations, column_types):
    """Build a summary of how each field was reconciled."""
    # TODO: Delete this

    how_reconciled = []
    for col in order_column_names(explanations, column_types):

        col_type = column_types.get(col, {'type': 'text'})['type']

        num_fuzzy_match = ''
        if col_type == 'text':
            num_fuzzy_match = '{:,}'.format(explanations[
                                                explanations[col].str.contains(
                                                    FUZZ_MATCH_PATTERN)].shape[
                                                0])

        num_no_match = explanations[
            explanations[col].str.contains(NO_MATCH_PATTERN)].shape[0]

        num_onesies = explanations[
            explanations[col].str.contains(ONESIES_PATTERN)].shape[0]

        num_mmr = ''
        if col_type in ('mmr', 'mean'):
            num_mmr = '{:,}'.format(explanations[
                                        explanations[col].str.contains(
                                            MMR_PATTERN)].shape[0]
                                    - num_onesies)

        how_reconciled.append({
            'name': col,
            'col_type': col_type,
            'num_no_match': num_no_match,
            'num_fuzzy_match': num_fuzzy_match,
            'num_reconciled': explanations.shape[0] - num_no_match,
            'num_majority_match': explanations[
                explanations[col].str.contains(
                    MAJORITY_MATCH_PATTERN)].shape[0],
            'num_unanimous_match': explanations[
                explanations[col].str.contains(
                    UNANIMOUS_MATCH_PATTERN)].shape[0],
            'num_all_blank': explanations[
                explanations[col].str.contains(ALL_BLANK_PATTERN)].shape[0],
            'num_onesies': num_onesies,
            'num_mmr': num_mmr})
    return how_reconciled


def order_column_names(df, column_types):
    """Sort column names by the column order."""
    # TODO: Delete this

    columns = [v['name'] for v
               in sorted(column_types.values(), key=lambda x: x['order'])
               if v['name'] in df.columns]
    return columns


def problems(explanations, column_types):
    """Make a list of problems for each subject."""
    # TODO: Delete this

    probs = {}
    opts = None

    for group_by, cols in explanations.iterrows():

        # Get the list of possible problems
        if not opts:
            opts = [('problem-{}'.format(i), k) for i, (k, v)
                    in enumerate(cols.iteritems(), 1)]
            opts = sorted(opts, key=lambda x: column_types[x[1]]['order'])

        # get the row's problems
        probs[group_by] = {}
        for i, (col, value) in enumerate(cols.iteritems(), 1):
            if re.search(PROBLEM_PATTERN, value):
                probs[group_by][col] = 'problem-{}'.format(i)

    return probs, opts
