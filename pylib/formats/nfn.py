import json
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field

import pandas as pd
from dateutil.parser import parse

from pylib.utils import error_exit


@dataclass
class WorkflowStrings:
    label_strings: dict[str, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )
    value_strings: dict[str, dict[str, str]] = field(default_factory=dict)


# #####################################################################################
def read(args):
    """Read and convert the input CSV data."""
    df = pd.read_csv(args.input_file, dtype=str)

    # Get the classifications for the workflow
    args.workflow_id = get_workflow_id(args, df)
    df = df.loc[df.workflow_id == str(args.workflow_id), :].fillna("")
    raw_records = df.to_dict("records")

    # A hack to workaround coded values returned from Zooniverse
    workflow_strings = get_workflow_strings(args.workflow_csv, args.workflow_id)

    # Extract the various json blobs
    data = []
    for raw_row in raw_records:
        row = {
            "subject_id": raw_row["subject_ids"].split(",", maxsplit=1)[0],
            "classification_id": raw_row["classification_id"],
            "user_name": raw_row.get("user_name", ""),
        }
        extract_annotations(raw_row, row, workflow_strings)
        extract_subject_data(raw_row, row)
        extract_metadata(raw_row, row)
        extract_misc_data(raw_row, row)

        data.append(row)

    data = sorted(data, key=lambda d: (d["subject_id"], d["classification_id"]))
    df = pd.DataFrame(data)

    return df


# #############################################################################
def extract_annotations(raw_row: dict, row: dict, workflow_strings: WorkflowStrings):
    """Extract annotations from the json object in the annotations column.

    Annotations are nested json blobs with a WTF format. Part of the WTF is that each
    record can have a different format. It all starts with a list of annotations.
    """
    for anno in json.loads(raw_row["annotations"]):
        flatten_annotation(anno, row, workflow_strings)


def flatten_annotation(
    anno: dict, row: dict, workflow_strings: WorkflowStrings, anno_id: str = ""
):
    """Flatten one annotation recursively."""
    anno_id = anno.get("task", anno_id)

    match anno:
        case {"value": [str(), *__], **___}:
            list_annotation(anno, row, anno_id)
        case {"value": list(), **__}:
            subtask_annotation(anno, row, workflow_strings, anno_id)
        case {"select_label": _, **__}:
            select_label_annotation(anno, row, anno_id)
        case {"task_label": _, **__}:
            task_label_annotation(anno, row, anno_id)
        case {"tool_label": _, "width": __, **___}:
            box_annotation(anno, row, anno_id)
        case {"tool_label": _, "x1": __, **___}:
            line_annotation(anno, row, anno_id)
        case {"tool_label": _, "x": __, **___}:
            point_annotation(anno, row, anno_id)
        case {"tool_label": _, "details": __, **___}:
            workflow_annotation(anno, row, workflow_strings, anno_id)
        case _:
            print(f"Annotation type not found: {anno}")


def list_annotation(anno, row, anno_id):
    label = column_name(anno_id, anno["task_label"])
    values = sorted(anno.get("value", ""))
    row[label] = " ".join(values)


def subtask_annotation(anno, row, workflow_strings, anno_id):
    """Handle an annotation with subtasks."""
    anno_id = anno.get("task", anno_id)
    for subtask in anno["value"]:
        flatten_annotation(subtask, row, workflow_strings, anno_id)


def select_label_annotation(anno, row, anno_id):
    label = column_name(anno_id, anno["select_label"])
    option = anno.get("option")
    value = anno.get("label", "") if option else anno.get("value", "")
    row[label] = value


def task_label_annotation(anno, row, anno_id):
    label = column_name(anno_id, anno["task_label"])
    row[label] = anno.get("value", "")


def box_annotation(anno, row, anno_id):
    label = column_name(anno_id, anno["tool_label"])
    row[f"{label}: left"] = round(anno["x"])
    row[f"{label}: right"] = round(anno["x"] + anno["width"])
    row[f"{label}: top"] = round(anno["y"])
    row[f"{label}: bottom"] = round(anno["y"] + anno["height"])


def line_annotation(anno, row, anno_id):
    label = column_name(anno_id, anno["tool_label"])
    row[f"{label}: x1"] = round(anno["x1"])
    row[f"{label}: y1"] = round(anno["y1"])
    row[f"{label}: x2"] = round(anno["x2"])
    row[f"{label}: y2"] = round(anno["y2"])


def point_annotation(anno, row, anno_id):
    label = column_name(anno_id, anno["tool_label"])
    row[f"{label}: x"] = round(anno["x"])
    row[f"{label}: y"] = round(anno["y"])


def workflow_annotation(anno, row, workflow_strings, anno_id):
    """Get the value of an annotation from workflow data.

    We are trying to match a coded value (UUID-like) with strings in the workflow
    description.The field may be a text value or a (multi-)select value.
    """
    label = "unknown"

    # Get all possible strings for the annotation
    values = []
    for key, value in workflow_strings.label_strings.items():
        if key.startswith(anno_id) and key.endswith("details"):
            values.append(value)
    labels = values[-1] if values else []

    # Loop thru the UUID values
    for i, detail in enumerate(anno["details"]):
        outer_value = detail["value"]

        # If it's a list then we have a (multi-)select value
        if isinstance(outer_value, list):
            values = []

            for item in outer_value:
                # We found the workflow string for the UUID
                if item["value"] in workflow_strings.value_strings:
                    value, label = workflow_strings.value_strings[item["value"]]
                    values.append(value)

                # Paranoia: Cannot find string in workflow
                else:
                    value = item["value"]
                    label = item.get("label", "unknown")
                    values.append(value)

            value = ",".join(v for v in values if v)

        # It's a single text value
        else:
            value = outer_value
            label = labels[i] if i < len(labels) else "unknown"

        # Now we can use the reconstructed annotation
        label = column_name(anno_id, f"{anno['tool_label']}.{label}")
        row[label] = value


def column_name(anno_id, name):
    """Make the column name unique."""
    return f"#{anno_id.removeprefix('T')} {name.strip()}"


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
            if key2 != "retired" and key2 not in row:
                row[key2] = val2


# #############################################################################
def extract_metadata(raw_row, row):
    """Extract a few field from the metadata JSON object."""
    annos = json.loads(raw_row["metadata"])

    def _extract_date(value):
        return parse(value).strftime("%d-%b-%Y %H:%M:%S")

    row["classification_started_at"] = _extract_date(annos["started_at"])
    row["classification_finished_at"] = _extract_date(annos["finished_at"])


# #############################################################################
def extract_misc_data(raw_row, row):
    wanted = """ gold_standard expert
        workflow_id workflow_name workflow_version """.split()
    for key in wanted:
        if value := raw_row.get(key) and key not in row:
            row[key] = value


# #############################################################################
def get_workflow_id(args, df):
    """Pull the workflow ID from the data frame if it was not given."""
    if args.workflow_id:
        return args.workflow_id

    workflow_ids = df.workflow_id.unique()

    if len(workflow_ids) > 1:
        error_exit(
            "There are multiple workflows in this file. "
            "You must provide a workflow ID as an argument."
        )

    return workflow_ids[0]


def get_workflow_strings(workflow_csv, workflow_id):
    """Get strings from the workflow for when they're not in the annotations."""
    value_strings = {}
    if not workflow_csv:
        return value_strings

    df = pd.read_csv(workflow_csv)
    df = df.loc[df.workflow_id == int(workflow_id), :]
    row = df.iloc[-1]

    strings = json.loads(row["strings"]).items()

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
                value_strings[node["value"]] = {string: label}
        elif isinstance(node, dict):
            for child in node.values():
                _task_dive(child)
        elif isinstance(node, list):
            for child in node:
                _task_dive(child)

    annos = json.loads(row["tasks"])
    _task_dive(annos)

    return WorkflowStrings(label_strings=label_strings, value_strings=value_strings)
