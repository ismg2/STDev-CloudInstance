"""Results manager — CSV storage and querying of benchmark results."""

import csv
import os
from datetime import datetime

import pandas as pd

from config import RESULTS_CSV, RESULTS_DIR, CSV_COLUMNS


def ensure_results_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)


def ensure_csv_exists():
    ensure_results_dir()
    if not os.path.exists(RESULTS_CSV):
        with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(CSV_COLUMNS)


def append_result(
    model_name, model_dir, type_framework, board,
    optimization, compression,
    inference_time_ms, ram_ko, rom_ko, macc, params,
    accuracy="N/A", rmse="N/A", mae="N/A", l2r="N/A",
    status="OK",
):
    """Append one benchmark result row to the CSV."""
    ensure_csv_exists()
    row = [
        model_name,
        model_dir,
        type_framework,
        board,
        optimization,
        compression,
        inference_time_ms,
        ram_ko,
        rom_ko,
        macc,
        params,
        accuracy,
        rmse,
        mae,
        l2r,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        status,
    ]
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(row)
    print(f"  Resultat sauvegarde → {RESULTS_CSV}")


def load_results() -> pd.DataFrame:
    """Load all results as a DataFrame."""
    ensure_csv_exists()
    try:
        df = pd.read_csv(RESULTS_CSV, delimiter=";", encoding="utf-8")
        return df if not df.empty else pd.DataFrame(columns=CSV_COLUMNS)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame(columns=CSV_COLUMNS)


def display_results(df=None, last_n=None):
    """Print results as a formatted table in the terminal."""
    if df is None:
        df = load_results()
    if df.empty:
        print("\n  Aucun resultat disponible.")
        return
    if last_n:
        df = df.tail(last_n)

    print(f"\n{'='*110}")
    print(f"  RESULTATS ({len(df)} entrees)")
    print(f"{'='*110}")
    fmt = "  {:<22} {:<20} {:<12} {:<10} {:<10} {:<12} {:<10} {:<8}"
    print(fmt.format("Modele", "Board", "Inference(ms)", "RAM(Ko)", "ROM(Ko)", "MACC", "Accuracy", "Optim"))
    print(f"  {'-'*105}")
    for _, row in df.iterrows():
        acc = row.get("accuracy", "N/A")
        acc_str = f"{acc}%" if acc not in ("N/A", "", None) else "N/A"
        print(fmt.format(
            str(row.get("modele", ""))[:21],
            str(row.get("board", ""))[:19],
            str(row.get("inference_time_ms", "N/A"))[:11],
            str(row.get("ram_ko", "N/A"))[:9],
            str(row.get("rom_ko", "N/A"))[:9],
            str(row.get("macc", "N/A"))[:11],
            acc_str[:9],
            str(row.get("optimization", "N/A"))[:7],
        ))
    print()


def filter_results(board=None, model_dir=None, optimization=None) -> pd.DataFrame:
    df = load_results()
    if df.empty:
        return df
    if board:
        df = df[df["board"].str.contains(board, case=False, na=False)]
    if model_dir:
        df = df[df["dossier"].str.contains(model_dir, case=False, na=False)]
    if optimization:
        df = df[df["optimization"].str.contains(optimization, case=False, na=False)]
    return df
