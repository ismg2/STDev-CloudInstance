"""Diagnostic export utilities for consolidating CSV rows and JSONL logs by run_id."""

import json
import os
from datetime import datetime

import pandas as pd

from config import RESULTS_CSV, RUN_LOGS_JSONL, RESULTS_DIR


def _safe_run_id(run_id: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in run_id)


def export_diagnostic_report(run_id: str, output_dir: str = "") -> dict:
    """Export consolidated report files for one run_id.

    Returns a dict with created paths and counters.
    """
    if not run_id or not run_id.strip():
        raise ValueError("run_id est obligatoire")

    rid = run_id.strip()
    safe = _safe_run_id(rid)
    out_dir = output_dir or os.path.join(RESULTS_DIR, "diagnostics")
    os.makedirs(out_dir, exist_ok=True)

    rows_csv_path = os.path.join(out_dir, f"{safe}_rows.csv")
    events_jsonl_path = os.path.join(out_dir, f"{safe}_events.jsonl")
    summary_json_path = os.path.join(out_dir, f"{safe}_summary.json")

    row_count = 0
    event_count = 0

    # Extract CSV rows
    if os.path.exists(RESULTS_CSV):
        df = pd.read_csv(RESULTS_CSV, delimiter=";", encoding="utf-8")
        if "run_id" in df.columns:
            filtered = df[df["run_id"].astype(str) == rid]
        else:
            filtered = df.iloc[0:0]
        row_count = len(filtered)
        filtered.to_csv(rows_csv_path, sep=";", index=False, encoding="utf-8")
    else:
        pd.DataFrame().to_csv(rows_csv_path, sep=";", index=False, encoding="utf-8")

    # Extract JSONL events
    with open(events_jsonl_path, "w", encoding="utf-8") as out_f:
        if os.path.exists(RUN_LOGS_JSONL):
            with open(RUN_LOGS_JSONL, "r", encoding="utf-8") as in_f:
                for line in in_f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if str(event.get("run_id", "")) == rid:
                        out_f.write(json.dumps(event, ensure_ascii=False) + "\n")
                        event_count += 1

    summary = {
        "run_id": rid,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "rows_csv": rows_csv_path,
        "events_jsonl": events_jsonl_path,
        "csv_rows_count": row_count,
        "events_count": event_count,
    }
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    summary["summary_json"] = summary_json_path
    return summary
