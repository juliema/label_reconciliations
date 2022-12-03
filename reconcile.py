#!/usr/bin/env python3
import argparse
import os
import textwrap
import warnings
import zipfile
from os.path import basename

from pylib import summary
from pylib import utils
from pylib.table import Table


VERSION = "0.5.7"


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        fromfile_prefix_chars="@",
        description=textwrap.dedent(
            """
            This takes raw Notes from Nature classifications and creates a
            reconciliation of the classifications for a particular workflow.
            That is, it reduces n classifications per subject to the "best"
            values."""
        ),
        epilog=textwrap.dedent(
            """
            Current reconciliation types
            ----------------------------
            select: Reconcile a fixed list of options.
            text:   Reconcile free text entries.
            same:   Check that all items in a group are the same.
            box:    Reconcile drawn bounding boxes, the mean of the corners.
                    Required box format:
                    {"x": <int>, "y": <int>, "width": <int>, "height": <int>}
            point:  Calculate the mean of a point. Required point format:
                    {"x": <int>, "y": <int>}
            noop:   Do nothing with this field.
            length: Calculate the length of a drawn line. It first calculates the
                    mean of the end points and then uses a scale to get the
                    calibrated length relative to the scale. Required length format:
                    {"x1": <int>, "y1": <int>, "x2": <int>, "y2": <int>}
                    To get actual lengths (vs. pixel) you will need a scale length
                    header with a number and column with units. Ex: "scale 0.5 mm".
            """
        ),
    )

    parser.add_argument("input_file", metavar="INPUT-FILE", help="""The input file.""")

    parser.add_argument(
        "-u",
        "--unreconciled",
        help="""Write the unreconciled workflow classifications to this CSV file.""",
    )

    parser.add_argument(
        "-r",
        "--reconciled",
        help="""Write the reconciled classifications to this CSV file.""",
    )

    parser.add_argument(
        "-s",
        "--summary",
        help="""Write a summary of the reconciliation to this HTML file.""",
    )

    parser.add_argument(
        "-e",
        "--explanations",
        action="store_true",
        help="""Output the reconciled explanations with the reconciled classifications
            CSV file.""",
    )

    parser.add_argument(
        "-z",
        "--zip",
        help="""Zip the output files and put them into this archive.""",
    )

    parser.add_argument(
        "-n",
        "--workflow-name",
        help="""The name of the workflow. NfN extracts can find a default.""",
    )

    parser.add_argument(
        "-w",
        "--workflow-id",
        type=int,
        help="""The workflow to extract. Required if there is more than one workflow in
            the classifications file. This is only used for nfn formats.""",
    )

    parser.add_argument(
        "--fuzzy-ratio-threshold",
        default=90,
        type=int,
        help="""Sets the cutoff for fuzzy ratio matching (0-100) (default: %(default)s)
            See https://github.com/seatgeek/fuzzywuzzy.""",
    )

    parser.add_argument(
        "--fuzzy-set-threshold",
        default=50,
        type=int,
        help="""Sets the cutoff for fuzzy set matching (0-100) (default: %(default)s).
            See https://github.com/seatgeek/fuzzywuzzy.""",
    )

    parser.add_argument(
        "--workflow-csv",
        default="",
        metavar="CSV",
        help="""Sometimes we need to translate a value from its numeric code to a
            human-readable string. The workflow file will contain these translations.
            """,
    )

    parser.add_argument(
        "-f",
        "--format",
        choices=["nfn", "csv", "json"],
        default="nfn",
        help="""The unreconciled data is in what type of file? nfn=A Zooniverse
            classification data dump. csv=A flat CSV file. json=A JSON file. When the
            format is "csv" or "json" we require the --column-types. If the type is
            "nfn" we can guess the --column-types but the --column-types option will
            still override our guesses. (default: %(default)s)""",
    )

    parser.add_argument(
        "-c",
        "--column-types",
        action="append",
        help="""We need do identify what the column types are for CSV or JSON files.
            This is a string with information on how to reconcile each column in the
            input file. The format is --column-types "foo:select,bar:text,baz:text".
            The list is comma separated with the column label going before the colon
            and the reconciliation type after the colon. You may want to use this
            argument multiple times. The default field type is a NoOp (Do nothing).""",
    )
    parser.add_argument(
        "--group-by",
        default="subject_id",
        help="""Group CSV & JSON the rows by this column (Default=subject_id).""",
    )

    parser.add_argument(
        "--page-size",
        default=20,
        type=int,
        help="""Page size for the summary report's detail section.
            (default: %(default)s)""",
    )

    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {VERSION}"
    )

    args = parser.parse_args()

    setattr(args, "row_key", "classification_id")
    setattr(args, "user_column", "user_name")

    if args.fuzzy_ratio_threshold < 0 or args.fuzzy_ratio_threshold > 100:
        utils.error_exit("--fuzzy-ratio-threshold must be between 0 and 100.")

    if args.fuzzy_set_threshold < 0 or args.fuzzy_set_threshold > 100:
        utils.error_exit("--fuzzy-set-threshold must be between 0 and 100.")

    if args.format == "nfn" and args.column_types:
        warnings.warn("Column types are ignored for 'nfn' format.")
        return

    return args


def zip_files(args):
    zip_file = args.zip if args.zip else args.zip_keep

    args_dict = vars(args)
    arg_files = ["unreconciled", "reconciled", "summary"]

    with zipfile.ZipFile(zip_file, mode="w") as zippy:
        for arg_file in arg_files:
            if args_dict[arg_file]:
                zippy.write(
                    args_dict[arg_file],
                    arcname=basename(args_dict[arg_file]),
                    compress_type=zipfile.ZIP_DEFLATED,
                )

    for arg_file in arg_files:
        if args_dict[arg_file]:
            os.remove(args_dict[arg_file])


def main():
    args = parse_args()

    formats = utils.get_plugins("formats")
    unreconciled: Table = formats[args.format].read(args)

    if not unreconciled.has_rows:
        utils.error_exit(f"Workflow {args.workflow_id} has no data.")

    if args.unreconciled:
        unreconciled.to_csv(args, args.unreconciled)

    if args.reconciled or args.summary:
        reconciled = Table.reconcile(unreconciled, args)

        if args.reconciled:
            reconciled.to_csv(args, args.reconciled, unreconciled)

        if args.summary:
            summary.report(args, unreconciled, reconciled)

    if args.zip:
        zip_files(args)


if __name__ == "__main__":
    main()
