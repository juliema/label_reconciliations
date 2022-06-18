#!/usr/bin/env python3
import argparse
import os
import sys
import textwrap
import zipfile
from os.path import basename

from lib import reconciled as reconciled_df
from lib import reconciler
from lib import summary
from lib import util

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
            values. The summary file will provide explanations of how the
            reconciliations were done. NOTE: You may use a file to hold the
            command-line arguments like: @path/to/args.txt."""
        ),
        epilog=textwrap.dedent(
            """
            Current reconciliation types
            ----------------------------
              select: Reconcile a fixed list of options.
              text:   Reconcile free text entries.
              same:   Check that all items in a group are the same.
              mean:   Show the mean and range for each group.
            * Note:   If a column is not listed it will not be reconciled."""
        ),
    )

    parser.add_argument("input_file", metavar="INPUT-FILE", help="""The input file.""")

    parser.add_argument(
        "-c",
        "--column-types",
        action="append",
        help="""A string with information on how to reconcile each column in the input
            file. The format is --column-types "foo foo:select,bar:text,baz:text". The
            list is comma separated with the column label going before the colon and the
            reconciliation type after the colon. Note: This overrides any column type
            guesses. You may use this multiple times.""",
    )

    parser.add_argument(
        "--user-weights",
        default="",
        help="""A string with user IDs and corresponding weights. Used to favor
            contributions from specific users when using the "text" column
            type. The format is --user-weights "foo:-10,bar:25". The list is
            comma separated with the user ID going before the colon and the
            weight after the colon. Note: This weight is added to the
            fuzzywuzzy score, which is a percentage. --user-weights "aSmith:70"
            would very often select aSmith's transcriptions. --user-weights
            "aSmith:10" would add 10 to all of aSmith's scores. --user-weights
            "aSmith:-50" would distrust aSmith's transcriptions.""",
    )

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

    # We may want to make these arguments in the future
    defaults = {
        "format": "nfn_sql",  # "nfn",
        "group_by": "subject_id",
        "key_column": "classification_id",
        "user_column": "user_name",
        "page_size": 20,
    }
    for key, value in defaults.items():
        args[key] = value

    # Format the user weights: user1:weight1, user2:weight2, ...
    args.user_weights_ = {}
    for user_weight in args.user_weights.split(","):
        user_weight = user_weight.strip()
        for user, weight in user_weight.split(":"):
            args.user_weights_[user.lower()] = int(weight)

    if args.fuzzy_ratio_threshold < 0 or args.fuzzy_ratio_threshold > 100:
        print("--fuzzy-ratio-threshold must be between 0 and 100.")
        sys.exit(1)

    if args.fuzzy_set_threshold < 0 or args.fuzzy_set_threshold > 100:
        print("--fuzzy-set-threshold must be between 0 and 100.")
        sys.exit(1)

    return args


def zip_files(args):
    """Put results into a zip file."""
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


def append_column_types(args, column_types):
    """Update or add argument column types to the inferred column types."""
    if args.column_types:
        for arg in args.column_types:
            for option in arg.split(","):
                name, col_type = (x.strip() for x in option.split(":"))
                column_types[name] = col_type


def validate_columns(args, column_types, unreconciled):
    """Validate that the columns are in the unreconciled data frame.

    Also verify that the column types are an existing plug-in.
    """
    plugins = util.get_plugins("column_types")
    plugin_types = list(plugins.keys())

    error = missing_headers(unreconciled, column_types, plugin_types)
    error |= missing_key_columns(args, unreconciled)

    if error:
        error_exit(unreconciled, plugin_types)


def missing_headers(unreconciled, column_types, plugin_types):
    """Look for errors with column validation."""
    error = False
    for column, column_type in column_types.items():
        if column not in unreconciled.columns:
            error = True
            print(f'ERROR: "{column}" is not a column header')
        if column_type["type"] not in plugin_types:
            error = True
            print('ERROR: "{}" is not a column type'.format(column_type["type"]))
    return error


def missing_key_columns(args, unreconciled):
    """Look for errors with column validation."""
    error = False
    for column in [args.group_by, args.key_column]:
        if column not in unreconciled.columns:
            error = True
            print(f'ERROR: "{column}" is not a column header')
    return error


def error_exit(unreconciled, plugin_types):
    """Look for errors with column validation."""
    print(f"\nValid column types are: {plugin_types}\n")
    print("Valid column headers are:")
    for col in unreconciled.columns:
        print(f"\t{col}")
    print('* Please remember that "--format=nfn" may rename column headers.')
    sys.exit(1)


def reconcile_data(args, unreconciled, column_types):
    """Build and output reconciled data."""
    reconciled, explanations = reconciler.build(args, unreconciled, column_types)

    if args.reconciled:
        reconciled = reconciled_df.reconciled_output(args, reconciled, column_types)

    if args.summary:
        summary.report(args, unreconciled, reconciled, explanations, column_types)


def main():
    """Reconcile the data."""
    args = parse_args()

    formats = util.get_plugins("formats")
    unreconciled, column_types = formats[args.format].read(args)

    if unreconciled.shape[0] == 0:
        sys.exit(f"Workflow {args.workflow_id} has no data.")

    append_column_types(args, column_types)
    validate_columns(args, column_types, unreconciled)

    if args.unreconciled:
        unreconciled.to_csv(args.unreconciled, index=False)

    if args.reconciled or args.summary:
        reconcile_data(args, unreconciled, column_types)

    if args.zip:
        zip_files(args)


if __name__ == "__main__":
    main()
