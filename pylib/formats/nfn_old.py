"""Convert Zooniverse Notes from Nature expedition CSV format to something sane."""
import json
import re
from collections import defaultdict
from collections import namedtuple
from dataclasses import dataclass
from dataclasses import field

import pandas as pd
from dateutil.parser import parse

from .. import util

STARTED_AT = "classification_started_at"
USER_NAME = "user_name"

UNWANTED = " user_id user_ip subject_ids subject_data subject_retired ".split()

WorkflowString = namedtuple("WorkflowString", "value label")


@dataclass
class WorkflowStrings:
    label_strings: dict[str, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )
    value_strings: dict[str, WorkflowString] = field(default_factory=dict)


def read(args):
    """Read and convert the input CSV data."""
    df = pd.read_csv(args.input_file, dtype=str)

    # Workflows must be processed individually
    workflow_id = get_workflow_id(df, args)

    df = df.loc[df.workflow_id == str(workflow_id), :]

    get_nfn_only_defaults(df, args, workflow_id)

    # A hack to workaround crap coming back from Zooniverse
    workflow_strings = get_workflow_strings(args.workflow_csv, workflow_id)

    # Extract the various json blobs
    df, column_types = extract_annotations(df, workflow_strings)
    df = extract_subject_data(df, column_types)
    df = extract_metadata(df)

    # Get the subject_id from the subject_ids list, use the first one
    df[args.group_by] = df.subject_ids.map(lambda x: int(str(x).split(";")[0]))

    # Remove unwanted columns
    unwanted_columns = [c for c in df.columns if c.lower() in UNWANTED]
    df = df.drop(unwanted_columns, axis=1)

    column_types = {k: v for k, v in column_types.items() if k.lower() not in UNWANTED}

    columns_ = column_sort_order(
        column_types, df.columns, args.group_by, args.key_column, args.user_column
    )
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.reindex(columns_, axis="columns").fillna("")
    df = df.sort_values([args.group_by, STARTED_AT])
    df = df.drop_duplicates([args.group_by, USER_NAME], keep="first")
    df = df.groupby(args.group_by)

    return df, column_types


def get_workflow_strings(workflow_csv, workflow_id):
    """Get strings from the workflow when they're not in the annotations."""
    value_strings = {}
    if not workflow_csv:
        return value_strings

    df = pd.read_csv(workflow_csv)
    df = df.loc[df.workflow_id == int(workflow_id), :]
    row = df.iloc[-1]

    strings = {k: v for k, v in json.loads(row["strings"]).items()}

    instructions = {}
    label_strings = defaultdict(list)
    for key, value in strings.items():
        if key.endswith("instruction"):
            parts = key.split(".")
            key = ".".join(parts[:-1])
            value = value.strip()
            instructions[key] = value
            key = ".".join(parts[:-2])
            if key:
                label_strings[key].append(value)

    def _task_dive(node):
        if isinstance(node, dict) and node.get("value"):
            string = strings.get(node.get("label"))
            if string:
                string = string.strip()
                label = node["label"].strip()
                labels = [v for k, v in instructions.items() if label.startswith(k)]
                label = labels[-1] if labels else ""
                value_strings[node["value"]] = WorkflowString(string, label)
        elif isinstance(node, dict):
            for child in node.values():
                _task_dive(child)
        elif isinstance(node, list):
            for child in node:
                _task_dive(child)

    tasks = json.loads(row["tasks"])
    _task_dive(tasks)

    return WorkflowStrings(label_strings=label_strings, value_strings=value_strings)


def get_nfn_only_defaults(df, args, workflow_id):
    workflow_name = ""
    if args.summary:
        workflow_name = get_workflow_name(df)

    if not args.title and args.summary:
        args.title = f'Summary of "{workflow_name}" ({workflow_id})'

    if not args.user_column:
        args.user_column = USER_NAME


def get_workflow_id(df, args):
    """Pull the workflow ID from the data-df if it was not given."""
    if args.workflow_id:
        return args.workflow_id

    workflow_ids = df.workflow_id.unique()

    if len(workflow_ids) > 1:
        util.error_exit(
            "There are multiple workflows in this file. "
            "You must provide a workflow ID as an argument."
        )

    return workflow_ids[0]


def get_workflow_name(df):
    """Extract and format the workflow name from the data df."""
    workflow_name = ""
    try:
        workflow_name = df.workflow_name.iloc[0]
        workflow_name = re.sub(r"^[^_]*_", "", workflow_name)
    except KeyError:
        util.error_exit("Workflow name not found in classifications file.")
    return workflow_name


# #############################################################################
def extract_metadata(df):
    """Extract a few field from the metadata JSON object."""

    def _extract_date(value):
        return parse(value).strftime("%d-%b-%Y %H:%M:%S")

    data = df.metadata.map(json.loads).tolist()
    data = pd.DataFrame(data, index=df.index)

    df[STARTED_AT] = data.started_at.map(_extract_date)

    name = "classification_finished_at"
    df[name] = data.finished_at.map(_extract_date)

    return df.drop(["metadata"], axis=1)


# #############################################################################
def extract_subject_data(df, column_types):
    """Extract subject data from the json object in the subject_data column.

    We prefix the new column names with "subject_" to keep them separate from
    the other data df columns. The subject data json looks like:
        {<subject_id>: {"key_1": "value_1", "key_2": "value_2", ...}}
    """
    data = df.subject_data.map(json.loads).apply(lambda x: list(x.values())[0]).tolist()
    data = pd.DataFrame(data, index=df.index)
    df = df.drop(["subject_data"], axis=1)

    if "retired" in data.columns:
        data = data.drop(["retired"], axis=1)

    if "id" in data.columns:
        data = data.rename(columns={"id": "external_id"})

    columns_ = [re.sub(r"\W+", "_", c) for c in data.columns]
    columns_ = [re.sub(r"^_+|_$", "", c) for c in columns_]
    columns_ = ["subject_" + c for c in columns_]

    columns_ = dict(zip(data.columns, columns_))
    data = data.rename(columns=columns_)

    df = pd.concat([df, data], axis=1)

    # Put the subject columns into the column_types: They're all 'same'
    for name in data.columns:
        column_types[name] = "same"

    return df


# #############################################################################
def extract_annotations(df, workflow_strings):
    """Extract annotations from the json object in the annotations column.

    Annotations are nested json blobs with a WTF format.
    """
    column_types: dict[str, str] = {}

    data = df.annotations.map(json.loads)
    data = [flatten_annotations(a, column_types, workflow_strings) for a in data]
    data = pd.DataFrame(data, index=df.index)

    df = pd.concat([df, data], axis=1)

    column_types, renames = rename_columns(column_types)

    return df.rename(columns=renames).drop(["annotations"], axis=1), column_types


def flatten_annotations(annotations, column_types, workflow_strings):
    """Flatten annotations.

    Annotations are nested json blobs with a peculiar data format. So we flatten it to
    make it easier to reconcile.  We also need to consider that some tasks have the
    same label. In that case we use a tie breaker.
    """
    tasks = {}

    for annotation in annotations:
        flatten_annotation(column_types, tasks, annotation, workflow_strings, "")

    return tasks


def flatten_annotation(column_types, tasks, task, workflow_strings, task_id):
    """Flatten one annotation recursively."""
    task_id = task.get("task", task_id)

    if (
        isinstance(task.get("value"), list)
        and task["value"]
        and isinstance(task["value"][0], str)
    ):
        list_annotation(column_types, tasks, task)
    elif isinstance(task.get("value"), list):
        subtask_annotation(column_types, tasks, task, workflow_strings, task_id)
    elif "select_label" in task:
        select_label_annotation(column_types, tasks, task)
    elif "task_label" in task:
        task_label_annotation(column_types, tasks, task)
    elif "tool_label" in task:
        tool_label_annotation(column_types, tasks, task, workflow_strings, task_id)
    else:
        print(f"Annotation task type not found: {task}")


def list_annotation(column_types, tasks, task):
    """Handle a list of literals annotation."""
    key = unique_name(column_types, task["task_label"])
    values = sorted(task.get("value", ""))
    tasks[key] = " ".join(values)
    column_types[key] = "text"


def subtask_annotation(column_types, tasks, task, workflow_strings, task_id):
    """Handle a task annotation with subtasks."""
    task_id = task.get("task", task_id)
    for subtask in task["value"]:
        flatten_annotation(column_types, tasks, subtask, workflow_strings, task_id)


def select_label_annotation(column_types, tasks, task):
    """Handle a select label task annotation."""
    key = unique_name(column_types, task["select_label"])
    option = task.get("option")
    value = task.get("label", "") if option else task.get("value", "")
    tasks[key] = value
    column_types[key] = "select"


def task_label_annotation(column_types, tasks, task):
    """Handle a task label task annotation."""
    key = unique_name(column_types, task["task_label"])
    tasks[key] = task.get("value", "")
    column_types[key] = "text"


def tool_label_annotation(column_types, tasks, task, workflow_strings, task_id):
    """Handle a tool label task annotation."""
    if task.get("width"):
        label = "{}: box".format(task["tool_label"])
        label = unique_name(column_types, label)
        col_type = "box"
        value = json.dumps(
            {
                "left": round(task["x"]),
                "right": round(task["x"] + task["width"]),
                "top": round(task["y"]),
                "bottom": round(task["y"] + task["height"]),
            }
        )
    elif task.get("x1"):
        label = "{}: line".format(task["tool_label"])
        col_type = "line"
        value = json.dumps(
            {
                "x1": round(task["x1"]),
                "y1": round(task["y1"]),
                "x2": round(task["x2"]),
                "y2": round(task["y2"]),
            }
        )
    else:
        label = "{}: point".format(task["tool_label"])
        value = json.dumps({"x": round(task["x"]), "y": round(task["y"])})
        col_type = "point"

    label = unique_name(column_types, label)
    tasks[label] = value
    column_types[label] = col_type

    if task.get("tool_label") and task.get("details"):
        candidates = [
            v
            for k, v in workflow_strings.label_strings.items()
            if k.startswith(task_id) and k.endswith("details")
        ]
        labels = candidates[-1] if candidates else []
        for i, detail in enumerate(task["details"]):
            outer_value = detail["value"]
            type_ = "select"
            if isinstance(outer_value, list):
                values = []
                for item in outer_value:
                    if item["value"] in workflow_strings.value_strings:
                        value, label = workflow_strings.value_strings[item["value"]]
                        values.append(value)
                    else:
                        value = item["value"]
                        label = item.get("label", "unknown")
                        values.append(value)
                value = ",".join(v for v in values if v)
            else:
                value = outer_value
                label = labels[i] if i < len(labels) else "unknown"
                type_ = "text"
            label = f"{task['tool_label']}.{label}"
            label = unique_name(column_types, label)
            tasks[label] = value
            column_types[label] = type_


# #############################################################################
def unique_name(columns_types, name):
    """Make the column name unique."""
    name = name.strip()
    base = name
    i = 1
    while name in columns_types.columns:
        i += 1
        name = f"{base} #{i}"
    return name


def column_sort_order(
    columns_types, df_columns: list[str], group_by: str, key_column: str, user_column=""
):
    """Get the order of columns for a data frame."""
    sort_order = [group_by, key_column]
    if user_column:
        sort_order.append(user_column)
    sort_order += list(columns_types.keys())
    sort_order += [c for c in df_columns if c not in sort_order]
    return sort_order


def rename_columns(columns_types):
    """Rename columns to use a "#1" suffix if there exists a "#2" suffix."""
    renames = {}

    for name in columns_types.keys():
        old_name = name[:-3]
        if name.endswith("#2") and old_name in columns_types:
            renames[old_name] = old_name + " #1"

    new_columns: dict[str, str] = {}
    for name, type_ in columns_types.items():
        new_name = renames.get(name, name)
        new_columns[new_name] = type_

    return new_columns, renames
