#!/usr/bin/env python3
"""CLI Model Zoo Benchmark - Point d'entree principal.

Script interactif en ligne de commande pour:
- Naviguer et selectionner des modeles AI
- Les benchmarker via ST Edge AI Developer Cloud
- Stocker et visualiser les resultats

Usage:
    python main.py                  # Menu interactif
    python main.py --benchmark      # Lancer directement un benchmark
    python main.py --results        # Afficher les resultats
    python main.py --visualize      # Ouvrir le dashboard graphique
    python main.py --help           # Aide
"""

import argparse
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import MODELS_DIR, RESULTS_DIR, AVAILABLE_BOARDS
from model_discovery import interactive_model_selection, scan_models
from results_manager import (
    append_result, display_results, load_results, filter_results, ensure_csv_exists,
)
from dashboard import interactive_dashboard


BANNER = r"""
  ╔══════════════════════════════════════════════════════╗
  ║       CLI Model Zoo Benchmark                        ║
  ║       ST Edge AI Developer Cloud                     ║
  ╚══════════════════════════════════════════════════════╝
"""


def select_board():
    """Interactive board selection."""
    print(f"\n{'='*50}")
    print("  SELECTION DU BOARD CIBLE")
    print(f"{'='*50}")

    # Try to fetch from cloud, fall back to config
    boards = AVAILABLE_BOARDS
    try:
        from cloud_api import CloudClient
        client = CloudClient()
        cloud_boards = client.get_available_boards()
        if isinstance(cloud_boards, list) and cloud_boards:
            boards = cloud_boards
    except Exception:
        pass

    for i, board in enumerate(boards, 1):
        print(f"  [{i}] {board}")

    while True:
        choice = input(f"\n  Choisir un board (1-{len(boards)}) > ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(boards):
            selected = boards[int(choice) - 1]
            if isinstance(selected, dict):
                selected = selected.get("name", selected.get("board_name", str(selected)))
            print(f"  → Board selectionne: {selected}")
            return selected
        print("  Choix invalide.")


def run_benchmark():
    """Full benchmark workflow: select models, board, run, save results."""
    print("\n  === LANCEMENT D'UN BENCHMARK ===\n")

    # Step 1: Select models
    print("  Etape 1/3 : Selection des modeles")
    models = interactive_model_selection()
    if not models:
        print("  Benchmark annule (aucun modele selectionne).")
        return

    print(f"\n  {len(models)} modele(s) selectionne(s):")
    for m in models:
        print(f"    - {m['relative_dir']}/{m['name']}")

    # Step 2: Select board
    print("\n  Etape 2/3 : Selection du board")
    board = select_board()

    # Step 3: Confirm and run
    print(f"\n  Etape 3/3 : Lancement du benchmark")
    print(f"  → {len(models)} modele(s) sur {board}")
    confirm = input("  Confirmer ? (O/n) > ").strip().upper()
    if confirm == "N":
        print("  Benchmark annule.")
        return

    # Import cloud client
    try:
        from cloud_api import CloudClient, CloudAPIError
    except ImportError as e:
        print(f"  Erreur d'import: {e}")
        return

    try:
        client = CloudClient()
    except Exception as e:
        print(f"\n  Erreur d'authentification: {e}")
        print("  Verifiez vos identifiants et reessayez.")
        return

    ensure_csv_exists()
    success_count = 0
    error_count = 0

    for i, model in enumerate(models, 1):
        print(f"\n  [{i}/{len(models)}] {model['name']}")
        print(f"  {'─'*40}")

        try:
            # Upload
            file_id = client.upload_model(model["path"])

            # Analyze (for memory info)
            analysis = client.analyze_model(file_id)

            # Benchmark (for inference time)
            benchmark = client.benchmark_model(file_id, board)

            # Merge results
            inference_time = benchmark.get("inference_time_ms", "N/A")
            ram = benchmark.get("ram_ko") or analysis.get("ram_ko", "N/A")
            rom = benchmark.get("rom_ko") or analysis.get("rom_ko", "N/A")
            macc = analysis.get("macc", "N/A")

            append_result(
                model_name=model["name"],
                model_dir=model["relative_dir"],
                board=board,
                inference_time_ms=inference_time,
                ram_ko=ram,
                rom_ko=rom,
                macc=macc,
                precision="N/A",
                status="OK",
            )
            success_count += 1
            print(f"  ✓ OK - Inference: {inference_time}ms, RAM: {ram}Ko, ROM: {rom}Ko")

        except Exception as e:
            error_count += 1
            print(f"  ✗ ERREUR: {e}")
            append_result(
                model_name=model["name"],
                model_dir=model["relative_dir"],
                board=board,
                inference_time_ms="N/A",
                ram_ko="N/A",
                rom_ko="N/A",
                macc="N/A",
                precision="N/A",
                status=f"ERREUR: {str(e)[:100]}",
            )

    print(f"\n  === BENCHMARK TERMINE ===")
    print(f"  Succes: {success_count} | Erreurs: {error_count}")
    print(f"  Resultats sauvegardes dans: {RESULTS_DIR}/resultats.csv")


def show_results_menu():
    """Interactive results viewing."""
    while True:
        print(f"\n{'='*50}")
        print("  RESULTATS")
        print(f"{'='*50}")
        print("  [1] Afficher tous les resultats")
        print("  [2] Afficher les 10 derniers")
        print("  [3] Filtrer par board")
        print("  [4] Filtrer par dossier de modeles")
        print("  [R] Retour")

        choice = input("\n  Choix > ").strip().upper()
        if choice == "R":
            return
        elif choice == "1":
            display_results()
        elif choice == "2":
            display_results(last_n=10)
        elif choice == "3":
            board = input("  Nom du board > ").strip()
            df = filter_results(board=board)
            display_results(df)
        elif choice == "4":
            dossier = input("  Nom du dossier > ").strip()
            df = filter_results(model_dir=dossier)
            display_results(df)
        else:
            print("  Choix invalide.")


def show_models_overview():
    """Show an overview of models in the models directory."""
    all_models = scan_models()
    if not all_models:
        print(f"\n  Aucun modele trouve dans {MODELS_DIR}")
        print(f"  Placez vos modeles (.tflite, .h5, .onnx, .keras) dans ce dossier.")
        return

    # Group by directory
    by_dir = {}
    for m in all_models:
        by_dir.setdefault(m["relative_dir"], []).append(m)

    print(f"\n{'='*50}")
    print(f"  MODELES DISPONIBLES ({len(all_models)} total)")
    print(f"{'='*50}")

    for dirname, models in sorted(by_dir.items()):
        print(f"\n  📁 {dirname}/ ({len(models)} modeles)")
        for m in models:
            size_kb = os.path.getsize(m["path"]) / 1024
            print(f"     - {m['name']} ({m['extension']}, {size_kb:.1f} Ko)")


def main_menu():
    """Main interactive menu."""
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
                token = get_bearer_token()
                print(f"  Token valide: {token[:20]}...")
            except Exception as e:
                print(f"  Erreur: {e}")
        else:
            print("  Choix invalide.")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CLI Model Zoo Benchmark - ST Edge AI Developer Cloud",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python main.py                  Menu interactif guide
  python main.py --benchmark      Lancer un benchmark
  python main.py --results        Afficher les resultats
  python main.py --visualize      Dashboard graphique
  python main.py --models         Lister les modeles
        """,
    )
    parser.add_argument("--benchmark", action="store_true", help="Lancer directement un benchmark")
    parser.add_argument("--results", action="store_true", help="Afficher les resultats")
    parser.add_argument("--visualize", action="store_true", help="Ouvrir le dashboard graphique")
    parser.add_argument("--models", action="store_true", help="Lister les modeles disponibles")
    parser.add_argument("--board", type=str, help="Filtrer par board (avec --results ou --visualize)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Ensure directories exist
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    if args.benchmark:
        print(BANNER)
        run_benchmark()
    elif args.results:
        if args.board:
            df = filter_results(board=args.board)
            display_results(df)
        else:
            display_results()
    elif args.visualize:
        from dashboard import plot_comparison_dashboard
        plot_comparison_dashboard(board_filter=args.board)
    elif args.models:
        show_models_overview()
    else:
        main_menu()
