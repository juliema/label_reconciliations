import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import plotly.express as px
from jinja2 import Environment
from jinja2 import PackageLoader
from pandas.io.formats.style import Styler

from pylib.fields.base_field import Flag
from pylib.flag import PROBLEM, FLAG_END, flag_labels
from pylib.table import Table

ALIAS = "__alias__"
ROW_TYPE = "__row_type__"


def report(args, unreconciled: Table, reconciled: Table):
    pd.options.styler.render.max_elements = 999_999_999
    pd.options.styler.render.max_rows = 999_999

    unreconciled_df = unreconciled.to_df(args)
    reconciled_df = reconciled.to_df(args)
    flag_df = reconciled.to_flag_df(args)
    alias_group_by(args, unreconciled_df, reconciled_df, flag_df)

    has_users = 1 if args.user_column in unreconciled_df.columns else 0
    transcribers_df = get_transcribers_df(args, unreconciled_df)
    transcribers = get_transcribers_table(transcribers_df)

    env = Environment(loader=PackageLoader("reconcile", "."))
    template = env.get_template("pylib/summary/summary.html")

    filters = {}
    skeleton, groups = None, {}
    print_detail = 0 if args.no_summary_detail else 1
    if print_detail:
        filters = get_filters(args, flag_df)
        skeleton, groups = get_reconciliations(
            args,
            unreconciled_df,
            reconciled_df,
            flag_df,
        )

    summary = template.render(
        date=datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M"),
        header=header_data(args, unreconciled, reconciled, transcribers),
        has_users=has_users,
        transcribers=transcribers,
        chart=get_chart(args, transcribers_df),
        threshold=args.max_transcriptions,
        pageSize=args.page_size,
        results=get_results(args, flag_df),
        filters=filters,
        groups=groups,
        skeleton=skeleton,
        print_detail=print_detail,
    )

    with open(args.summary, "w", encoding="utf-8") as out_file:
        out_file.write(summary)


def alias_group_by(args, unreconciled_df, reconciled_df, flag_df):
    """Rename the group-by field to a simple integer.

    The group-by field is typically something sensible like a subject-id, but
    in CSV or JSON files it can be anything like a file name, so we should both
    shorten long IDs and make sure we can easily put them into HTML data fields.
    """
    aliases = reconciled_df[args.group_by].to_dict()
    aliases = {v: k for k, v in aliases.items()}

    unreconciled_df[ALIAS] = unreconciled_df[args.group_by].map(aliases)
    reconciled_df[ALIAS] = reconciled_df[args.group_by].map(aliases)
    flag_df[ALIAS] = flag_df[args.group_by].map(aliases)

    flag_df.set_index(ALIAS, drop=False, inplace=True)


def header_data(args, unreconciled, reconciled, transcribers):
    name = args.workflow_name if args.workflow_name else Path(args.input_file).stem
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


def get_transcribers_df(args, unreconciled_df):
    if args.user_column not in unreconciled_df.columns:
        return pd.DataFrame(columns=["Transcriber", "Count"])

    df = unreconciled_df.sort_values(args.user_column)
    df = df.groupby(args.user_column)[[args.user_column]].count()
    df = df.rename(columns={args.user_column: "Count"})
    df["Transcriber"] = df.index
    df = df[["Transcriber", "Count"]]
    return df


def get_transcribers_table(transcribers_df):
    style = transcribers_df.style.set_table_styles(
        [
            {
                "selector": "th",
                "props": [
                    ("padding", "2px 4px"),
                    ("text-align", "left"),
                    ("text-decoration", "underline"),
                ],
            },
            {
                "selector": "td",
                "props": [
                    ("padding", "2px 4px"),
                ],
            },
        ]
    ).hide(axis="index")
    style = style.set_properties(
        **{"text-align": "right"}, axis="columns", subset=["Count"]
    )

    return style.to_html(index=False)


def get_chart(args, transcribers_df):
    df = transcribers_df.groupby("Count").count()
    df["Transcriptions"] = df.index
    lump = df[df["Transcriptions"] >= args.max_transcriptions].sum()
    df = df[df["Transcriptions"] < args.max_transcriptions]

    df.loc[f"{args.max_transcriptions}+"] = [
        lump["Transcriber"],
        args.max_transcriptions,
    ]

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


def get_results(args, flag_df):
    data = []
    for col in flag_df.columns:
        datum = flag_df[col].apply(get_flag_field, field="flag").value_counts()
        data.append(datum)
    df = pd.concat(data, axis=1)

    df = df.transpose().sort_index()

    for col in range(Flag.OK, FLAG_END):
        if col not in df.columns:
            df[col] = 0

    df = df[range(Flag.OK, FLAG_END)]
    df = df.fillna(0).astype(int)

    df["Total"] = df[range(Flag.OK, Flag.ONLY_ONE)].sum(axis="columns")

    total = df.pop("Total")
    df.insert(len(df.columns) - 3, "Total", total)

    renames = {k: v for k, v in flag_labels().items()}
    df = df.rename(columns=renames)
    df.insert(0, "Field", list(df.index))
    df = df.drop([args.group_by, ALIAS, ROW_TYPE], axis=0)

    style = df.style.set_table_styles(
        [
            {
                "selector": "th",
                "props": [
                    ("font-weight", "bold"),
                    ("padding", "4px 1rem"),
                ],
            },
        ]
    ).hide(axis="index")

    style = style.apply(align, axis=0)
    style = style.applymap_index(align_index, axis=1)
    return style.to_html()


def get_flag_field(x, field):
    if isinstance(x, dict):
        return x[field]
    return x


def align(column):
    if column.name == "Field":
        return ["text-align: left;"] * len(column)
    return ["text-align: center;"] * len(column)


def align_index(label):
    if label == "Field":
        return "text-align: left;"
    return "text-align: center;"


def get_filters(args, flag_df):
    filters = {
        "Show All": list(flag_df.index),
        "Show All Problems": [],
    }

    all_problems = set()
    problem_filters = {}
    exclude = (args.group_by, ALIAS, ROW_TYPE)
    for col in [c for c in flag_df.columns if c not in exclude]:
        ids = flag_df[
            flag_df[col].apply(get_flag_field, field="flag").isin(PROBLEM)
        ].index
        name = f"Show problems with: {col}"
        problem_filters[name] = list(ids)
        all_problems |= set(ids)

    filters["Show All Problems"] = list(all_problems)

    filters |= {" ".join(k.split()): v for k, v in problem_filters.items()}

    return filters


def get_reconciliations(args, unreconciled_df, reconciled_df, flag_df):
    df = merge_dataframes(args, unreconciled_df, reconciled_df, flag_df)

    btn = add_buttons(df)

    class_df = get_class_df(args, btn, df, flag_df)

    style = get_styler(class_df, df)

    html = get_table(style)

    rows, skeleton = split_table(html)

    groups = add_group_by_to_rows(rows)

    return skeleton, groups


def merge_dataframes(args, unreconciled_df, reconciled_df, flag_df):
    """Get the dataframe parts for the reconciled, explanations, & unreconciled data."""
    reconciled_df[ROW_TYPE] = 1

    flag_df[ROW_TYPE] = 2
    note_df = flag_df.copy()
    note_df = note_df.applymap(get_flag_field, field="note")

    unreconciled_df[ROW_TYPE] = 3

    # Combine the dataframe parts into a single dataframe
    keys = [args.group_by, ROW_TYPE]
    keys += [args.row_key] if args.row_key in unreconciled_df.columns else []
    keys += [args.user_column] if args.user_column in unreconciled_df.columns else []

    df = pd.concat([unreconciled_df, note_df, reconciled_df]).fillna("")
    df = df.reset_index(drop=True)
    df = df[keys + [c for c in df.columns if c not in keys]]
    df = df.sort_values(keys)
    df = df.applymap(create_link)
    df = df.reset_index(drop=True)

    return df


def create_link(value):
    """Convert a link into an anchor element."""
    try:
        url = urlparse(value)
        if url.scheme and url.netloc and url.path:
            return '<a href="{value}" target="_blank">{value}</a>'.format(value=value)
    except (ValueError, AttributeError):
        pass
    return value


def add_buttons(df):
    """Add an open/close button for the subjects."""
    btn = '<button class="hide" title="Open or close all subjects"></button>'
    df.insert(0, btn, "")
    idx = df.loc[df[ROW_TYPE] == 1].index
    df.iloc[idx, 0] = df.iloc[idx].apply(set_button, axis="columns")

    # Clear the button column for explanations and unreconciled
    idx = df[df[ROW_TYPE].isin([2, 3])].index
    df.iloc[idx, 0] = df.iloc[idx].apply(set_group_by, axis="columns")
    df.iloc[idx, 1] = ""
    return btn


def set_button(row):
    sid = row[ALIAS]
    title = "Open or close this subject"
    return f"""<button data-group-by="{sid}" title="{title}"></button>"""


def set_group_by(row):
    return f"""<span hidden>{row[ALIAS]}</span>"""


def get_class_df(args, btn, df, flag_df):
    """Get classes for cells."""
    class_df = pd.DataFrame(columns=df.columns, index=df.index)

    excludes = [btn, args.group_by, ROW_TYPE, ALIAS]

    columns = [c for c in df.columns if c not in excludes]
    class_df.loc[df[ROW_TYPE] == 3, columns] = "unrec"

    columns = [c for c in flag_df.columns if c not in excludes]
    class_df.loc[df[ROW_TYPE] == 2, columns] = "explain"

    for col in columns:
        ids = flag_df[
            flag_df[col].apply(get_flag_field, field="flag").isin(PROBLEM)
        ].index
        ids = df.loc[df[ROW_TYPE] == 1 & df[ALIAS].isin(ids)].index
        class_df.loc[ids, col] = "problem"

    return class_df


def get_styler(class_df, df):
    """Set basic styles for the data frame."""
    style = Styler(df, cell_ids=False)
    style = style.hide(axis="index").hide(axis="columns", subset=[ROW_TYPE, ALIAS])
    style = style.set_td_classes(class_df)
    style = style.format(precision=2)
    return style


def get_table(style):
    """Format table directly because some things are not possible with pandas.style."""
    html = style.to_html()
    html = re.sub(r"data row\d+ col\d+\s?", "", html)
    html = re.sub(r"col_heading level\d+ col\d+\s?", "", html)
    html = re.sub(r' class=""\s?', "", html)
    html = re.sub(r'" >', '">', html)
    html = re.sub(
        r'<tr>(\s*)<td><span hidden>([^<"]+)',
        r'<tr class="sub" data-group-by="\2">\1<td><span hidden>\2',
        html,
    )
    return html


def split_table(html):
    """Now split the table into a header, footer, and rows."""
    head1, head2, rows, foot1, foot2 = re.split(r"(\s*</?tbody>)", html)
    skeleton = head1, head2, foot1, foot2
    skeleton = "".join(skeleton)
    return rows, skeleton


def add_group_by_to_rows(rows):
    groups = {}
    rows = re.split(r"(\s*<tr>\s*<td><button)", rows)[1:]
    it = iter(rows)
    for part1 in it:
        part2 = next(it)
        match = re.search(r'data-group-by="([^<\"]+)"', part2)
        groups[match.group(1)] = "".join([part1, part2])
    return groups
