import json
import re
from collections import namedtuple

import pandas as pd
from dateutil.parser import parse as date_parse
from jsonpath_ng import parse

from pylib import utils
from pylib.row import Row
from pylib.row import BoxField, HighlightField, LengthField, MarkIndexField, NoOpField
from pylib.row import PointField, PolygonField, SameField, SelectField, TextField
from pylib.table import Table

# WF_String = Strings and values gathered from the workflow CSV file used for table
# lookups when the expedition CSV values are using UUID-like values as their output
WF_String = namedtuple("WF_String", "value title")


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
                name=args.group_by, value=raw_row["subject_ids"].split(",", 1)[0],
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
def flatten_task(task: dict, row: Row, strings: dict, args, task_id: str = ""):
    """Extract task annotations from the json object in the annotations' column."""
    task_id = task.get("task", task_id)

    match task:

        case {"value": [str(), *__], **___}:
            list_task(task, row, task_id)

        case {"value": [{"points": list(), **__}, *___], **____}:
            polygon_task(task, row, task_id)

        case {"value": list(), "taskType": "highlighter", **__}:
            highlighter_task(task, row, args, task_id)

        case {"value": list(), **__}:
            breakup_task(task, row, strings, args, task_id)

        case {"select_label": _, **__}:
            select_label_task(task, row, task_id)

        case {"task_label": _, **__}:
            task_label_task(task, row, task_id)

        case {"tool_label": _, "width": __, **___}:
            box_task(task, row, strings, task_id)

        case {"tool_label": _, "x1": __, **___}:
            length_task(task, row, task_id)

        case {"task": _, "value": __, "taskType": ___, "markIndex": ____}:
            mark_index_task(task, row, strings, task_id)

        case {"tool_label": _, "toolType": "point", "x": __, "y": ___, **____}:
            point_task(task, row, strings, task_id)

        case {"x": _, "y": _, **__}:
            point_task(task, row, strings, task_id)

        case {"task_type": "dropdown-simple", **__}:
            dropdown_task(task, row, task_id)

        case _:
            print(f"Annotation type not found: {task}\n")


def breakup_task(task, row, strings, args, task_id):
    """Handle an annotation with subtasks."""
    task_id = task.get("task", task_id)
    for subtask in task["value"]:
        flatten_task(subtask, row, strings, args, task_id)


def list_task(task: dict, row: Row, task_id: str) -> None:
    values = sorted(task.get("value", ""))
    field = TextField(name=task["task_label"], task_id=task_id, value=" ".join(values))
    row.add(field)


def select_label_task(task: dict, row: Row, task_id: str) -> None:
    option = task.get("option")
    value = task.get("label", "") if option else task.get("value", "")
    field = SelectField(name=task["select_label"], task_id=task_id, value=value)
    row.add(field)


def dropdown_task(task: dict, row: Row, task_id: str) -> None:
    value = task["value"]
    field = SelectField(
        name=value["select_label"],
        value=value["label"],
        task_id=task_id,
    )
    row.add(field)


def mark_index_task(task: dict, row, strings, task_id: str) -> None:
    strings_key = f'{task["task"]}.{task["value"]}'
    field = MarkIndexField(
        name=task["taskType"],
        task_id=task_id,
        value=strings[strings_key],
        index=task["markIndex"],
    )
    row.add(field)


def task_label_task(task: dict, row: Row, task_id: str) -> None:
    field = TextField(
        name=task["task_label"], task_id=task_id, value=task.get("value", ""),
    )
    row.add(field)


def length_task(task: dict, row: Row, task_id: str) -> None:
    field = LengthField(
        name=task["tool_label"],
        task_id=task_id,
        field_set="length",
        x1=round(task["x1"]),
        y1=round(task["y1"]),
        x2=round(task["x2"]),
        y2=round(task["y2"]),
    )
    row.add(field)


def box_task(task: dict, row: Row, strings, task_id: str) -> None:
    name = task["tool_label"]
    field = BoxField(
        name=name,
        task_id=task_id,
        left=round(task["x"]),
        right=round(task["x"] + task["width"]),
        top=round(task["y"]),
        bottom=round(task["y"] + task["height"]),
    )
    row.add(field)
    detail_tasks(task, row, strings, task_id, name)


def point_task(task: dict, row: Row, strings, task_id: str) -> None:
    name = task.get("tool_label", task.get("toolType"))
    field = PointField(
        name=name, task_id=task_id, x=round(task["x"]), y=round(task["y"])
    )
    row.add(field)
    detail_tasks(task, row, strings, task_id, name)


def polygon_task(task: dict, row: Row, task_id: str) -> None:
    points = [utils.Point(x=p["x"], y=p["y"]) for p in task["value"][0]["points"]]
    field = PolygonField(name=task["task_label"], task_id=task_id, points=points)
    row.add(field)


def highlighter_task(task, row, args, task_id: str):
    fields = HighlightField.unreconciled_list(task, task_id, args)
    for field in fields:
        row.add(field)


def detail_tasks(task: dict, row: Row, strings, task_id: str, name: str):
    """Extract subtasks that are stuffed in a 'detail' field."""
    for detail in task.get("details", []):
        for detail_value in detail.get("value", []):
            try:
                value = detail_value.get("value")
                string = strings[value]
                name2 = f"{name} {string.title}"
                field = SelectField(name=name2, task_id=task_id, value=string.value)
                row.add(field)
            except (KeyError, AttributeError):
                pass


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
        return date_parse(value).strftime("%d-%b-%Y %H:%M:%S")

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


def get_workflow_strings(workflow_csv, workflow_id) -> dict[str, WF_String]:
    """Get strings from the workflow for when they're not in the annotations."""
    if not workflow_csv:
        return {}

    df = pd.read_csv(workflow_csv)
    df = df.loc[df.workflow_id == int(workflow_id), :]
    workflow = df.iloc[-1]  # Get the most recent version

    strings: dict[str, WF_String] = {}
    for key, value in json.loads(workflow["strings"]).items():
        strings[key] = WF_String(value=value, title="")

        # *Sigh* Handle abbreviated string IDs too
        parts = key.split(".")
        match parts:
            case[_, "tools", __, "details", ___, "answers", *____]:
                strings[f"{parts[0]}.{parts[2]}.{parts[4]}.{parts[6]}"] = value

    # Sometimes strings have a 2-level index: level 1 in task field, level 2 in strings
    tasks = json.loads(workflow["tasks"])

    new: dict[str, WF_String] = {}
    for match in parse("$..tools[*].details[*].selects[*]").find(tasks):
        title = match.value["title"]
        for match2 in parse("$.options.'*'[*]").find(match.value):
            label = match2.value['label']
            key = match2.value['value']
            value = strings[label]
            new[key] = WF_String(value=value.value, title=title)

    strings |= new
    return strings
