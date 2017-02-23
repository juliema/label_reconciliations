"""The main program."""

import sys
import argparse
from lib.unreconciled_dataframe import create_unreconciled_dataframe
from lib.reconciled_builder import ReconciledBuilder
from lib.summary_report import create_summary_report
import lib.util as util


def parse_command_line():
    """Get user input."""

    parser = argparse.ArgumentParser(description='''
        This takes raw Notes from Nature classifications and creates a
        reconciliation of the classifications for a particular workflow.
        That is, it reduces n classifications per subject to the "best" values.
        The summary file will provide explanations of how the reconciliations
        were done.
    ''')
    parser.add_argument('classifications',
                        help=('The Notes from Nature classifications CSV '
                              'input file.'))
    parser.add_argument('-w', '--workflow-id', type=int,
                        help=('The workflow to extract. Required if there is '
                              'more than one workflow in the classifications '
                              'file.'))
    parser.add_argument('-r', '--reconciled',
                        help=('Write the reconciled classifications to this '
                              'CSV file.'))
    parser.add_argument('-u', '--unreconciled',
                        help=('Write the unreconciled workflow '
                              'classifications to this CSV file.'))
    parser.add_argument('-s', '--summary',
                        help=('Write a summary of the reconciliation to this '
                              'HTML file.'))
    parser.add_argument('-f', '--fuzzy-ratio-threshold', default=90, type=int,
                        help=('Sets the cutoff for fuzzy ratio matching '
                              '(0-100, default=90). '
                              'See https://github.com/seatgeek/fuzzywuzzy.'))
    parser.add_argument('-F', '--fuzzy-set-threshold', default=50, type=int,
                        help=('Sets the cutoff for fuzzy set matching (0-100, '
                              'default=50). '
                              'See https://github.com/seatgeek/fuzzywuzzy.'))
    return parser.parse_args()


if __name__ == "__main__":
    ARGS = parse_command_line()

    UNRECONCILED_DF = create_unreconciled_dataframe(ARGS.workflow_id,
                                                    ARGS.classifications)
    if UNRECONCILED_DF.shape[0] == 0:
        print('Workflow {} has no data.'.format(ARGS.workflow_id))
        sys.exit(1)

    if ARGS.unreconciled:
        util.output_dataframe(UNRECONCILED_DF, ARGS.unreconciled)

    if ARGS.reconciled or ARGS.summary:
        RECONCILED_DF, EXPLANATIONS_DF = ReconciledBuilder(
            ARGS, UNRECONCILED_DF).build()

        if ARGS.reconciled:
            util.output_dataframe(RECONCILED_DF, ARGS.reconciled)

        if ARGS.summary:
            create_summary_report(UNRECONCILED_DF,
                                  RECONCILED_DF,
                                  EXPLANATIONS_DF, ARGS)
