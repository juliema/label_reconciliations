from collections import defaultdict

from pylib.cell import get_prefix


def sort_columns(starting_columns, df, column_types):
    """Sort column headers."""
    columns = starting_columns
    other, same = [], []

    for col in df.columns:
        key = get_prefix(col)

        if key in column_types and column_types[key] != "same":
            other.append(col)

        elif key in column_types:
            same.append(col)

    columns += other
    columns += same

    columns += [c for c in df.columns if c not in columns]

    df = df[columns]

    return df


def rename_columns(df, column_types):
    """Rename columns by removing task IDs & adding tie-breakers."""
    # Remove the task ID prefix
    names = defaultdict(list)
    for col in df.columns:
        if col[0] == "#":
            new = " ".join(col.split()[1:])
        else:
            new = col
        names[new].append(col)

    # Check if removing the task ID will create duplicate columns, add tie-breaker
    renames = {}
    for new, olds in names.items():
        if len(olds) > 1:
            for i, old in enumerate(olds, 1):
                new_i = f"{new} #{i}"
                renames[old] = new_i
        else:
            renames[olds[0]] = new

    df = df.rename(renames, axis="columns")

    from pprint import pp

    pp(renames)
    pp(column_types)
    new_types = {}
    for old_name, col_type in column_types.items():
        new_name = renames[old_name]
        new_types[new_name] = col_type

    return df, new_types
