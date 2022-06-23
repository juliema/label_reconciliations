#!/usr/bin/env python3
import argparse
import os
import sys
import textwrap
import zipfile
from os.path import basename

from pylib import summary_html
from pylib import utils
from pylib.table import Table


VERSION = "0.5.0"


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
            mean:   Calculate the mean of each group.
            box:    Reconcile drawn bounding boxes, the mean of the corners.
            point:  Calculate the mean of a point.
            length: Calculate the length of a drawn line. It first calculates the
                    mean of the end points and then uses a scale to get the
                    calibrated length relative to the scale."""
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
        "-z",
        "--zip",
        help="""Zip the output files and put them into this archive.""",
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
        "-V", "--version", action="version", version=f"%(prog)s {VERSION}"
    )

    args = parser.parse_args()

    setattr(args, "group_by", "subject_id")
    setattr(args, "row_key", "classification_id")
    setattr(args, "user_column", "user_name")
    setattr(args, "page_size", 20)

    if args.fuzzy_ratio_threshold < 0 or args.fuzzy_ratio_threshold > 100:
        print("--fuzzy-ratio-threshold must be between 0 and 100.")
        sys.exit(1)

    if args.fuzzy_set_threshold < 0 or args.fuzzy_set_threshold > 100:
        print("--fuzzy-set-threshold must be between 0 and 100.")
        sys.exit(1)

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
    unreconciled: Table = formats["nfn"].read(args)

    if not unreconciled.has_rows:
        sys.exit(f"Workflow {args.workflow_id} has no data.")

    if args.unreconciled:
        unreconciled.to_csv(args.unreconciled)

    if args.reconciled or args.summary:
        reconciled = Table.reconcile(unreconciled, args)

        if args.reconciled:
            reconciled.to_csv(args.reconciled)

        if args.summary:
            summary_html.report(args, unreconciled, reconciled)

    if args.zip:
        zip_files(args)


if __name__ == "__main__":
    main()
