"""The main program."""

import os
import sys
import zipfile
import argparse
import textwrap
import lib.util as util
import lib.reconciler as reconciler

VERSION = '0.3.0'


def parse_command_line():
    """Get user input."""

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""
            This takes raw Notes from Nature classifications and creates a
            reconciliation of the classifications for a particular workflow.
            That is, it reduces n classifications per subject to the "best"
            values. The summary file will provide explanations of how the
            reconciliations were done."""),
        epilog=textwrap.dedent("""
            Current reconciliation types
            ----------------------------
              select: Reconcile a fixed list of options.
              text:   Reconcile free text entry.
              same:   All items are the same. Pick an arbitrary first one.
              none:   Do not reconcile this field. This is the default."""))
    #   median:   Show the median for groups in this column.
    #   mode:     Show the mode for groups in this column.
    #   mean:     Show the mean for groups in this column.
    #   mmm:      Show the mean, median, and mode for groups.

    parser.add_argument('--input', required=True, help="""The input file.""")

    parser.add_argument('--format',
                        choices=['nfn', 'csv', 'json'], default='nfn',
                        help="""The unreconciled data is in what type of file?
                             nfn=A Zooniverse classification data dump.
                             csv=A flat CSV file. json=A JSON file. The
                             default is "nfn". When the format is "csv" or
                             "json" we require the --column-types. If the
                             type is "nfn" we can guess the --column-types
                             but the --column-types option will override our
                             guesses.""")

    parser.add_argument('--reconcilers', action='append',
                        help="""A string with information on how to reconcile
                             each column in the input file. Note: we try to
                             guess the column type when --format="nfn",
                             this will override the guesses. The format is
                             --reconcilers="foo x:select,bar:text,baz:text".
                             The list is comma separated with the column
                             label going before the colon and the
                             reconciliation type after the colon.""")

    parser.add_argument('--workflow-id', type=int,
                        help="""The workflow to extract. Required if there is
                             more than one workflow in the classifications
                             file.""")

    parser.add_argument('--unreconciled',
                        help="""Write the unreconciled workflow
                            classifications to this CSV file.""")

    parser.add_argument('--reconciled',
                        help="""Write the reconciled classifications to this
                            CSV file.""")

    parser.add_argument('--summary',
                        help="""Write a summary of the reconciliation to this
                            HTML file.""")

    parser.add_argument('--group-by', default='subject_id',
                        help="""Group the rows by this column.
                            (Default=subject_id).""")

    parser.add_argument('--sort-by', default='classification_id',
                        help="""A secondary sort column. The primary sort is
                             the --group-by (Default=classification_id).""")

    parser.add_argument('--fuzzy-ratio-threshold', default=90, type=int,
                        help="""Sets the cutoff for fuzzy ratio matching
                            (0-100, default=90).
                            See https://github.com/seatgeek/fuzzywuzzy.""")

    parser.add_argument('--fuzzy-set-threshold', default=50, type=int,
                        help="""Sets the cutoff for fuzzy set matching (0-100,
                            default=50).
                            See https://github.com/seatgeek/fuzzywuzzy.""")

    parser.add_argument('--zip',
                        help="""Zip files and put them into this archive.
                            Remove the uncompressed files afterwards.""")

    parser.add_argument('--zip-keep',
                        help="""Zip files and put them into this archive.
                            Keep the uncompressed files afterwards.""")

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


def get_column_types(args, reconcilers):
    """Append the argument column types to the inferred column types."""

    if args.reconcilers:
        for arg in args.reconcilers:
            for option in arg.split(','):
                column, reconciler = option.split(':')
                column = column.strip()
                reconciler = reconciler.strip()
        print(args.reconcilers)

    return reconcilers


def main():
    """The main function."""
    args = parse_command_line()

    formats = util.get_plugins('formats')
    unreconciled, column_types = formats[args.format].read(args)

    if unreconciled.shape[0] == 0:
        sys.exit('Workflow {} has no data.'.format(args.workflow_id))

    reconcilers = get_column_types(args, column_types)

    if args.unreconciled:
        unreconciled.to_csv(
            args.unreconciled, sep=',', encoding='utf-8', index=False)

    if args.reconciled or args.summary:
        reconciled, explanations = reconciler.build(
            args, unreconciled, reconcilers)

        if args.reconciled:
            reconciled.to_csv(
                args.reconciled, sep=',', encoding='utf-8', index=False)

    #     if args.summary:
    #         SummaryReport(args,
    #                       unreconciled,
    #                       reconciled,
    #                       explanations).report()

    if args.zip or args.zip_keep:
        zip_files(args)


if __name__ == "__main__":
    main()
