import re
from datetime import datetime
from urllib.parse import urlparse

import pandas as pd
import plotly.express as px
from jinja2 import Environment
from jinja2 import PackageLoader
from pandas.io.formats.style import Styler

from pylib import result
from pylib.table import Table

THRESHOLD = 50
PAGE_SIZE = 20


def report(args, unreconciled: Table, reconciled: Table):
    pd.options.styler.render.max_elements = 999_999_999
    pd.options.styler.render.max_rows = 999_999

    problems = reconciled.problem_df(args)

    transcribers_df = get_transcribers_df(args, unreconciled)
    transcribers = get_transcribers(transcribers_df)

    env = Environment(loader=PackageLoader("reconcile", "."))
    template = env.get_template("pylib/summary/summary.html")
    
    skeleton, groups = get_reconciliations(
        args,
        unreconciled,
        reconciled,
        reconciled.explanation_df(args, unreconciled), 
        problems,
    )

    summary = template.render(
        date=datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M"),
        header=header_data(args, unreconciled, reconciled, transcribers),
        transcribers=transcribers,
        chart=get_chart(transcribers_df),
        results=get_results(reconciled, problems),
        filters=get_filters(reconciled, problems),
        threshold=THRESHOLD,
        pageSize=PAGE_SIZE,
        groups=groups,
        skeleton=skeleton,
    )

    with open(args.summary, "w", encoding="utf-8") as out_file:
        out_file.write(summary)


def get_filters(reconciled, problems):
    columns = list(reconciled.get_column_types().keys())
    filters = {
        "Show All": list(problems.index),
        "Show All Problems": [],
    }

    all_problems = set()
    for col in columns:
        subject_ids = problems[problems[col].isin(result.PROBLEM)].index
        name = f"Show problems with: {col}"
        filters[name] = list(subject_ids)
        all_problems |= set(subject_ids)

    filters["Show All Problems"] = list(all_problems)

    return filters


def get_reconciliations(args, unreconciled, reconciled, explanations, problems):
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
    btn = '<button class="hide" title="Open or close all subjects"></button>'
    df.insert(0, btn, "")
    idx = df.loc[df["__order__"] == 1].index
    df.iloc[idx, 0] = df.iloc[idx].apply(set_button, args=(args,), axis="columns")

    # Clear the button column for explanations and unreconciled
    idx = df[df["__order__"].isin([2, 3])].index
    df.iloc[idx, 0] = df.iloc[idx].apply(set_group_by, args=(args,), axis="columns")
    df.iloc[idx, 1] = ""

    # Classes for table cells
    class_df = pd.DataFrame(columns=df.columns, index=df.index)

    columns = [c for c in df.columns if c not in [btn, args.group_by]]
    class_df.loc[df["__order__"] == 3, columns] = "unrec"

    columns = list(reconciled.get_column_types().keys())
    class_df.loc[df["__order__"] == 2, columns] = "explain"

    for col in columns:
        sid = problems[problems[col].isin(result.PROBLEM)].index
        ids = df.loc[df["__order__"] == 1 & df[args.group_by].isin(sid)].index
        class_df.loc[ids, col] = "problem"

    # Basic styles for the table
    style = Styler(df, cell_ids=False)
    style = style.hide(axis="index").hide(axis="columns", subset=["__order__"])
    style = style.set_td_classes(class_df)

    # Format table directly because some things are not possible with pandas.style
    html = style.to_html()
    html = re.sub(r'data row\d+ col\d+\s?', "", html)
    html = re.sub(r'col_heading level\d+ col\d+\s?', "", html)
    html = re.sub(r' class=""\s?', "", html)
    html = re.sub(r'" >', '">', html)

    html = re.sub(
        r'<tr>(\s*)<td><span hidden>(\d+)',
        r'<tr class="sub" data-group-by="\2">\1<td><span hidden>\2',
        html,
    )

    # Now split the table into a header, footer, and rows
    head1, head2, rows, foot1, foot2 = re.split(r"(\s*</?tbody>)", html)
    skeleton = head1, head2, foot1, foot2
    skeleton = "".join(skeleton)

    groups = {}
    rows = re.split(r'(\s*<tr>\s*<td><button)', rows)[1:]
    it = iter(rows)
    for part1 in it:
        part2 = next(it)
        match = re.search(r'data-group-by="(\d+)"', part2)
        groups[match.group(1)] = "".join([part1, part2])

    return skeleton, groups


def set_group_by(row, args):
    sid = row[args.group_by]
    return f"""<span hidden>{sid}</span>"""


def set_button(row, args):
    sid = row[args.group_by]
    title = "Open or close this subject"
    return f"""<button data-group-by="{sid}" title="{title}"></button>"""


def create_link(value):
    """Convert a link into an anchor element."""
    try:
        url = urlparse(value)
        if url.scheme and url.netloc and url.path:
            return '<a href="{value}" target="_blank">{value}</a>'.format(value=value)
    except (ValueError, AttributeError):
        pass
    return value


def get_chart(transcribers_df):
    df = transcribers_df.groupby("Count").count()
    df["Transcriptions"] = df.index
    lump = df[df["Transcriptions"] >= THRESHOLD].sum()
    df = df[df["Transcriptions"] < THRESHOLD]
    df.loc[f"{THRESHOLD}+"] = [lump["Transcriber"], THRESHOLD]
    fig = px.bar(
        df,
        x="Transcriptions",
        y="Transcriber",
        labels={
            "Transcriptions": "Number of Transcriptions",
            "Transcriber": "Number of Transcribers",
        },
    )
    return fig.to_html()


def get_transcribers_df(args, unreconciled):
    if not args.user_column:
        return pd.DataFrame(columns=["Transcriber", "Count"])

    df = unreconciled.to_df(args)
    df = df.sort_values(args.user_column)
    df = df.groupby(args.user_column)[[args.user_column]].count()
    df = df.rename(columns={args.user_column: "Count"})
    df["Transcriber"] = df.index
    df = df[["Transcriber", "Count"]]
    return df


def get_transcribers(transcribers_df):
    style = transcribers_df.style.set_table_styles(
        [
            {
                "selector": "th",
                'props': [
                    ("padding", "2px 4px"),
                    ("text-align", "left"),
                    ("text-decoration", "underline"),
                ],
            },
            {
                "selector": "td",
                'props': [
                    ("padding", "2px 4px"),
                ],
            },
        ]
    ).hide(axis="index")
    style = style.set_properties(
        **{"text-align": "right"}, axis="columns", subset=["Count"]
    )

    return style.to_html(index=False)


def header_data(args, unreconciled, reconciled, transcribers):
    name = args.workflow_name if args.workflow_name else args.workflow_csv
    title = f"Summary of '{name}'"
    if hasattr(args, "workflow_id") and args.workflow_id:
        title += f" ({args.workflow_id})"
    # Number of transcribers = number of rows minus the header
    trans_count = sum(1 for ln in transcribers.splitlines() if ln.find("<tr>") > -1) - 1

    return {
        "date": datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M"),
        "title": title,
        "ratio": f"{len(unreconciled) / len(reconciled):0.2f}",
        "subjects": f"{len(reconciled):,}",
        "transcripts": f"{len(unreconciled):,}",
        "transcribers": trans_count,
    }


def get_results(reconciled, problems):
    data = []
    columns = list(reconciled.get_column_types().keys())
    for col in columns:
        datum = problems[col].value_counts()
        data.append(datum)
    df = pd.concat(data, axis=1)

    df = Table.natural_column_sort(df).transpose()
    for col in range(result.Result.OK, result.RESULT_END):
        if col not in df.columns:
            df[col] = 0

    df = df[range(result.Result.OK, result.RESULT_END)]
    df = df.fillna(0).astype(int)

    df["Total"] = df[
        range(result.Result.OK, result.Result.NO_MATCH)
    ].sum(axis="columns")

    total = df.pop("Total")
    df.insert(len(df.columns) - 2, "Total", total)

    renames = {k: v for k, v in result.result_labels().items()}
    df = df.rename(columns=renames)
    df.insert(0, "Field", list(df.index))

    style = df.style.set_table_styles(
        [
            {
                "selector": "th",
                'props': [
                    ("font-weight", "bold"),
                    ("padding", "4px 1rem"),
                ],
            },
        ]
    ).hide(axis="index")

    style = style.apply(align, axis=0)
    style = style.applymap_index(align_headers, axis=1)

    return style.to_html()


def align(column):
    if column.name == "Field":
        return ["text-align: left;"] * len(column)
    return ["text-align: center;"] * len(column)


def align_headers(column):
    if column == "Field":
        return "text-align: left;"
    return "text-align: center;"
