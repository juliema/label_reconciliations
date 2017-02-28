"""The main program."""

import sys
import argparse
from lib.unreconciled_builder import UnreconciledBuilder
from lib.reconciled_builder import ReconciledBuilder
from lib.summary_report import SummaryReport
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
    parser.add_argument('-t', '--top-transcribers', type=int, default=10,
                        help=('Show the top n transcribers in the summary '
                              'report. The default is 10. To turn this off '
                              'set it to zero.'))
    parser.add_argument('-f', '--fuzzy-ratio-threshold', default=90, type=int,
                        help=('Sets the cutoff for fuzzy ratio matching '
                              '(0-100, default=90). '
                              'See https://github.com/seatgeek/fuzzywuzzy.'))
    parser.add_argument('-F', '--fuzzy-set-threshold', default=50, type=int,
                        help=('Sets the cutoff for fuzzy set matching (0-100, '
                              'default=50). '
                              'See https://github.com/seatgeek/fuzzywuzzy.'))

    args = parser.parse_args()

    if args.top_transcribers < 0:
        print('--top-transcribers must be zero or more.')
        sys.exit(1)

    if args.fuzzy_ratio_threshold < 0 or args.fuzzy_ratio_threshold > 100:
        print('--fuzzy-ratio-threshold must be between 0 and 100.')
        sys.exit(1)

    if args.fuzzy_set_threshold < 0 or args.fuzzy_set_threshold > 100:
        print('--fuzzy-set-threshold must be between 0 and 100.')
        sys.exit(1)

    return args


if __name__ == "__main__":
    ARGS = parse_command_line()

    UNRECONCILED_DF = UnreconciledBuilder(ARGS.workflow_id,
                                          ARGS.classifications).build()
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
            SummaryReport(ARGS,
                          UNRECONCILED_DF,
                          RECONCILED_DF,
                          EXPLANATIONS_DF).report()
