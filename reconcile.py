"""The main program."""

import os
import sys
# import zlib
import zipfile
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

    parser.add_argument('-f', '--fuzzy-ratio-threshold', default=90, type=int,
                        help=('Sets the cutoff for fuzzy ratio matching '
                              '(0-100, default=90). '
                              'See https://github.com/seatgeek/fuzzywuzzy.'))

    parser.add_argument('-F', '--fuzzy-set-threshold', default=50, type=int,
                        help=('Sets the cutoff for fuzzy set matching (0-100, '
                              'default=50). '
                              'See https://github.com/seatgeek/fuzzywuzzy.'))

    parser.add_argument('-z', '--zip',
                        help='Zip files and put them into this archive. '
                             'Remove the uncompressed files afterwards.')

    parser.add_argument('-Z', '--zip-keep',
                        help='Zip files and put them into this archive. '
                             'Keep the uncompressed files afterwards.')

    args = parser.parse_args()

    if args.fuzzy_ratio_threshold < 0 or args.fuzzy_ratio_threshold > 100:
        print('--fuzzy-ratio-threshold must be between 0 and 100.')
        sys.exit(1)

    if args.fuzzy_set_threshold < 0 or args.fuzzy_set_threshold > 100:
        print('--fuzzy-set-threshold must be between 0 and 100.')
        sys.exit(1)

    return args


def zip_files(args):
    """Put results into a zip file."""

    zip_file = args.zip if args.zip else args.zip_keep

    with zipfile.ZipFile(zip_file, mode='w') as zippy:
        if args.unreconciled:
            zippy.write(args.unreconciled, compress_type=zipfile.ZIP_DEFLATED)
        if args.reconciled:
            zippy.write(args.reconciled, compress_type=zipfile.ZIP_DEFLATED)
        if args.summary:
            zippy.write(args.summary, compress_type=zipfile.ZIP_DEFLATED)

    if args.zip_keep:
        return

    if args.unreconciled:
        os.remove(args.unreconciled)
    if args.reconciled:
        os.remove(args.reconciled)
    if args.summary:
        os.remove(args.summary)


if __name__ == "__main__":
    ARGS = parse_command_line()

    UNRECONCILED_DF = UnreconciledBuilder(ARGS.workflow_id,
                                          ARGS.classifications).build()
    if UNRECONCILED_DF.shape[0] == 0:
        print('Workflow {} has no data.'.format(ARGS.workflow_id))
        sys.exit(1)

    if ARGS.unreconciled:
        util.output_dataframe(UNRECONCILED_DF, ARGS.unreconciled, index=False)

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

    if ARGS.zip or ARGS.zip_keep:
        zip_files(ARGS)
