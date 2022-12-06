from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
from jinja2 import Environment
from jinja2 import PackageLoader

from pylib import result
from pylib.table import Table

NO_MATCH = result.Result.NO_MATCH.value


def report(args, unreconciled: Table, reconciled: Table):
    explanations = reconciled.explanation_df(args, unreconciled)
    problems = reconciled.problem_df(args)
    table = build_table(args, unreconciled, reconciled, explanations, problems)

    env = Environment(loader=PackageLoader("reconcile", "."))
    template = env.get_template("pylib/summary/template.html")

    summary = template.render(
        title="test",
        table=table,
    )

    with open(args.summary, "w", encoding="utf-8") as out_file:
        out_file.write(summary)


def build_table(args, unreconciled, reconciled, explanations, problems):
    # Get the dataframe parts for the reconciled, explanations, & unreconciled data
    df1 = reconciled.to_df(args)
    df1["__order__"] = 1

    explanations["__order__"] = 2

    df3 = unreconciled.to_df(args)
    df3["__order__"] = 3

    # Combine the dataframe parts into a single dataframe
    keys = [args.group_by, "__order__", args.row_key]
    keys += [args.user_column] if args.user_column else []

    df = pd.concat([df1, explanations, df3]).fillna("")
    df = df.reset_index(drop=True)
    df = df[keys + [c for c in df.columns if c not in keys]]
    df = df.sort_values(keys)
    df = df.applymap(create_link)
    df = Table.sort_columns(args, df)
    df = df.reset_index(drop=True)

    # Add an open/close button for the subjects
    btn = '<button title="Open or close all subjects">+</button>'
    df.insert(0, btn, "")
    idx = df.loc[df["__order__"] == 1].index
    df.iloc[idx, 0] = df.iloc[idx].apply(set_button, args=(args,), axis="columns")

    # Clear the button column for explanations and unreconciled
    df.loc[df["__order__"] == 2, args.group_by] = ""
    df.loc[df["__order__"] == 3, args.group_by] = ""

    # Basic styles for the table
    style = df.style.set_table_styles(
        [
            {
                "selector": "table",
                'props': [("font-family", "Bitstream Vera Serif Bold")],
            },
            {
                "selector": "th",
                'props': [
                    ("padding", "2px 4px"),
                    ("vertical-align", "bottom"),
                ],
            },
            {
                "selector": "tbody td",
                'props': [("border-bottom", "1px solid lightgray")],
            },
        ]
    ).hide(axis="index").hide(axis="columns", subset=["__order__"])

    # Highlight explanations columns
    columns = list(reconciled.get_column_types().keys()) + ["__order__"]
    style = style.apply(
        set_background, subset=columns, axis=1, color='lightgray', order=2
    )

    # Highlight unreconciled columns
    columns = [c for c in df.columns if c not in [btn, args.group_by]]
    style = style.apply(
        set_background, subset=columns, axis=1, color='#e7f0f0', order=3
    )

    return style.to_html()


def set_background(row, color, order):
    if row["__order__"] == order:
        return [f"background-color: {color}"] * len(row)
    return [""] * len(row)


def set_button(row, args):
    sid = row[args.group_by]
    title = "Open or close this subject"
    return f'<button data-group-by="{sid}" title="{title}">+</button>'


def create_link(value):
    """Convert a link into an anchor element."""
    try:
        url = urlparse(value)
        if url.scheme and url.netloc and url.path:
            return '<a href="{value}" target="_blank">{value}</a>'.format(value=value)
    except (ValueError, AttributeError):
        pass
    return value


# def get_groups(args, unreconciled, reconciled, results_df):
#     keys = get_keys(args)
#
#     df1 = reconciled.to_df(args)
#     df1["__order__"] = 1
#
#     results_df["__order__"] = 2
#
#     df3 = unreconciled.to_df(args)
#     df3["__order__"] = 3
#
#     df = pd.concat([df1, results_df, df3]).fillna("")
#     df = df.reset_index(drop=True)
#     df = df[keys + [c for c in df.columns if c not in keys]]
#     df = df.sort_values(keys)
#     df = df.drop(["__order__"], axis="columns")
#     df = df.applymap(create_link)
#     df = Table.sort_columns(args, df)
#
#     groups = {}
#     for subject_id, rows in df.groupby(args.group_by):
#         rows = rows.to_dict("records")
#         groups[subject_id] = {
#             "reconciled": rows[0],
#             "explanations": rows[1],
#             "unreconciled": rows[2:],
#         }
#
#     return groups, df.columns
#
#
# def header_data(args, unreconciled, reconciled, transcribers):
#     """Get data that goes into the report header."""
#     name = args.workflow_name if args.workflow_name else args.workflow_csv
#     title = f"Summary of '{name}'"
#     if args.workflow_id:
#         title += f" ({args.workflow_id})"
#
#     return {
#         "date": datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M"),
#         "title": title,
#         "ratio": len(unreconciled) / len(reconciled),
#         "subjects": len(reconciled),
#         "transcripts": len(unreconciled),
#         "transcribers": len(transcribers),
#     }
#
#
# def get_filters(groups, result_counts, results_df):
#     filters = {
#         "__select__": ["Show All", "Show All Problems"],
#         "Show All": list(groups.keys()),
#         "Show All Problems": [],
#     }
#
#     problems = get_problems(results_df)
#
#     for label in result_counts.keys():
#         name = f"Show problems with: {label}"
#         filters["__select__"].append(name)
#         filters[name] = []
#
#     for label, subject_ids in problems.items():
#         name = f"Show problems with: {label}"
#         filters[name] = subject_ids
#
#     all_problems = set()
#     for subject_ids in problems.values():
#         all_problems |= set(subject_ids)
#     filters["Show All Problems"] = list(all_problems)
#
#     return filters
#
#
# def get_problems(results_df):
#     """Get a list of problems for each field."""
#     problems = defaultdict(list)
#     for subject_id, row in results_df.iterrows():
#         for col, val in row.items():
#             if not isinstance(val, dict):
#                 continue
#             if val["result"] >= NO_MATCH:
#                 problems[col].append(subject_id)
#     return problems
#
#
# def user_summary(args, unreconciled):
#     if not args.user_column:
#         return {}
#     transcribers = defaultdict(int)
#     for row in unreconciled:
#         field = row.get(args.user_column)
#         if field:
#             transcribers[field.value] += 1
#     transcribers = sorted(transcribers.items())
#     transcribers = [{"name": n, "count": c} for n, c in transcribers]
#     return transcribers
#
#
# def reconciled_summary(column_types, result_counts, result_dict):
#     """Build a summary of how each field was reconciled."""
#     how_reconciled = []
#     for label, counts in result_counts.items():
#         how = {
#             "name": label,
#             "col_type": column_types[label],
#             "total": sum(v for k, v in counts.items() if k < NO_MATCH),
#         }
#         how |= {k: "" for k in result_dict.values()}
#         for res, count in counts.items():
#             key = result_dict[res]
#             how[key] = f"{count:,}"
#         how_reconciled.append(how)
#
#     return how_reconciled
#
#
# def get_result_counts(results_df, args):
#     """Get how many times each result happened for each column."""
#     counts = defaultdict(dict)
#     skips = get_keys(args)
#     for col in [c for c in results_df.columns if c not in skips]:
#         series = pd.Series([r["result"] for r in results_df[col]])
#         series = series.value_counts().to_dict()
#         for key, val in series.items():
#             counts[col][key] = val
#     return counts
