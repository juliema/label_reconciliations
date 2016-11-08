import re


COLUMN_PATTERN = r'^T\d+[st]:\s*'   # Either a select or text column
SELECT_COLUMN_PATTERN = r'^T\d+s:'  # How select columns are labeled
TEXT_COLUMN_PATTERN = r'^T\d+t:'    # How text columns are labeled


def format_name(name):
    return re.sub(COLUMN_PATTERN, '', name)


def output_dataframe(df, file_name):
    columns = {c: format_name(c) for c in df.columns}
    new_df = df.rename(columns=columns)
    new_df.to_csv(file_name, sep=',', encoding='utf-8')
