"""Core orchestration logic for label reconciliation, including a DataFrame-first API."""

from __future__ import annotations

import argparse
import os
import tempfile
import warnings
import zipfile
import json
from os.path import basename
from typing import Optional, Tuple, Union, Dict, Iterable

import pandas as pd

from . import summary, utils
from .table import Table

VERSION = "0.8.4"


# --------------------------- Helpers --------------------------- #
def _table_to_dataframe(tbl: Table, args=None) -> pd.DataFrame:
    if args is not None and hasattr(tbl, "to_df"):
        try:
            return tbl.to_df(args, add_note=False)
        except TypeError:
            return tbl.to_df(args)
    if hasattr(tbl, "to_records"):
        return pd.DataFrame(tbl.to_records(add_note=False))
    if hasattr(tbl, "to_pandas") and callable(getattr(tbl, "to_pandas")):
        return tbl.to_pandas()
    if hasattr(tbl, "dataframe"):
        return getattr(tbl, "dataframe")
    try:
        return pd.DataFrame(tbl)
    except Exception as exc:
        raise TypeError(
            "Cannot convert Table to pandas DataFrame. "
            "Implement Table.to_df(args) or Table.to_records()."
        ) from exc


def _table_to_json(tbl: Table, args=None, *, add_note: bool = False) -> list[dict]:
    """Return a list of row dicts suitable for json.dumps()."""
    if hasattr(tbl, "to_records"):
        return tbl.to_records(add_note=add_note)
    # fallback via DataFrame if needed
    if args is not None and hasattr(tbl, "to_df"):
        df = tbl.to_df(args, add_note=add_note)
        return df.to_dict(orient="records")
    raise TypeError("Table lacks to_records()/to_df(); cannot convert to JSON.")


def _normalize_column_types(
    column_types: Optional[Union[Dict[str, str], Iterable[str]]]
) -> Optional[Iterable[str]]:
    """
    Accept either:
      - dict like {"foo": "select", "bar": "text"}  -> ["foo:select,bar:text"]
      - iterable of strings already in "col:type" or "col:type,col2:type2" form
    Returns a list to match argparse 'append' behavior (could be None).
    """
    if column_types is None:
        return None
    if isinstance(column_types, dict):
        joined = ",".join(f"{k}:{v}" for k, v in column_types.items())
        return [joined]
    return list(column_types)


def zip_outputs(
    *,
    zip_path: Optional[str],
    unreconciled_path: Optional[str],
    reconciled_path: Optional[str],
    summary_path: Optional[str],
    keep_originals: bool = False,
) -> None:
    """Zip output files if requested."""
    if not zip_path:
        return

    members = [p for p in (unreconciled_path, reconciled_path, summary_path) if p]
    if not members:
        return

    with zipfile.ZipFile(zip_path, mode="w") as zippy:
        for path in members:
            if os.path.exists(path):
                zippy.write(path, arcname=basename(path), compress_type=zipfile.ZIP_DEFLATED)

    if not keep_originals:
        for path in members:
            if path and os.path.exists(path):
                os.remove(path)


# --------------------------- File-based API (used by CLI) --------------------------- #
def read_unreconciled(args) -> Table:
    formats = utils.get_plugins("formats")
    return formats[args.format].read(args)


def write_unreconciled(args, unreconciled: Table) -> None:
    if getattr(args, "unreconciled", None):
        unreconciled.to_csv(args, args.unreconciled)


def reconcile_data(args, unreconciled: Table) -> Table:
    return unreconciled.reconcile(args)


def write_reconciled(args, reconciled: Table) -> None:
    if getattr(args, "reconciled", None):
        reconciled.to_csv(args, args.reconciled, getattr(args, "explanations", False))


def write_summary(args, unreconciled: Table, reconciled: Table) -> None:
    if getattr(args, "summary", None):
        summary.report(args, unreconciled, reconciled)


def run(args, return_summary = False) -> dict:
    """Programmatic entry point (file-based). Returns dict with Table objects."""
    unreconciled: Table = read_unreconciled(args)

    if len(unreconciled) == 0:
        utils.error_exit(f"Workflow {args.workflow_id} has no data.")

    write_unreconciled(args, unreconciled)

    reconciled = None
    needs_reconcile = bool(
        getattr(args, "reconciled", None)
        or getattr(args, "summary", None)
        or getattr(args, "_force_reconcile", False)
    )
    if needs_reconcile:
        reconciled = reconcile_data(args, unreconciled)
        write_reconciled(args, reconciled)
        write_summary(args, unreconciled, reconciled)

    zip_arg = getattr(args, "zip", None) or getattr(args, "zip_keep", None)
    if zip_arg:
        zip_outputs(
            zip_path=zip_arg,
            unreconciled_path=getattr(args, "unreconciled", None),
            reconciled_path=getattr(args, "reconciled", None),
            summary_path=getattr(args, "summary", None),
            keep_originals=bool(getattr(args, "zip_keep", None)),
        )

    if return_summary:
        summary_path = getattr(args, "summary", None)
        if getattr(args, "return_summary_html", False):
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    summary_html = f.read()
            except Exception:
                summary_html = None
    else:
        summary_html = None

    return {"unreconciled": unreconciled, "reconciled": reconciled, "summary_html": summary_html}

def _build_args(
    *,
    input_path: str,
    fmt_key: str,                        # e.g., "csv_format", "json_format", "nfn_format"
    column_types,
    group_by: str,
    workflow_name,
    workflow_id,
    fuzzy_ratio_threshold: int,
    fuzzy_set_threshold: int,
    join_distance: int,
    page_size: int,
    no_summary_detail: bool,
    explanations: bool,
    workflow_csv: str,
) -> argparse.Namespace:
    """Create the argparse-like Namespace used by the pipeline."""
    args = argparse.Namespace(
        input_file=input_path,
        unreconciled=None,
        reconciled=None,
        summary=None,
        explanations=bool(explanations),
        zip=None,
        zip_keep=None,
        workflow_name=workflow_name,
        workflow_id=workflow_id,
        fuzzy_ratio_threshold=int(fuzzy_ratio_threshold),
        fuzzy_set_threshold=int(fuzzy_set_threshold),
        join_distance=int(join_distance),
        workflow_csv=str(workflow_csv or ""),
        format=fmt_key,
        column_types=_normalize_column_types(column_types),
        group_by=str(group_by),
        page_size=int(page_size),
        no_summary_detail=bool(no_summary_detail),
        row_key="classification_id",
        user_column="user_name",
        max_transcriptions=50,
    )
    setattr(args, "_force_reconcile", True)
    return args


def _validate_args(args: argparse.Namespace, *, format_choice: str) -> None:
    """Common validation mirroring the CLI behavior."""
    if args.fuzzy_ratio_threshold < 0 or args.fuzzy_ratio_threshold > 100:
        utils.error_exit("--fuzzy-ratio-threshold must be between 0 and 100.")
    if args.fuzzy_set_threshold < 0 or args.fuzzy_set_threshold > 100:
        utils.error_exit("--fuzzy-set-threshold must be between 0 and 100.")

    # Warnings depending on plugin
    if format_choice == "json" and not args.column_types:
        warnings.warn(
            "No column_types provided for JSON format. Default field type is NoOp; "
            "reconciliation may not change fields as expected."
        )
    if format_choice == "nfn" and args.column_types:
        warnings.warn("Column types are ignored for 'nfn' format.")


def _run_with_input_path(
    *,
    input_path: str,
    format_choice: str,  # "csv" | "json" | "nfn"
    column_types=None,
    group_by="subject_id",
    workflow_name=None,
    workflow_id=None,
    fuzzy_ratio_threshold=90,
    fuzzy_set_threshold=50,
    join_distance=6,
    page_size=20,
    no_summary_detail=False,
    return_summary=False,
    explanations=False,
    workflow_csv="",
) -> tuple[dict, argparse.Namespace]:
    """Build args, validate, run pipeline, return (out_tables, args)."""
    fmt_key = f"{format_choice}_format"
    args = _build_args(
        input_path=input_path,
        fmt_key=fmt_key,
        column_types=column_types,
        group_by=group_by,
        workflow_name=workflow_name,
        workflow_id=workflow_id,
        fuzzy_ratio_threshold=fuzzy_ratio_threshold,
        fuzzy_set_threshold=fuzzy_set_threshold,
        join_distance=join_distance,
        page_size=page_size,
        no_summary_detail=no_summary_detail,
        explanations=explanations,
        workflow_csv=workflow_csv,
    )
    _validate_args(args, format_choice=format_choice)
    return run(args, return_summary), args


def _materialize_json_input(data: Union[str, bytes, dict, list]) -> tuple[str, bool]:
    """Return a file path containing JSON and whether we should delete it afterwards."""
    # If it's an existing file path, use it directly
    if isinstance(data, str) and os.path.exists(data):
        return data, False

    # Otherwise, write to a temp file
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_in:
        tmp_path = tmp_in.name
    if isinstance(data, (dict, list)):
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    elif isinstance(data, str):
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(data)
    elif isinstance(data, bytes):
        with open(tmp_path, "wb") as f:
            f.write(data)
    else:
        raise TypeError("data must be a dict/list JSON object, JSON string/bytes, or a path str.")
    return tmp_path, True


def _materialize_dataframe_input(df: pd.DataFrame) -> str:
    """Write DataFrame to a temp CSV and return its path."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_in:
        tmp_path = tmp_in.name
    df.to_csv(tmp_path, index=False)
    return tmp_path



def run_on_dataframe(
    df: pd.DataFrame,
    *,
    column_types: Optional[Union[Dict[str, str], Iterable[str]]] = None,
    format_choice = "csv",
    group_by: str = "subject_id",
    workflow_name: Optional[str] = None,
    workflow_id: Optional[int] = None,
    fuzzy_ratio_threshold: int = 90,
    fuzzy_set_threshold: int = 50,
    join_distance: int = 6,
    page_size: int = 20,
    no_summary_detail: bool = False,
    return_summary: bool = False,
    explanations: bool = False,
    workflow_csv: str = "",
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    """Run reconciliation from a pandas DataFrame and return DataFrames."""
    tmp_in_path = _materialize_dataframe_input(df)
    try:
        out, args = _run_with_input_path(
            input_path=tmp_in_path,
            format_choice=format_choice,
            column_types=column_types,
            group_by=group_by,
            workflow_name=workflow_name,
            workflow_id=workflow_id,
            fuzzy_ratio_threshold=fuzzy_ratio_threshold,
            fuzzy_set_threshold=fuzzy_set_threshold,
            join_distance=join_distance,
            page_size=page_size,
            no_summary_detail=no_summary_detail,
            return_summary= return_summary,
            explanations=explanations,
            workflow_csv=workflow_csv,
        )
        unreconciled_tbl = out.get("unreconciled")
        reconciled_tbl = out.get("reconciled")
        summary_html = out.get("summary_html")
        unrec_df = _table_to_dataframe(unreconciled_tbl, args) if unreconciled_tbl is not None else None
        rec_df   = _table_to_dataframe(reconciled_tbl,    args) if reconciled_tbl is not None else None
        return unrec_df, rec_df, summary_html
    finally:
        try:
            os.remove(tmp_in_path)
        except Exception:
            pass
