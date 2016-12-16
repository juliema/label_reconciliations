"""The main program."""

import sys
import argparse
from unreconciled_dataframe import create_unreconciled_dataframe
from reconciled_dataframes import create_reconciled_dataframes
from summary_report import create_summary_report
import utils


def parse_command_line():
    """Get user input."""
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
                        help='Do not write either a reconciled classifications file or '
                        'an explanations file and '
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
    args_out = parser.parse_args()
    if not args_out.reconciled:
        args_out.reconciled = 'reconciled_{}.csv'.format(args_out.workflow_id)
    if not args_out.explanations:
        args_out.explanations = 'reconciled_{}_explanations.csv'.format(args_out.workflow_id)
    if not args_out.summary:
        args_out.summary = 'reconciled_{}_summary.html'.format(args_out.workflow_id)
    if args_out.no_reconciled and not args_out.unreconciled:
        print('The --no-reconciled option (-R) requires the --unreconciled (-u) option.')
        sys.exit()
    args_out.explanations = '' if args_out.no_explanations else args_out.explanations
    args_out.reconciled = '' if args_out.no_reconciled else args_out.reconciled
    args_out.summary = '' if args_out.no_summary else args_out.summary
    return args_out


if __name__ == "__main__":
    ARGS = parse_command_line()

    UNRECONCILED_DF = create_unreconciled_dataframe(ARGS.workflow_id,
                                                    ARGS.input_classifications,
                                                    ARGS.input_subjects)
    if UNRECONCILED_DF.shape[0] == 0:
        print('Workflow {} has no data.'.format(ARGS.workflow_id))
        sys.exit()

    if ARGS.unreconciled:
        utils.output_dataframe(UNRECONCILED_DF, ARGS.unreconciled)

    if ARGS.no_reconciled:
        sys.exit()

    RECONCILED_DF, EXPLANATIONS_DF = create_reconciled_dataframes(UNRECONCILED_DF, ARGS)

    utils.output_dataframe(RECONCILED_DF, ARGS.reconciled)

    if ARGS.explanations:
        utils.output_dataframe(EXPLANATIONS_DF, ARGS.explanations)

    if ARGS.summary:
        create_summary_report(UNRECONCILED_DF, RECONCILED_DF, EXPLANATIONS_DF, ARGS)
