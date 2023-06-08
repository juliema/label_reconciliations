import json
import re
from collections import defaultdict

import pandas as pd
from dateutil.parser import parse

from pylib import utils
from pylib.fields.box_field import BoxField
from pylib.fields.length_field import LengthField
from pylib.fields.mark_index_field import MarkIndexField
from pylib.fields.noop_field import NoOpField
from pylib.fields.point_field import PointField
from pylib.fields.same_field import SameField
from pylib.fields.select_field import SelectField
from pylib.fields.text_field import TextField
from pylib.row import Row
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

        row.add_field(
            args.group_by,
            SameField(value=raw_row["subject_ids"].split(",", 1)[0]),
        )

        row.add_field(args.row_key, NoOpField(value=raw_row[args.row_key]))

        if args.user_column:
            row.add_field(
                args.user_column, NoOpField(value=raw_row.get(args.user_column, ""))
            )

        for task in json.loads(raw_row["annotations"]):
            flatten_task(task, row, strings)

        extract_subject_data(raw_row, row)
        extract_metadata(raw_row, row)
        extract_misc_data(raw_row, row)

        table.append_row(row)

    return table


# ###################################################################################
def flatten_task(
    task: dict, row: Row, strings: dict, task_id: str = ""
):
    """Extract task annotations from the json object in the annotations' column.

    Task annotations are nested json blobs with a WTF format. Part of the WTF is that
    each record can have a different format. It all starts with a list of annotations.
    """
    task_id = task.get("task", task_id)

    match task:

        case {"value": [str(), *__], **___}:
            list_task(task, row, task_id)

        case {"value": list(), **__}:
            subtask_task(task, row, strings, task_id)

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


def subtask_task(task, row, strings, task_id):
    """Handle an annotation with subtasks."""
    task_id = task.get("task", task_id)
    for subtask in task["value"]:
        flatten_task(subtask, row, strings, task_id)


def list_task(task: dict, row: Row, task_id: str) -> None:
    values = sorted(task.get("value", ""))
    row.add_field(task["task_label"], TextField(value=" ".join(values)), task_id)


def select_label_task(task: dict, row: Row, task_id: str) -> None:
    option = task.get("option")
    value = task.get("label", "") if option else task.get("value", "")
    row.add_field(task["select_label"], SelectField(value=value), task_id)


def mark_index_task(task, row, strings, task_id) -> None:
    value = strings[task["task"]][task["value"]]
    index = task["markIndex"]
    name = f'{task["taskType"]}_{index + 1}'
    row.add_field(name, MarkIndexField(value=value, index=index), task_id)


def task_label_task(task: dict, row: Row, task_id: str) -> None:
    value = task.get("value", "")
    row.add_field(task["task_label"], TextField(value=value), task_id)


def box_task(task: dict, row: Row, task_id: str) -> None:
    row.add_field(
        task["tool_label"],
        BoxField(
            left=round(task["x"]),
            right=round(task["x"] + task["width"]),
            top=round(task["y"]),
            bottom=round(task["y"] + task["height"]),
        ),
        task_id,
    )


def length_task(task: dict, row: Row, task_id: str) -> None:
    row.add_field(
        task["tool_label"],
        LengthField(
            x1=round(task["x1"]),
            y1=round(task["y1"]),
            x2=round(task["x2"]),
            y2=round(task["y2"]),
        ),
        task_id,
    )


def point_task(task: dict, row: Row, task_id: str) -> None:
    field = PointField(x=round(task["x"]), y=round(task["y"]))
    label = task.get("tool_label", task.get("toolType"))
    label = label if label else task["toolType"]
    row.add_field(label, field, task_id)


# #############################################################################
def extract_subject_data(raw_row, row):
    """Extract subject data from the json object in the subject_data column.

    We prefix the new column names with "subject_" to keep them separate from
    the other data df columns. The subject data json looks like:
        {<subject_id>: {"key_1": "value_1", "key_2": "value_2", ...}}
    """
    annos = json.loads(raw_row["subject_data"])

    for val1 in annos.values():
        for key2, val2 in val1.items():
            if key2 and key2 != "retired":
                row.add_field(key2, SameField(value=val2))


# #############################################################################
def extract_metadata(raw_row, row):
    """Extract a few field from the metadata JSON object."""
    annos = json.loads(raw_row["metadata"])

    def _date(value):
        return parse(value).strftime("%d-%b-%Y %H:%M:%S")

    row.add_field("started_at", NoOpField(value=_date(annos.get("started_at"))))
    row.add_field("finished_at", NoOpField(value=_date(annos.get("finished_at"))))


# #############################################################################
def extract_misc_data(raw_row, row):
    wanted = """ gold_standard expert workflow_version """.split()
    for key in wanted:
        if (value := raw_row.get(key)) is not None:
            row.add_field(key, NoOpField(value=value))


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
