"""The main program."""

import os
import sys
import zipfile
import argparse
import pandas as pd
import lib.nfn_format as nfn_format
import lib.util as util
# from lib.unreconciled_builder import UnreconciledBuilder
# from lib.reconciled_builder import ReconciledBuilder
# from lib.summary_report import SummaryReport
# import lib.util as util

VERSION = '0.3.0'


def parse_command_line():
    """Get user input."""

    parser = argparse.ArgumentParser(description='''
        This takes raw Notes from Nature classifications and creates a
        reconciliation of the classifications for a particular workflow.
        That is, it reduces n classifications per subject to the "best" values.
        The summary file will provide explanations of how the reconciliations
        were done.
        ''')

    parser.add_argument('-i', '--input', required=True,
                        help='The input file.')

    parser.add_argument('-f', '--format',
                        choices=['nfn', 'csv', 'json'], default='nfn',
                        help='The unreconciled data is in what type of file? '
                             'nfn=A Zooniverse classification data dump. '
                             'csv=A flat CSV file. json=A JSON file. The '
                             'default is "nfn". When the format is "csv" or '
                             '"json" we require the --column-types. If the '
                             'type is "nfn" we can guess the --column-types '
                             'but the --column-types option will override our '
                             'guesses.')

    parser.add_argument('-c', '--column-types',
                        help='A string with information on how to reconcile '
                             'each column in the input file. Note: we try to '
                             'guess the column type when --format="nfn", '
                             'this will override the guesses.')

    # parser.add_argument('-C', '--column-types-file',
    #                     help='The file containing information on how to '
    #                          'reconcile each column in the input file. '
    #                          'Note: we try to guess the column type when '
    #                          '--format=nfn')

    parser.add_argument('-w', '--workflow-id', type=int,
                        help='The workflow to extract. Required if there is '
                             'more than one workflow in the classifications '
                             'file.')

    parser.add_argument('-u', '--unreconciled',
                        help=('Write the unreconciled workflow '
                              'classifications to this CSV file.'))

    parser.add_argument('-r', '--reconciled',
                        help='Write the reconciled classifications to this '
                             'CSV file.')

    parser.add_argument('-s', '--summary',
                        help='Write a summary of the reconciliation to this '
                             'HTML file.')

    parser.add_argument('-G', '--group-by', default='subject_id',
                        help='Group the rows by this column. '
                             '(Default=subject_id).')

    parser.add_argument('-S', '--sort-by', default='classification_id',
                        help='A secondary sort column. The primary sort is '
                             'the --group-by (Default=classification_id).')

    parser.add_argument('--fuzzy-ratio-threshold', default=90, type=int,
                        help='Sets the cutoff for fuzzy ratio matching '
                             '(0-100, default=90). '
                             'See https://github.com/seatgeek/fuzzywuzzy.')

    parser.add_argument('--fuzzy-set-threshold', default=50, type=int,
                        help='Sets the cutoff for fuzzy set matching (0-100, '
                             'default=50). '
                             'See https://github.com/seatgeek/fuzzywuzzy.')

    parser.add_argument('-z', '--zip',
                        help='Zip files and put them into this archive. '
                             'Remove the uncompressed files afterwards.')

    parser.add_argument('-Z', '--zip-keep',
                        help='Zip files and put them into this archive. '
                             'Keep the uncompressed files afterwards.')

    parser.add_argument('-V', '--version', action='version',
                        version='%(prog)s {}'.format(VERSION))

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


def unreconciled_setup(args, unreconciled):
    """Simple processing of the unreconciled dataframe. This is not used
    when there is a large amount of processing of the input."""

    unreconciled = pd.read_csv(args.input)

    # Workflows must be processed individually
    workflow_id = util.get_workflow_id(unreconciled, args)

    # Remove anything not in the workflow
    unreconciled = unreconciled.loc[unreconciled.workflow_id == workflow_id, :]
    unreconciled = unreconciled.fillna('')

    unreconciled.sort_values([args.group_by, args.sort_by], inplace=True)

    return unreconciled


if __name__ == "__main__":
    ARGS = parse_command_line()

    TYPES = {}  # Column types

    if ARGS.format == 'nfn':
        UNRECONCILED, TYPES = nfn_format.read(ARGS)
    elif ARGS.format == 'csv':
        UNRECONCILED = pd.read_csv(ARGS.input)
        UNRECONCILED = unreconciled_setup(ARGS, UNRECONCILED)
    elif ARGS.format == 'json':
        UNRECONCILED = pd.read_json(ARGS.input)
        UNRECONCILED = unreconciled_setup(ARGS, UNRECONCILED)

    if UNRECONCILED.shape[0] == 0:
        sys.exit('Workflow {} has no data.'.format(ARGS.workflow_id))

    if ARGS.unreconciled:
        UNRECONCILED.to_csv(
            ARGS.unreconciled, sep=',', encoding='utf-8', index=False)

    # if ARGS.reconciled or ARGS.summary:
    #     RECONCILED_DF, EXPLANATIONS_DF = ReconciledBuilder(
    #         ARGS, UNRECONCILED).build()
    #
    #     if ARGS.reconciled:
    #         output_dataframe(RECONCILED_DF, ARGS.reconciled)
    #
    #     if ARGS.summary:
    #         SummaryReport(ARGS,
    #                       UNRECONCILED,
    #                       RECONCILED_DF,
    #                       EXPLANATIONS_DF).report()
    #
    # if ARGS.zip or ARGS.zip_keep:
    #     zip_files(ARGS)
