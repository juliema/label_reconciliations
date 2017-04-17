"""Common utilites."""

import re

GROUP_BY = 'subject_id'             # We group on this column
COLUMN_PATTERN = r'^T\d+[st]:\s*'   # Either a select or text column
SELECT_COLUMN_PATTERN = r'^T\d+s:'  # How select columns are labeled
TEXT_COLUMN_PATTERN = r'^T\d+t:'    # How text columns are labeled
ROW_TYPES = {  # Row types and their sort order
    'explanations': 'A',
    'reconciled': 'B',
    'unreconciled': 'C'}


def format_name(name):
    """Remove tag ID and type flag from the column name."""

    name = re.sub(COLUMN_PATTERN, '', name)
    return re.sub(r'\W', '', name)


def output_dataframe(df, file_name, index=True):
    """Write a dataframe to a file."""

    columns = {c: format_name(c) for c in df.columns}
    new_df = df.rename(columns=columns)
    new_df.to_csv(file_name, sep=',', encoding='utf-8', index=index)
