import json
import re
from collections import defaultdict

import pandas as pd
from dateutil.parser import parse

from pylib import utils
from pylib.row import Row
from pylib.row import BoxField, HighlightField, LengthField, MarkIndexField, NoOpField
from pylib.row import PointField, SameField, SelectField, TextField
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

    # A hack to workaround coded values returned from Zooniverse
    strings = get_workflow_strings(args.workflow_csv, args.workflow_id)

    table = Table()
    for raw_row in raw_records:
        row = Row()

        row.append(SameField(
            name=args.group_by, value=raw_row["subject_ids"].split(",", 1)[0],
        ))

        row.append(NoOpField(name=args.row_key, value=raw_row[args.row_key]))

        if args.user_column:
            row.append(NoOpField(
                name=args.user_column, value=raw_row.get(args.user_column, "")
            ))

        for task in json.loads(raw_row["annotations"]):
            flatten_task(task, row, strings, args)

        extract_subject_data(raw_row, row)
        extract_metadata(raw_row, row)
        extract_misc_data(raw_row, row)

        table.append(row)

    return table


# ###################################################################################
def flatten_task(task: dict, row: Row, strings: dict, args, task_id: str = ""):
    """Extract task annotations from the json object in the annotations' column.

    Task annotations are nested json blobs with a WTF format. Part of the WTF is that
    each record can have a different format. It all starts with a list of annotations.
    """
    task_id = task.get("task", task_id)

    match task:

        case {"value": [str(), *__], **___}:
            list_task(task, row, task_id)

        # case {"value": [{"points": list(), **__}, *___], **____}:
        #     polygon_task(task, row, task_id)

        case {"value": list(), "taskType": "highlighter", **__}:
            highlighter_task(task, row, args, task_id)

        case {"value": list(), **__}:
            subtask_task(task, row, strings, args, task_id)

        case {"select_label": _, **__}:
            select_label_task(task, row, task_id)

        case {"task_label": _, **__}:
            task_label_task(task, row, task_id)

        case {"tool_label": _, "width": __, **___}:
            box_task(task, row, task_id)

        case {"tool_label": _, "x1": __, **___}:
            length_task(task, row, task_id)

        case {"tool_label": _, "toolType": "point", "x": __, "y": ___, **____}:
            point_task(task, row, task_id)

        case {"task": _, "value": __, "taskType": ___, "markIndex": ____}:
            mark_index_task(task, row, strings, task_id)

        case _:
            print(f"Annotation type not found: {task}")


def subtask_task(task, row, strings, args, task_id):
    """Handle an annotation with subtasks."""
    task_id = task.get("task", task_id)
    for subtask in task["value"]:
        flatten_task(subtask, row, strings, args, task_id)


def list_task(task: dict, row: Row, task_id: str) -> None:
    values = sorted(task.get("value", ""))
    row.append(TextField(
        name=task["task_label"],
        task_id=task_id,
        value=" ".join(values),
    ))


def select_label_task(task: dict, row: Row, task_id: str) -> None:
    option = task.get("option")
    value = task.get("label", "") if option else task.get("value", "")
    row.append(SelectField(
        name=task["select_label"],
        task_id=task_id,
        value=value,
    ))


def mark_index_task(task: dict, row, strings, task_id) -> None:
    row.append(MarkIndexField(
        name=task["taskType"],
        task_id=task_id,
        value=strings[task["task"]][task["value"]],
        index=task["markIndex"],
    ))


def task_label_task(task: dict, row: Row, task_id: str) -> None:
    row.append(TextField(
        name=task["task_label"],
        task_id=task_id,
        value=task.get("value", ""),
    ))


def box_task(task: dict, row: Row, task_id: str) -> None:
    row.append(BoxField(
        name=task["tool_label"],
        task_id=task_id,
        left=round(task["x"]),
        right=round(task["x"] + task["width"]),
        top=round(task["y"]),
        bottom=round(task["y"] + task["height"]),
    ))


def length_task(task: dict, row: Row, task_id: str) -> None:
    row.append(LengthField(
        name=task["tool_label"],
        task_id=task_id,
        field_set="length",
        x1=round(task["x1"]),
        y1=round(task["y1"]),
        x2=round(task["x2"]),
        y2=round(task["y2"]),
    ))


def point_task(task: dict, row: Row, task_id: str) -> None:
    row.append(PointField(
        name=task.get("tool_label", task.get("toolType")),
        task_id=task_id,
        x=round(task["x"]),
        y=round(task["y"]),
    ))


# def polygon_task(task: dict, row: Row, task_id: str) -> None:
#     points = [PolygonPoint(x=p["x"], y=p["y"]) for p in task["value"]["points"]]
#     row.add_field(task["task_label"], PolygonField(points=points), task_id)


def highlighter_task(task, row, args, task_id):
    fields = HighlightField.unreconciled_list(task, task_id, args)
    for field in fields:
        row.append(field)


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
                row.append(SameField(name=key2, value=val2))


# #############################################################################
def extract_metadata(raw_row, row):
    """Extract a few field from the metadata JSON object."""
    annos = json.loads(raw_row["metadata"])

    def _date(value):
        return parse(value).strftime("%d-%b-%Y %H:%M:%S")

    row.append(NoOpField(name="started_at", value=_date(annos.get("started_at"))))
    row.append(NoOpField(name="finished_at", value=_date(annos.get("finished_at"))))


# #############################################################################
def extract_misc_data(raw_row, row):
    wanted = """ gold_standard expert workflow_version """.split()
    for key in wanted:
        if (value := raw_row.get(key)) is not None:
            row.append(NoOpField(name=key, value=value))


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
