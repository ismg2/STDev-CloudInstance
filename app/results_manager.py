"""Results manager - SQLite primary storage with CSV export compatibility."""

import csv
import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import pandas as pd

from app.config import (
    RESULTS_CSV,
    RESULTS_DB,
    RESULTS_DIR,
    CSV_COLUMNS,
    EXPORT_CSV_ON_APPEND,
)


def ensure_results_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _get_conn() -> sqlite3.Connection:
    ensure_results_dir()
    conn = sqlite3.connect(RESULTS_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def _db_conn():
    conn = _get_conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def ensure_csv_exists():
    """Keep CSV available for compatibility and exports."""
    ensure_results_dir()
    if not os.path.exists(RESULTS_CSV):
        with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(CSV_COLUMNS)
        return

    try:
        df = pd.read_csv(RESULTS_CSV, delimiter=";", encoding="utf-8")
        missing = [col for col in CSV_COLUMNS if col not in df.columns]
        if missing:
            for col in missing:
                df[col] = ""
            df = df[CSV_COLUMNS]
            df.to_csv(RESULTS_CSV, sep=";", index=False, encoding="utf-8")
    except Exception:
        pass


def ensure_db_exists():
    ensure_results_dir()
    with _db_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS benchmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                modele TEXT,
                dossier TEXT,
                type_framework TEXT,
                board TEXT,
                optimization TEXT,
                compression TEXT,
                inference_time_ms TEXT,
                ram_ko TEXT,
                rom_ko TEXT,
                macc TEXT,
                params TEXT,
                accuracy TEXT,
                rmse TEXT,
                mae TEXT,
                l2r TEXT,
                core_version TEXT,
                target TEXT,
                st_neural_art TEXT,
                memory_pool TEXT,
                split_weights TEXT,
                allocate_activations TEXT,
                allocate_states TEXT,
                input_memory_alignment TEXT,
                output_memory_alignment TEXT,
                no_inputs_allocation TEXT,
                no_outputs_allocation TEXT,
                core_command TEXT,
                run_id TEXT,
                benchmark_id TEXT,
                date TEXT,
                status TEXT,
                record_hash TEXT NOT NULL UNIQUE
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT ''
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS benchmark_tags (
                benchmark_row_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                tagged_at TEXT NOT NULL,
                PRIMARY KEY (benchmark_row_id, tag_id),
                FOREIGN KEY (benchmark_row_id) REFERENCES benchmarks(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
            """
        )

        conn.execute("CREATE INDEX IF NOT EXISTS idx_bench_date ON benchmarks(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bench_board ON benchmarks(board)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bench_modele ON benchmarks(modele)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bench_status ON benchmarks(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bench_benchmark_id ON benchmarks(benchmark_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bench_run_id ON benchmarks(run_id)")
        conn.commit()


def _clean_scalar(value):
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return value


def _row_signature(row: dict) -> str:
    run_id = str(row.get("run_id", "") or "").strip()
    benchmark_id = str(row.get("benchmark_id", "") or "").strip()
    if run_id or benchmark_id:
        base = {
            "run_id": run_id,
            "benchmark_id": benchmark_id,
            "modele": str(row.get("modele", "") or ""),
            "board": str(row.get("board", "") or ""),
            "date": str(row.get("date", "") or ""),
        }
    else:
        base = {k: str(row.get(k, "") or "") for k in CSV_COLUMNS}
    payload = json.dumps(base, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _insert_row_sqlite(conn: sqlite3.Connection, row: dict) -> int:
    normalized = {k: _clean_scalar(row.get(k, "")) for k in CSV_COLUMNS}
    if not normalized.get("date"):
        normalized["date"] = _now_str()
    record_hash = _row_signature(normalized)

    run_id = str(normalized.get("run_id", "") or "").strip()
    benchmark_id = str(normalized.get("benchmark_id", "") or "").strip()
    if run_id and benchmark_id:
        cur = conn.execute(
            "SELECT id FROM benchmarks WHERE run_id = ? AND benchmark_id = ? LIMIT 1",
            (run_id, benchmark_id),
        )
        hit = cur.fetchone()
        if hit:
            return int(hit["id"])

    values = [normalized[c] for c in CSV_COLUMNS] + [record_hash]
    conn.execute(
        f"INSERT OR IGNORE INTO benchmarks ({', '.join(CSV_COLUMNS)}, record_hash) VALUES ({', '.join(['?'] * (len(CSV_COLUMNS) + 1))})",
        values,
    )
    cur = conn.execute("SELECT id FROM benchmarks WHERE record_hash = ? LIMIT 1", (record_hash,))
    hit = cur.fetchone()
    return int(hit["id"]) if hit else 0


def migrate_csv_to_sqlite() -> int:
    """Idempotent migration from CSV history to SQLite."""
    ensure_csv_exists()
    ensure_db_exists()
    if not os.path.exists(RESULTS_CSV):
        return 0

    try:
        df = pd.read_csv(RESULTS_CSV, delimiter=";", encoding="utf-8")
    except Exception:
        return 0
    if df.empty:
        return 0

    for col in CSV_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[CSV_COLUMNS]

    inserted = 0
    with _db_conn() as conn:
        for _, row in df.iterrows():
            before = conn.total_changes
            _insert_row_sqlite(conn, row.to_dict())
            inserted += max(0, conn.total_changes - before)
        conn.commit()
    return inserted


def ensure_storage_ready():
    ensure_db_exists()
    ensure_csv_exists()
    migrate_csv_to_sqlite()


def export_results_to_csv(csv_path: str = "") -> str:
    """Export current SQLite contents to CSV file."""
    ensure_storage_ready()
    out_path = csv_path or RESULTS_CSV
    with _db_conn() as conn:
        df = pd.read_sql_query(
            f"SELECT {', '.join(CSV_COLUMNS)} FROM benchmarks ORDER BY date ASC, id ASC",
            conn,
        )
    df.to_csv(out_path, sep=";", index=False, encoding="utf-8")
    return out_path


def append_result(
    model_name, model_dir, type_framework, board,
    optimization, compression,
    inference_time_ms, ram_ko, rom_ko, macc, params,
    accuracy="N/A", rmse="N/A", mae="N/A", l2r="N/A",
    core_version="",
    target="",
    st_neural_art="",
    memory_pool="",
    split_weights="",
    allocate_activations="",
    allocate_states="",
    input_memory_alignment="",
    output_memory_alignment="",
    no_inputs_allocation="",
    no_outputs_allocation="",
    core_command="",
    run_id="",
    benchmark_id="",
    status="OK",
):
    """Append one benchmark result row to SQLite (primary) and optional CSV export."""
    ensure_storage_ready()
    row = {
        "modele": model_name,
        "dossier": model_dir,
        "type_framework": type_framework,
        "board": board,
        "optimization": optimization,
        "compression": compression,
        "inference_time_ms": inference_time_ms,
        "ram_ko": ram_ko,
        "rom_ko": rom_ko,
        "macc": macc,
        "params": params,
        "accuracy": accuracy,
        "rmse": rmse,
        "mae": mae,
        "l2r": l2r,
        "core_version": core_version,
        "target": target,
        "st_neural_art": st_neural_art,
        "memory_pool": memory_pool,
        "split_weights": split_weights,
        "allocate_activations": allocate_activations,
        "allocate_states": allocate_states,
        "input_memory_alignment": input_memory_alignment,
        "output_memory_alignment": output_memory_alignment,
        "no_inputs_allocation": no_inputs_allocation,
        "no_outputs_allocation": no_outputs_allocation,
        "core_command": core_command,
        "run_id": run_id,
        "benchmark_id": benchmark_id,
        "date": _now_str(),
        "status": status,
    }

    with _db_conn() as conn:
        _insert_row_sqlite(conn, row)
        conn.commit()

    if EXPORT_CSV_ON_APPEND:
        export_results_to_csv(RESULTS_CSV)
    print(f"  Resultat sauvegarde -> {RESULTS_DB}")


def _load_results_from_sqlite() -> pd.DataFrame:
    ensure_storage_ready()
    with _db_conn() as conn:
        df = pd.read_sql_query(
            f"SELECT {', '.join(CSV_COLUMNS)} FROM benchmarks ORDER BY date DESC, id DESC",
            conn,
        )
    return df if not df.empty else pd.DataFrame(columns=CSV_COLUMNS)


def load_results() -> pd.DataFrame:
    """Load results from SQLite first, fallback to CSV if needed."""
    try:
        return _load_results_from_sqlite()
    except Exception:
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
        df = df.head(last_n)

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
        df = df[df["board"].astype(str).str.contains(board, case=False, na=False)]
    if model_dir:
        df = df[df["dossier"].astype(str).str.contains(model_dir, case=False, na=False)]
    if optimization:
        df = df[df["optimization"].astype(str).str.contains(optimization, case=False, na=False)]
    return df


def tag_benchmark(identifier: str, tag_name: str = "reference", active: bool = True, deactivate_previous: bool = True) -> bool:
    """Tag benchmark by benchmark_id or run_id."""
    ensure_storage_ready()
    ident = (identifier or "").strip()
    if not ident:
        return False

    with _db_conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM benchmarks
            WHERE benchmark_id = ? OR run_id = ?
            ORDER BY date DESC, id DESC
            LIMIT 1
            """,
            (ident, ident),
        ).fetchone()
        if not row:
            return False

        conn.execute(
            "INSERT OR IGNORE INTO tags(name, description) VALUES (?, ?)",
            (tag_name, "User tag"),
        )
        tag = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,)).fetchone()
        tag_id = int(tag["id"])

        if deactivate_previous and tag_name == "reference":
            conn.execute(
                """
                UPDATE benchmark_tags
                SET is_active = 0
                WHERE tag_id = ? AND benchmark_row_id IN (
                    SELECT id FROM benchmarks
                    WHERE modele = ? AND board = ?
                      AND optimization = ? AND compression = ?
                )
                """,
                (tag_id, row["modele"], row["board"], row["optimization"], row["compression"]),
            )

        conn.execute(
            """
            INSERT INTO benchmark_tags(benchmark_row_id, tag_id, is_active, tagged_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(benchmark_row_id, tag_id)
            DO UPDATE SET is_active = excluded.is_active, tagged_at = excluded.tagged_at
            """,
            (int(row["id"]), tag_id, 1 if active else 0, _now_str()),
        )
        conn.commit()
    return True


def get_active_reference(model_name: str = "", board: str = "") -> dict:
    """Return the latest active reference benchmark matching optional filters."""
    ensure_storage_ready()
    query = (
        "SELECT b.* FROM benchmarks b "
        "JOIN benchmark_tags bt ON bt.benchmark_row_id = b.id "
        "JOIN tags t ON t.id = bt.tag_id "
        "WHERE t.name = 'reference' AND bt.is_active = 1"
    )
    params = []
    if model_name:
        query += " AND b.modele = ?"
        params.append(model_name)
    if board:
        query += " AND b.board = ?"
        params.append(board)
    query += " ORDER BY b.date DESC, b.id DESC LIMIT 1"

    with _db_conn() as conn:
        row = conn.execute(query, params).fetchone()
    return dict(row) if row else {}


def get_version_history(model_name: str, board: str, optimization: str = "", compression: str = "") -> list:
    """Return chronological history for one model+board(+config)."""
    ensure_storage_ready()
    query = "SELECT * FROM benchmarks WHERE modele = ? AND board = ?"
    params = [model_name, board]
    if optimization:
        query += " AND optimization = ?"
        params.append(optimization)
    if compression:
        query += " AND compression = ?"
        params.append(compression)
    query += " ORDER BY date DESC, id DESC"

    with _db_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]
