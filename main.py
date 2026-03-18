#!/usr/bin/env python3
"""CLI Model Zoo Benchmark — ST Edge AI Developer Cloud.

Script interactif en ligne de commande pour benchmarker des modèles AI
sur des boards STM32 réelles via l'API REST ST Edge AI Developer Cloud.

ST Edge AI Core 4.0 supported:
  Frameworks : keras (.h5/.keras), tflite (.tflite), onnx (.onnx)
  Optimization: balanced | ram | time | size
  Compression : none | lossless | low | medium | high

Usage:
  python main.py                  → Menu interactif guidé
  python main.py --benchmark      → Lancer un benchmark
  python main.py --results        → Afficher les résultats
  python main.py --visualize      → Dashboard graphique
  python main.py --models         → Lister les modèles
  python main.py --help           → Aide
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    MODELS_DIR, RESULTS_DIR,
    OPTIMIZATION_OPTIONS, OPTIMIZATION_DEFAULT,
    COMPRESSION_OPTIONS, COMPRESSION_DEFAULT,
)
from model_discovery import interactive_model_selection, scan_models
from results_manager import (
    append_result, display_results, load_results, filter_results, ensure_csv_exists,
)
from dashboard import interactive_dashboard, plot_comparison_dashboard

# Fallback board list if cloud API is unreachable at board selection time
AVAILABLE_BOARDS = [
    "STM32H747I-DISCO",
    "STM32H7S78-DK",
    "STM32F469I-DISCO",
    "STM32F746G-DISCO",
    "STM32H573I-DK",
    "STM32N6570-DK",
    "STM32MP257F-EV1",
    "B-U585I-IOT02A",
    "NUCLEO-H743ZI2",
]

BANNER = r"""
  ╔══════════════════════════════════════════════════════╗
  ║       CLI Model Zoo Benchmark                        ║
  ║       ST Edge AI Core 4.0 — Developer Cloud          ║
  ╚══════════════════════════════════════════════════════╝
"""


# ---------------------------------------------------------------------------
# Selection helpers
# ---------------------------------------------------------------------------

def select_board(client=None) -> str:
    """Interactive board selection — fetches live list from cloud."""
    boards = AVAILABLE_BOARDS
    if client:
        try:
            live = client.get_boards()
            if live:
                boards = live
        except Exception:
            pass

    print(f"\n{'='*50}")
    print("  SELECTION DU BOARD CIBLE")
    print(f"{'='*50}")
    for i, board in enumerate(boards, 1):
        print(f"  [{i:2}] {board}")

    while True:
        choice = input(f"\n  Choisir (1-{len(boards)}) > ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(boards):
            selected = boards[int(choice) - 1]
            if isinstance(selected, dict):
                selected = selected.get("name", str(selected))
            print(f"  → Board: {selected}")
            return selected
        print("  Choix invalide.")


def select_option(title: str, options: dict, default: str) -> str:
    """Generic single-choice selector from a dict {value: description}."""
    print(f"\n  {title}")
    keys = list(options.keys())
    for i, (k, desc) in enumerate(options.items(), 1):
        marker = " (defaut)" if k == default else ""
        print(f"    [{i}] {k:<12} — {desc}{marker}")
    print(f"    [Entrée] Garder le defaut ({default})")

    choice = input(f"  Choix > ").strip()
    if not choice:
        return default
    if choice.isdigit() and 1 <= int(choice) <= len(keys):
        return keys[int(choice) - 1]
    print(f"  Choix invalide, utilisation du defaut: {default}")
    return default


# ---------------------------------------------------------------------------
# Benchmark workflow
# ---------------------------------------------------------------------------

def run_benchmark():
    """Full benchmark workflow: select models → board → options → run → save."""
    print("\n  === LANCEMENT D'UN BENCHMARK ===\n")

    # 1. Select models
    print("  Etape 1/4 : Selection des modeles")
    models = interactive_model_selection()
    if not models:
        print("  Benchmark annule.")
        return

    print(f"\n  {len(models)} modele(s) selectionne(s):")
    for m in models:
        print(f"    - {m['relative_dir']}/{m['name']}")

    # 2. Select board
    print("\n  Etape 2/4 : Selection du board")
    from cloud_api import CloudClient, CloudAPIError
    try:
        client = CloudClient()
    except Exception as e:
        print(f"\n  Erreur d'authentification: {e}")
        return

    board = select_board(client)

    # 3. Select optimization and compression options
    print("\n  Etape 3/4 : Options de compilation ST Edge AI Core 4.0")
    optimization = select_option(
        "Optimisation (-O) :", OPTIMIZATION_OPTIONS, OPTIMIZATION_DEFAULT
    )
    compression = select_option(
        "Compression (-c) :", COMPRESSION_OPTIONS, COMPRESSION_DEFAULT
    )

    # 4. Confirm
    print(f"\n  Etape 4/4 : Confirmation")
    print(f"  → {len(models)} modele(s) | Board: {board}")
    print(f"  → Optimization: {optimization} | Compression: {compression}")
    confirm = input("  Lancer ? (O/n) > ").strip().upper()
    if confirm == "N":
        print("  Benchmark annule.")
        return

    ensure_csv_exists()
    success_count = 0
    error_count   = 0

    for i, model in enumerate(models, 1):
        print(f"\n  [{i}/{len(models)}] {model['name']}")
        print(f"  {'─'*45}")
        try:
            metrics = client.run_benchmark(
                model["path"], board,
                optimization=optimization,
                compression=compression,
            )
            append_result(
                model_name       = model["name"],
                model_dir        = model["relative_dir"],
                type_framework   = model["extension"].lstrip("."),
                board            = board,
                optimization     = optimization,
                compression      = compression,
                inference_time_ms= metrics.get("inference_time_ms", "N/A"),
                ram_ko           = metrics.get("ram_ko", "N/A"),
                rom_ko           = metrics.get("rom_ko", "N/A"),
                macc             = metrics.get("macc", "N/A"),
                params           = metrics.get("params", "N/A"),
                accuracy         = metrics.get("accuracy", "N/A"),
                rmse             = metrics.get("rmse", "N/A"),
                mae              = metrics.get("mae", "N/A"),
                l2r              = metrics.get("l2r", "N/A"),
                status           = "OK",
            )
            success_count += 1
            t = metrics.get("inference_time_ms", "N/A")
            r = metrics.get("ram_ko", "N/A")
            o = metrics.get("rom_ko", "N/A")
            a = metrics.get("accuracy", "N/A")
            print(f"  OK — Inference: {t}ms | RAM: {r}Ko | ROM: {o}Ko | Accuracy: {a}")

        except Exception as e:
            error_count += 1
            print(f"  ERREUR: {e}")
            append_result(
                model_name=model["name"], model_dir=model["relative_dir"],
                type_framework=model["extension"].lstrip("."),
                board=board, optimization=optimization, compression=compression,
                inference_time_ms="N/A", ram_ko="N/A", rom_ko="N/A",
                macc="N/A", params="N/A",
                status=f"ERREUR: {str(e)[:100]}",
            )

    print(f"\n  === BENCHMARK TERMINE ===")
    print(f"  Succes: {success_count} | Erreurs: {error_count}")
    print(f"  CSV: {RESULTS_DIR}/resultats.csv")


# ---------------------------------------------------------------------------
# Results menu
# ---------------------------------------------------------------------------

def show_results_menu():
    while True:
        print(f"\n{'='*50}")
        print("  RESULTATS")
        print(f"{'='*50}")
        print("  [1] Afficher tous les resultats")
        print("  [2] Derniers 10 resultats")
        print("  [3] Filtrer par board")
        print("  [4] Filtrer par dossier de modeles")
        print("  [5] Filtrer par optimisation")
        print("  [R] Retour")

        choice = input("\n  Choix > ").strip().upper()
        if choice == "R":
            return
        elif choice == "1":
            display_results()
        elif choice == "2":
            display_results(last_n=10)
        elif choice == "3":
            board = input("  Board (ou partie du nom) > ").strip()
            display_results(filter_results(board=board))
        elif choice == "4":
            dossier = input("  Dossier > ").strip()
            display_results(filter_results(model_dir=dossier))
        elif choice == "5":
            opt = input("  Optimisation (balanced/ram/time/size) > ").strip()
            display_results(filter_results(optimization=opt))
        else:
            print("  Choix invalide.")


# ---------------------------------------------------------------------------
# Models overview
# ---------------------------------------------------------------------------

def show_models_overview():
    all_models = scan_models()
    if not all_models:
        print(f"\n  Aucun modele dans {MODELS_DIR}")
        print("  Formats supportes: .tflite, .h5, .onnx, .keras, .pb")
        return

    by_dir = {}
    for m in all_models:
        by_dir.setdefault(m["relative_dir"], []).append(m)

    print(f"\n{'='*50}")
    print(f"  MODELES DISPONIBLES ({len(all_models)} total)")
    print(f"{'='*50}")
    for dirname, models in sorted(by_dir.items()):
        print(f"\n  {dirname}/ ({len(models)} modeles)")
        for m in models:
            size_kb = os.path.getsize(m["path"]) / 1024
            print(f"     {m['name']} ({m['extension']}, {size_kb:.1f} Ko)")


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main_menu():
    print(BANNER)
    while True:
        print(f"\n{'='*50}")
        print("  MENU PRINCIPAL")
        print(f"{'='*50}")
        print("  [1] Voir les modeles disponibles")
        print("  [2] Lancer un benchmark")
        print("  [3] Voir les resultats")
        print("  [4] Visualiser les performances (graphiques)")
        print("  [5] Verifier l'authentification")
        print("  [Q] Quitter")

        choice = input("\n  Choix > ").strip().upper()
        if choice == "Q":
            print("\n  Au revoir!\n")
            sys.exit(0)
        elif choice == "1":
            show_models_overview()
        elif choice == "2":
            run_benchmark()
        elif choice == "3":
            show_results_menu()
        elif choice == "4":
            interactive_dashboard()
        elif choice == "5":
            try:
                from auth import get_bearer_token
                from cloud_api import get_latest_version
                token = get_bearer_token()
                ver   = get_latest_version(token)
                print(f"\n  Token valide: {token[:20]}...")
                print(f"  Cache       : ~/.stmai_token")
                print(f"  ST Edge AI Core version detectee: {ver}")
            except Exception as e:
                print(f"  Erreur: {e}")
        else:
            print("  Choix invalide.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="CLI Model Zoo Benchmark — ST Edge AI Core 4.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python main.py                        Menu interactif
  python main.py --benchmark            Benchmark direct
  python main.py --results              Voir resultats
  python main.py --results --board STM32H747I-DISCO
  python main.py --visualize            Graphiques
  python main.py --models               Lister modeles
        """,
    )
    parser.add_argument("--benchmark",  action="store_true")
    parser.add_argument("--results",    action="store_true")
    parser.add_argument("--visualize",  action="store_true")
    parser.add_argument("--models",     action="store_true")
    parser.add_argument("--board",      type=str, help="Filtrer par board")
    return parser.parse_args()


if __name__ == "__main__":
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    args = parse_args()

    if args.benchmark:
        print(BANNER)
        run_benchmark()
    elif args.results:
        display_results(filter_results(board=args.board) if args.board else None)
    elif args.visualize:
        plot_comparison_dashboard(board_filter=args.board)
    elif args.models:
        show_models_overview()
    else:
        main_menu()
