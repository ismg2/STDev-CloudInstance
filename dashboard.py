"""Visualization dashboard for benchmark results.

Uses matplotlib for charts. Can be launched standalone or from the CLI.
"""

import sys

import matplotlib.pyplot as plt
import pandas as pd

from results_manager import load_results, filter_results


def _check_data(df):
    """Check if we have data to plot."""
    if df.empty:
        print("\n  Aucun resultat a visualiser.")
        print("  Lancez d'abord un benchmark via le menu principal.")
        return False
    return True


def _to_numeric(series):
    """Convert a series to numeric, coercing errors to NaN."""
    return pd.to_numeric(series, errors="coerce")


def plot_inference_time(df=None, board_filter=None):
    """Bar chart of inference time per model."""
    if df is None:
        df = filter_results(board=board_filter) if board_filter else load_results()
    if not _check_data(df):
        return

    df = df.copy()
    df["inference_time_ms"] = _to_numeric(df["inference_time_ms"])
    df = df.dropna(subset=["inference_time_ms"])
    if df.empty:
        print("  Pas de donnees d'inference time valides.")
        return

    labels = df["modele"] + "\n(" + df["board"] + ")"

    fig, ax = plt.subplots(figsize=(max(8, len(df) * 1.2), 6))
    bars = ax.bar(range(len(df)), df["inference_time_ms"], color="#2196F3", edgecolor="white")
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Temps d'inference (ms)")
    ax.set_title("Temps d'inference par modele")
    ax.grid(axis="y", alpha=0.3)

    # Add value labels on bars
    for bar, val in zip(bars, df["inference_time_ms"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:.2f}", ha="center", va="bottom", fontsize=7)

    plt.tight_layout()
    plt.show()


def plot_memory(df=None, board_filter=None):
    """Grouped bar chart of RAM and ROM usage."""
    if df is None:
        df = filter_results(board=board_filter) if board_filter else load_results()
    if not _check_data(df):
        return

    df = df.copy()
    df["ram_ko"] = _to_numeric(df["ram_ko"])
    df["rom_ko"] = _to_numeric(df["rom_ko"])
    df = df.dropna(subset=["ram_ko", "rom_ko"], how="all")
    if df.empty:
        print("  Pas de donnees memoire valides.")
        return

    labels = df["modele"].tolist()
    x = range(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(max(8, len(df) * 1.5), 6))
    ram_vals = df["ram_ko"].fillna(0).tolist()
    rom_vals = df["rom_ko"].fillna(0).tolist()

    bars1 = ax.bar([i - width / 2 for i in x], ram_vals, width, label="RAM (Ko)", color="#4CAF50")
    bars2 = ax.bar([i + width / 2 for i in x], rom_vals, width, label="ROM (Ko)", color="#FF9800")

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Taille (Ko)")
    ax.set_title("Utilisation memoire par modele")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.show()


def plot_precision(df=None):
    """Bar chart of model precision/accuracy if available."""
    if df is None:
        df = load_results()
    if not _check_data(df):
        return

    df = df.copy()
    df["precision"] = _to_numeric(df["precision"])
    df = df.dropna(subset=["precision"])
    if df.empty:
        print("  Pas de donnees de precision disponibles.")
        return

    labels = df["modele"].tolist()

    fig, ax = plt.subplots(figsize=(max(8, len(df) * 1.2), 6))
    bars = ax.bar(range(len(df)), df["precision"], color="#9C27B0", edgecolor="white")
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Precision (%)")
    ax.set_title("Precision des modeles")
    ax.set_ylim(0, 105)
    ax.grid(axis="y", alpha=0.3)

    for bar, val in zip(bars, df["precision"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:.1f}%", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    plt.show()


def plot_comparison_dashboard(df=None, board_filter=None):
    """Full comparison dashboard with all metrics in subplots."""
    if df is None:
        df = filter_results(board=board_filter) if board_filter else load_results()
    if not _check_data(df):
        return

    df = df.copy()
    df["inference_time_ms"] = _to_numeric(df["inference_time_ms"])
    df["ram_ko"] = _to_numeric(df["ram_ko"])
    df["rom_ko"] = _to_numeric(df["rom_ko"])
    df["precision"] = _to_numeric(df["precision"])

    has_inference = df["inference_time_ms"].notna().any()
    has_memory = df["ram_ko"].notna().any() or df["rom_ko"].notna().any()
    has_precision = df["precision"].notna().any()

    n_plots = sum([has_inference, has_memory, has_precision])
    if n_plots == 0:
        print("  Aucune donnee numerique a afficher.")
        return

    fig, axes = plt.subplots(1, n_plots, figsize=(6 * n_plots, 6))
    if n_plots == 1:
        axes = [axes]

    plot_idx = 0
    labels = df["modele"].tolist()
    x = range(len(labels))

    if has_inference:
        ax = axes[plot_idx]
        vals = df["inference_time_ms"].fillna(0)
        ax.bar(x, vals, color="#2196F3")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        ax.set_ylabel("ms")
        ax.set_title("Inference Time")
        ax.grid(axis="y", alpha=0.3)
        plot_idx += 1

    if has_memory:
        ax = axes[plot_idx]
        width = 0.35
        ax.bar([i - width / 2 for i in x], df["ram_ko"].fillna(0), width, label="RAM", color="#4CAF50")
        ax.bar([i + width / 2 for i in x], df["rom_ko"].fillna(0), width, label="ROM", color="#FF9800")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        ax.set_ylabel("Ko")
        ax.set_title("Memoire")
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)
        plot_idx += 1

    if has_precision:
        ax = axes[plot_idx]
        ax.bar(x, df["precision"].fillna(0), color="#9C27B0")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
        ax.set_ylabel("%")
        ax.set_title("Precision")
        ax.set_ylim(0, 105)
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle("Dashboard Comparatif des Modeles", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.show()


def interactive_dashboard():
    """Interactive menu for visualization options."""
    while True:
        print(f"\n{'='*50}")
        print("  DASHBOARD DE VISUALISATION")
        print(f"{'='*50}")
        print("  [1] Temps d'inference (barres)")
        print("  [2] Utilisation memoire (RAM/ROM)")
        print("  [3] Precision des modeles")
        print("  [4] Dashboard complet (tous les graphiques)")
        print("  [5] Filtrer par board")
        print("  [R] Retour au menu principal")

        choice = input("\n  Choix > ").strip().upper()

        if choice == "R":
            return
        elif choice == "1":
            plot_inference_time()
        elif choice == "2":
            plot_memory()
        elif choice == "3":
            plot_precision()
        elif choice == "4":
            plot_comparison_dashboard()
        elif choice == "5":
            board = input("  Nom du board (ou partie du nom) > ").strip()
            if board:
                plot_comparison_dashboard(board_filter=board)
        else:
            print("  Choix invalide.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--board":
        board = sys.argv[2] if len(sys.argv) > 2 else None
        plot_comparison_dashboard(board_filter=board)
    else:
        interactive_dashboard()
