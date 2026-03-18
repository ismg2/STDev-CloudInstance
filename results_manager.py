"""Results manager - handles CSV storage and querying of benchmark results."""

import csv
import os
from datetime import datetime

import pandas as pd

from config import RESULTS_CSV, RESULTS_DIR, CSV_COLUMNS


def ensure_results_dir():
    """Create results directory if it doesn't exist."""
    os.makedirs(RESULTS_DIR, exist_ok=True)


def ensure_csv_exists():
    """Create CSV file with headers if it doesn't exist."""
    ensure_results_dir()
    if not os.path.exists(RESULTS_CSV):
        with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(CSV_COLUMNS)


def append_result(model_name, model_dir, board, inference_time_ms,
                  ram_ko, rom_ko, macc, precision="N/A", status="OK"):
    """Append a single benchmark result to the CSV.

    Args:
        model_name: Model filename.
        model_dir: Relative directory of the model.
        board: Target board name.
        inference_time_ms: Inference time in milliseconds.
        ram_ko: RAM usage in KB.
        rom_ko: ROM/Flash usage in KB.
        macc: Number of MACC operations.
        precision: Model precision/accuracy if available.
        status: Result status (OK, ERROR, etc).
    """
    ensure_csv_exists()
    row = [
        model_name,
        model_dir,
        board,
        inference_time_ms,
        ram_ko,
        rom_ko,
        macc,
        precision,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        status,
    ]
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(row)
    print(f"  Resultat sauvegarde dans {RESULTS_CSV}")


def load_results():
    """Load all results from CSV as a pandas DataFrame.

    Returns:
        pd.DataFrame: All benchmark results, or empty DataFrame if no results.
    """
    ensure_csv_exists()
    try:
        df = pd.read_csv(RESULTS_CSV, delimiter=";", encoding="utf-8")
        if df.empty:
            return pd.DataFrame(columns=CSV_COLUMNS)
        return df
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return pd.DataFrame(columns=CSV_COLUMNS)


def display_results(df=None, last_n=None):
    """Display results in a formatted table on the terminal.

    Args:
        df: DataFrame to display. Loads from CSV if None.
        last_n: Show only the last N results.
    """
    if df is None:
        df = load_results()
    if df.empty:
        print("\n  Aucun resultat disponible.")
        return

    if last_n:
        df = df.tail(last_n)

    print(f"\n{'='*100}")
    print(f"  RESULTATS DE BENCHMARK ({len(df)} entrees)")
    print(f"{'='*100}")

    # Format for terminal display
    fmt = "  {:<25} {:<20} {:<12} {:<10} {:<10} {:<12} {:<10}"
    print(fmt.format("Modele", "Board", "Inference(ms)", "RAM(Ko)", "ROM(Ko)", "MACC", "Precision"))
    print(f"  {'-'*95}")

    for _, row in df.iterrows():
        print(fmt.format(
            str(row.get("modele", ""))[:24],
            str(row.get("board", ""))[:19],
            str(row.get("inference_time_ms", "N/A"))[:11],
            str(row.get("ram_ko", "N/A"))[:9],
            str(row.get("rom_ko", "N/A"))[:9],
            str(row.get("macc", "N/A"))[:11],
            str(row.get("precision", "N/A"))[:9],
        ))
    print()


def filter_results(board=None, model_dir=None):
    """Filter results by board and/or model directory.

    Returns:
        pd.DataFrame: Filtered results.
    """
    df = load_results()
    if df.empty:
        return df
    if board:
        df = df[df["board"].str.contains(board, case=False, na=False)]
    if model_dir:
        df = df[df["dossier"].str.contains(model_dir, case=False, na=False)]
    return df
