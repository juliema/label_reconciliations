import json
import re
from collections import defaultdict

import pandas as pd
from dateutil.parser import parse

from pylib import utils
from pylib.row import Row
from pylib.row import BoxField, HighlightField, LengthField, MarkIndexField, NoOpField
from pylib.row import PointField, PolygonField, SameField, SelectField, TextField
from pylib.table import Table

Strings = dict[str, dict[int, str]]


# #####################################################################################
def read(args):
    """Read and convert the input CSV data."""
    df = pd.read_csv(args.input_file, dtype=str)

    args.workflow_id = get_workflow_id(args, df)
    args.workflow_name = get_workflow_name(args, df)

    df = df.loc[df.workflow_id == str(args.workflow_id), :].fillna("")
    raw_records = df.to_dict("records")

    # A hack to workaround UUID coded values returned from Zooniverse
    strings = get_workflow_strings(args.workflow_csv, args.workflow_id)

    table = Table()
    for raw_row in raw_records:
        row = Row()

        row.add(
            SameField(
                name=args.group_by,
                value=raw_row["subject_ids"].split(",", 1)[0],
            )
        )

        row.add(NoOpField(name=args.row_key, value=raw_row[args.row_key]))

        if args.user_column:
            row.add(
                NoOpField(
                    name=args.user_column, value=raw_row.get(args.user_column, "")
                )
            )

        for task in json.loads(raw_row["annotations"]):
            flatten_task(task, row, strings, args)

        extract_subject_data(raw_row, row)
        extract_metadata(raw_row, row)
        extract_misc_data(raw_row, row)

        table.add(row)

    return table


# ###################################################################################
def flatten_task(task: dict, row: Row, strings: dict, args):
    """Extract task annotations from the json object in the annotations' column.

    Task annotations are nested json blobs with a WTF format. Part of the WTF is that
    each record can have vastly different formats. It all starts with a list of
    annotations and typically but not always an annotation will have a list of [one]
    value.
    """
    match task:

        case {"task": _, "value": [str(), *__], **___}:
            list_task(task, row)

        case {"task": _, "value": [{"points": list(), **__}, *___], **____}:
            polygon_task(task, row)

        case {"task": _, "value": list(), "taskType": "highlighter", **__}:
            highlighter_task(task, row, args)

        case {"task": _, "value": [{"select_label": _, **__}, *___], **____}:
            select_label_task(task, row)

        case {"task": _, "value": _, "task_label": __, **___}:
            task_label_task(task, row)

        # ######## More here ##########################################################
        case {"tool_label": _, "width": __, **___}:
            box_task(task, row)

        case {"tool_label": _, "x1": __, **___}:
            length_task(task, row)

        case {"tool_label": _, "toolType": "point", "x": __, "y": ___, **____}:
            point_task(task, row)

        case {"task": _, "value": __, "taskType": ___, "markIndex": ____}:
            mark_index_task(task, row, strings)

        case _:
            print(f"Annotation type not found: {task}")


def list_task(task: dict, row: Row) -> None:
    values = sorted(task.get("value", ""))
    row.add(
        TextField(
            name=task["task_label"],
            task_id=task.get("task", ""),
            value=" ".join(values),
        )
    )


def select_label_task(task: dict, row: Row) -> None:
    first_value = task["value"][0]
    option = first_value.get("option")
    value = first_value.get("label", "") if option else first_value.get("value", "")
    row.add(
        SelectField(
            name=first_value["select_label"], task_id=task.get("task", ""), value=value
        )
    )


def mark_index_task(task: dict, row, strings) -> None:
    row.add(
        MarkIndexField(
            name=task["taskType"],
            task_id=task.get("task", ""),
            value=strings[task["task"]][task["value"]],
            index=task["markIndex"],
        )
    )


def task_label_task(task: dict, row: Row) -> None:
    row.add(
        TextField(
            name=task["task_label"],
            task_id=task.get("task", ""),
            value=task.get("value", ""),
        )
    )


def box_task(task: dict, row: Row) -> None:
    row.add(
        BoxField(
            name=task["tool_label"],
            task_id=task.get("task", ""),
            left=round(task["x"]),
            right=round(task["x"] + task["width"]),
            top=round(task["y"]),
            bottom=round(task["y"] + task["height"]),
        )
    )


def length_task(task: dict, row: Row) -> None:
    row.add(
        LengthField(
            name=task["tool_label"],
            task_id=task.get("task", ""),
            field_set="length",
            x1=round(task["x1"]),
            y1=round(task["y1"]),
            x2=round(task["x2"]),
            y2=round(task["y2"]),
        )
    )


def point_task(task: dict, row: Row) -> None:
    row.add(
        PointField(
            name=task.get("tool_label", task.get("toolType")),
            task_id=task.get("task", ""),
            x=round(task["x"]),
            y=round(task["y"]),
        )
    )


def polygon_task(task: dict, row: Row) -> None:
    points = [utils.Point(x=p["x"], y=p["y"]) for p in task["value"][0]["points"]]
    row.add(
        PolygonField(
            name=task["task_label"], task_id=task.get("task", ""), points=points
        )
    )


def highlighter_task(task, row, args):
    fields = HighlightField.unreconciled_list(task, task.get("task", ""), args)
    for field in fields:
        row.add(field)


# #############################################################################
def extract_subject_data(raw_row, row):
    """Extract subject data from the json object in the subject_data column.

    The subject data json looks like:
        {<subject_id>: {"key_1": "value_1", "key_2": "value_2", ...}}
    """
    annos = json.loads(raw_row["subject_data"])

    for val1 in annos.values():
        for key2, val2 in val1.items():
            if key2 and key2 != "retired":
                row.add(SameField(name=key2, value=val2))


# #############################################################################
def extract_metadata(raw_row, row):
    """Extract a few field from the metadata JSON object."""
    annos = json.loads(raw_row["metadata"])

    def _date(value):
        return parse(value).strftime("%d-%b-%Y %H:%M:%S")

    row.add(NoOpField(name="started_at", value=_date(annos.get("started_at"))))
    row.add(NoOpField(name="finished_at", value=_date(annos.get("finished_at"))))


# #############################################################################
def extract_misc_data(raw_row, row):
    wanted = """ gold_standard expert workflow_version """.split()
    for key in wanted:
        if (value := raw_row.get(key)) is not None:
            row.add(NoOpField(name=key, value=value))


# #############################################################################
def get_workflow_id(args, df):
    """Pull the workflow ID from the data frame if it was not given."""
    if args.workflow_id:
        return args.workflow_id

    if "workflow_id" not in df.columns:
        utils.error_exit("This is not a Notes from Nature CSV.")

    workflow_ids = df.workflow_id.unique()

    if len(workflow_ids) > 1:
        utils.error_exit(
            "There are multiple workflows in this file. "
            "You must provide a workflow ID as an argument."
        )

    return workflow_ids[0]


def get_workflow_name(args, df):
    """Extract and format the workflow name from the data df."""
    if args.workflow_name:
        return args.workflow_name

    workflow_name = ""
    try:
        workflow_name = df.workflow_name.iloc[0]
        workflow_name = re.sub(r"^[^_]*_", "", workflow_name)
    except KeyError:
        utils.error_exit("Workflow name not found in classifications file.")
    return workflow_name


def get_workflow_strings(workflow_csv, workflow_id) -> Strings:
    """Get strings from the workflow for when they're not in the annotations."""
    if not workflow_csv:
        return {}

    df = pd.read_csv(workflow_csv)
    df = df.loc[df.workflow_id == int(workflow_id), :]
    workflow = df.iloc[-1]  # Get the most recent version

    strings = defaultdict(dict)

    # TODO Moar formats
    for key, value in json.loads(workflow["strings"]).items():
        parts = key.split(".")

        match parts:
            case [_, "tools", __, "details", ___, "answers", *____]:
                strings[f"{parts[0]}.{parts[2]}.{parts[4]}"][int(parts[6])] = value

    return strings
