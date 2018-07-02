"""Split the CSV file based upon the given column and regular expression."""


import os
import argparse
import textwrap
import pandas as pd


def parse_command_line():
    """Get user input."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        fromfile_prefix_chars='@',
        description=textwrap.dedent("""
            Split the CSV file based upon the given column and regular
            expression."""))

    parser.add_argument('-i', '--input-file', required=True,
                        help="""The input file.""")

    parser.add_argument('-o', '--output-prefix', required=True,
                        help="""The output files' prefix.""")

    parser.add_argument('-p', '--pattern',
                        help="""What are we looking for inclusion in the column
                            to include in the new CSV file.""")

    parser.add_argument('-c', '--column', default='dynamicProperties',
                        help="""Which column has the key value to split
                            (default=dynamicProperties)""")

    parser.add_argument('--group-by', default='occurrenceID',
                        help="""Group the rows by this column
                            (Default=occurrenceID).""")

    parser.add_argument('--key-column', default='classificationID',
                        help="""The column containing the primary key
                            (Default=classificationID).""")

    args = parser.parse_args()
    return args


def process_csv(args):
    """Get the data from the input CSV."""
    df = pd.read_csv(args.input_file, low_memory=False, dtype=str).fillna('')

    if args.pattern:
        df = df.loc[df[args.column].str.contains(args.pattern, regex=True), :]

    empty_columns = []
    for column in df.columns:
        values = df[column].unique()
        if len(values) == 1 and not values[0]:
            empty_columns.append(column)

    df = (df.drop(empty_columns, axis=1)
            .sort_values([args.group_by, args.key_column])

    csv_name = args.output_prefix + '.csv'
    df.to_csv(csv_name, index=False)

    return df


def write_args(args, df):
    """Output an arguments file for reconcile.py."""
    args_name = args.output_prefix + '_args.txt'

    with open(args_name, 'w') as args_file:
        args_file.write('--title={}\n'.format(
            args.output_prefix.split(os.sep)[-1]))
        args_file.write('--format=csv\n')
        args_file.write('--group-by={}\n'.format(args.group_by))
        args_file.write('--key-column={}\n'.format(args.key_column))
        args_file.write('--unreconciled={}\n'.format(
            args.output_prefix + '_unreconciled.csv'))
        args_file.write('--reconciled={}\n'.format(
            args.output_prefix + '_reconciled.csv'))
        args_file.write('--summary={}\n'.format(
            args.output_prefix + '_summary.html'))
        args_file.write('--zip={}\n'.format(args.output_prefix + '.zip'))
        skip_columns = [args.group_by, args.key_column]
        for column in [c for c in df.columns if c not in skip_columns]:
            args_file.write('--column-types={}:text\n'.format(column))


def main():
    """Main function."""
    args = parse_command_line()
    df = process_csv(args)
    write_args(args, df)


if __name__ == "__main__":
    main()
