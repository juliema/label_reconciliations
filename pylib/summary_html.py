import json
from collections import defaultdict
from datetime import datetime

import pandas as pd
from jinja2 import Environment
from jinja2 import PackageLoader

from pylib import result
from pylib.table import Table


def report(args, unreconciled: Table, reconciled: Table):
    """Build a report including reconciled and unreconciled data."""
    # Get the report template
    env = Environment(loader=PackageLoader("reconcile", "."))
    template = env.get_template("pylib/summary/template.html")

    transcribers = user_summary(args, unreconciled)

    groups, columns = get_groups(args, unreconciled, reconciled)
    column_types = reconciled.get_column_types()

    summary = template.render(
        args=vars(args),
        header=header_data(args, unreconciled, reconciled, transcribers),
        groups=iter(groups.items()),
        columns=list(columns),
        reconciled=reconciled_summary(groups, column_types),
        transcribers=transcribers,
        filters=get_filters(args, groups),
    )

    with open(args.summary, "w", encoding="utf-8") as out_file:
        out_file.write(summary)


def get_groups(args, unreconciled, reconciled):
    keys = [args.group_by, "__order__", args.row_key]
    keys += [args.user_column] if args.user_column else []

    df1 = pd.DataFrame(reconciled.to_reconciled_records())
    df1["__order__"] = 1

    df2 = pd.DataFrame(reconciled.to_explanations(args.group_by))
    df2["__order__"] = 2

    df3 = pd.DataFrame(unreconciled.to_unreconciled_records())
    df2["__order__"] = 3

    df = pd.concat([df1, df2, df3]).fillna("")
    df = df[keys + [c for c in df.columns if c not in keys]]
    df = df.sort_values(keys)
    df = df.drop(["__order__"], axis="columns")

    groups = {}
    for subject_id, rows in df.groupby(args.group_by):
        rows = rows.to_dict("records")
        groups[subject_id] = {
            "reconciled": rows[0],
            "explanations": rows[1],
            "unreconciled": rows[2:],
        }

    return groups, df.columns


def header_data(args, unreconciled, reconciled, transcribers):
    """Get data that goes into the report header."""
    return {
        "date": datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M"),
        "title": f"Summary of '{args.workflow_name}' ({args.workflow_id})",
        "ratio": len(unreconciled) / len(reconciled),
        "subjects": len(reconciled),
        "transcripts": len(unreconciled),
        "transcribers": len(transcribers),
    }


def get_filters(args, groups):
    filters = {
        "__select__": ["Show All", "Show All Problems"],
        "Show All": list(groups.keys()),
        "Show All Problems": [],
    }
    return filters


def user_summary(args, unreconciled):
    if not args.user_column:
        return {}
    transcribers = defaultdict(int)
    for row in unreconciled:
        field = row.get(args.user_column)
        if field:
            transcribers[field.value] += 1
    transcribers = sorted(transcribers.items())
    transcribers = [{"name": n, "count": c} for n, c in transcribers]
    return transcribers


def reconciled_summary(groups, column_types):
    """Build a summary of how each field was reconciled."""
    result_counts = {}
    for label, type_ in column_types.items():
        result_counts[label] = {f.value: 0 for f in type_.results()}

    for group in groups.values():
        for field in group["explanations"].values():
            if field:
                field = json.loads(field)
                if isinstance(field, dict) and field["base_label"] in result_counts:
                    result_counts[field["base_label"]][field["flag"]] += 1

    result_dict = result.result_dict()
    how_reconciled = []
    for label, counts in result_counts.items():
        how = {
            "name": label,
            "col_type": column_types[label],
            "total": sum(counts.values()),
        }
        how |= {k: "" for k in result_dict.values()}
        for res, count in counts.items():
            key = result_dict[res]
            how[key] = f"{count:,}"
        how_reconciled.append(how)

    return how_reconciled
