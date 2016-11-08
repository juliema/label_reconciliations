#!/usr/bin/python3

import sys
import argparse
from unreconciled_dataframe import create_unreconciled_dataframe
from reconciled_dataframes import create_reconciled_dataframes
from summary_report import create_summary_report
import utils


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
    args = parse_command_line()

    unreconciled_df = create_unreconciled_dataframe(args.workflow_id, args.input_classifications, args.input_subjects)

    if args.unreconciled:
        utils.output_dataframe(unreconciled_df, args.unreconciled)

    if args.no_reconciled:
        sys.exit()

    reconciled_df, explanations_df = create_reconciled_dataframes(unreconciled_df, args)

    utils.output_dataframe(reconciled_df, args.reconciled)

    if args.explanations:
        utils.output_dataframe(explanations_df, args.explanations)

    if args.summary:
        create_summary_report(unreconciled_df, reconciled_df, explanations_df, args)
