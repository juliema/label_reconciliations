"""Cleanup broken CSV file."""

# pylint: disable=invalid-name

import sys


def main():
    """Start here."""
    with open(sys.argv[1]) as in_file:
        for line in in_file:
            print(line.rstrip() + '"')


if __name__ == "__main__":
    main()
