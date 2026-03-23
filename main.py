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
  python main.py --benchmark      → Lancer un benchmark simple
  python main.py --batch          → Batch benchmark (multi-selection)
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
    RESULTS_DB,
)
from model_discovery import interactive_model_selection, scan_models
from results_manager import (
    append_result,
    display_results,
    load_results,
    filter_results,
    ensure_storage_ready,
    export_results_to_csv,
    tag_benchmark,
    get_active_reference,
    get_version_history,
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


def select_core_version(default_version: str = "") -> str:
    from cloud_api import CloudClient

    versions = CloudClient.available_versions()
    if not versions:
        return default_version

    default = default_version or versions[-1]
    options = {v: "Version STEdgeAI Core" for v in versions}
    return select_option("Version Core Technology :", options, default)


def _ask_yes_no(prompt: str, default: bool = False) -> bool:
    default_hint = "O" if default else "n"
    answer = input(f"  {prompt} (O/n, defaut={default_hint}) > ").strip().upper()
    if not answer:
        return default
    return answer == "O"


def _is_npu_board_name(board_name: str) -> bool:
    upper = (board_name or "").upper()
    return any(kw in upper for kw in ("N6", "N6570", "NEURAL-ART", "NEURAL_ART", "NPU"))


def _print_memory_guidance(analysis: dict, visibility: dict, recommendation: dict):
    print("\n  Analyse modele (guidage memory pooling)")
    print(
        "  "
        f"Poids={analysis.get('weights_ko', 'N/A')} Ko | "
        f"Activations={analysis.get('activations_ko', 'N/A')} Ko | "
        f"Params={analysis.get('params', 'N/A')} | "
        f"MACCs={analysis.get('macc', 'N/A')}"
    )
    print(
        "  "
        f"Input={analysis.get('input_shape', 'N/A')} ({analysis.get('input_dtype', 'N/A')}) | "
        f"Output={analysis.get('output_shape', 'N/A')} ({analysis.get('output_dtype', 'N/A')})"
    )
    print("\n  Visibilite memoire (seuils STM32 internes)")
    for row in visibility.get("rows", []):
        flash_state = "OK" if row.get("flash_ok") else "TROP GRAND"
        ram_state = "OK" if row.get("ram_ok") else "TROP GRAND"
        overall_state = "OK" if row.get("overall_ok") else "TROP GRAND"
        print(
            "  "
            f"- {row.get('tier')}: Flash={flash_state} | RAM={ram_state} | Global={overall_state}"
        )
    print(f"\n  Recommandation auto: {recommendation.get('reason', '')}")


def collect_simple_core_preferences(memory_analysis: dict = None) -> dict:
    """Collect user intent with guided memory pooling recommendations."""
    print("\n  Options Core simplifiees")
    print("  Recommandation : laisser 'auto' pour compute mode et desactiver les options memoire au premier run.")
    print("  Impact fonctionnel :")
    print("    - split_weights=True : les poids sont separes en plusieurs buffers (integration/debug), incompatible en NPU stm32n6")
    print("    - allocate_activations=True : la RAM activations est geree par le runtime, incompatible en NPU stm32n6")

    compute_mode = select_option(
        "Mode de calcul (auto/cpu/npu) :",
        {
            "auto": "Auto selon board (recommande)",
            "cpu": "Force CPU pour comparaison",
            "npu": "Force NPU (si board compatible)",
        },
        "auto",
    )

    recommended_split = False
    recommended_alloc = False
    if memory_analysis:
        from cloud_api import build_memory_visibility_report, recommend_memory_pooling

        visibility = build_memory_visibility_report(memory_analysis)
        recommendation = recommend_memory_pooling(memory_analysis)
        _print_memory_guidance(memory_analysis, visibility, recommendation)
        recommended_split = bool(recommendation.get("split_weights", False))
        recommended_alloc = bool(recommendation.get("allocate_activations", False))
    else:
        print("  Analyse memoire indisponible: mode manuel pour split_weights/allocate_activations.")

    return {
        "compute_mode": compute_mode,
        "split_weights": _ask_yes_no(
            "Activer split_weights (poids separes) ?",
            default=recommended_split,
        ),
        "allocate_activations": _ask_yes_no(
            "Activer allocate_activations (RAM activations par runtime) ?",
            default=recommended_alloc,
        ),
    }


def choose_compute_mode_for_board(board_name: str, requested_mode: str) -> dict:
    """Resolve requested compute mode against board capabilities."""
    mode = (requested_mode or "auto").strip().lower()
    if mode not in {"auto", "cpu", "npu"}:
        mode = "auto"

    is_npu_board = _is_npu_board_name(board_name)
    if is_npu_board:
        if mode == "npu":
            return {
                "requested_mode": mode,
                "effective_mode": "npu",
                "recommendation": "Board NPU detecte: mode NPU pertinent pour minimiser la latence.",
                "impact": "Utilise target=stm32n6 + profile Neural-ART.",
            }
        if mode == "cpu":
            return {
                "requested_mode": mode,
                "effective_mode": "cpu",
                "recommendation": "Mode CPU force sur board NPU pour comparer CPU vs NPU.",
                "impact": "Desactive les options NPU explicites.",
            }
        return {
            "requested_mode": mode,
            "effective_mode": "npu",
            "recommendation": "Auto sur board NPU: NPU sera privilegie.",
            "impact": "Active target=stm32n6 + profile Neural-ART.",
        }

    if mode == "npu":
        return {
            "requested_mode": mode,
            "effective_mode": "cpu",
            "recommendation": "Board non-NPU detecte: bascule automatique vers CPU.",
            "impact": "Les options NPU sont ignorees.",
        }

    return {
        "requested_mode": mode,
        "effective_mode": "cpu",
        "recommendation": "CPU retenu sur board non-NPU.",
        "impact": "Execution sans acceleration NPU.",
    }


def build_core_options_for_board(board_name: str, simple_preferences: dict) -> dict:
    """Build board-aware options accepted by CloudClient.run_benchmark()."""
    mode_info = choose_compute_mode_for_board(board_name, simple_preferences.get("compute_mode", "auto"))
    split_weights = bool(simple_preferences.get("split_weights", False))
    allocate_activations = bool(simple_preferences.get("allocate_activations", False))
    notes = []

    if mode_info["effective_mode"] == "npu":
        if split_weights:
            notes.append("split_weights desactive: non supporte en mode NPU stm32n6")
        if allocate_activations:
            notes.append("allocate_activations desactive: non supporte en mode NPU stm32n6")
        split_weights = False
        allocate_activations = False
        target = "stm32n6"
        st_neural_art = "default"
    else:
        target = "stm32"
        st_neural_art = ""

    return {
        "cloud_args": {
            "target": target,
            "st_neural_art": st_neural_art,
            "memory_pool": "",
            "split_weights": split_weights,
            "allocate_activations": allocate_activations,
            "allocate_states": False,
            "input_memory_alignment": None,
            "output_memory_alignment": None,
            "no_inputs_allocation": False,
            "no_outputs_allocation": False,
        },
        "mode_info": mode_info,
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Benchmark workflow
# ---------------------------------------------------------------------------

def run_benchmark(core_version: str = ""):
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

    # 2. Core version + board
    print("\n  Etape 2/5 : Selection version Core Technology")
    selected_version = core_version or select_core_version()

    # 3. Select board
    print("\n  Etape 2/4 : Selection du board")
    from cloud_api import CloudClient, CloudAPIError
    try:
        client = CloudClient(version=selected_version)
    except Exception as e:
        print(f"\n  Erreur d'authentification: {e}")
        return

    board = select_board(client)

    # 4. Select optimization and compression options
    print("\n  Etape 3/5 : Options de compilation ST Edge AI Core 4.0")
    optimization = select_option(
        "Optimisation (-O) :", OPTIMIZATION_OPTIONS, OPTIMIZATION_DEFAULT
    )
    compression = select_option(
        "Compression (-c) :", COMPRESSION_OPTIONS, COMPRESSION_DEFAULT
    )

    memory_analysis = None
    if models:
        try:
            representative = models[0]
            print(f"\n  Analyse de reference sur {representative['name']}...")
            memory_analysis = client.run_analyze(
                representative["path"],
                optimization=optimization,
                compression=compression,
            )
        except Exception as e:
            print(f"  Analyse memoire ignoree ({e}).")

    # 5. Simple options
    print("\n  Etape 4/5 : Options simplifiees")
    simple_preferences = collect_simple_core_preferences(memory_analysis=memory_analysis)
    core_bundle = build_core_options_for_board(board, simple_preferences)
    core_options = core_bundle["cloud_args"]
    mode_info = core_bundle["mode_info"]

    print("\n  Commentaires Core :")
    print(f"  - Recommandation : {mode_info['recommendation']}")
    print(f"  - Impact fonctionnel : {mode_info['impact']}")
    print(f"  - Mode compute : demande={mode_info['requested_mode']} -> effectif={mode_info['effective_mode']}")
    for note in core_bundle["notes"]:
        print(f"  - Note : {note}")

    # 6. Confirm
    print(f"\n  Etape 5/5 : Confirmation")
    print(f"  → {len(models)} modele(s) | Board: {board}")
    print(f"  → Core version: {selected_version}")
    print(f"  → Optimization: {optimization} | Compression: {compression}")
    print(
        "  → Core options: "
        f"target={core_options.get('target')}, "
        f"st_neural_art={core_options.get('st_neural_art') or 'none'}, "
        f"split_weights={core_options.get('split_weights')}, "
        f"allocate_activations={core_options.get('allocate_activations')}"
    )
    confirm = input("  Lancer ? (O/n) > ").strip().upper()
    if confirm == "N":
        print("  Benchmark annule.")
        return

    ensure_storage_ready()
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
                **core_options,
            )
            run_meta = metrics.get("_run_meta", {})
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
                core_version     = run_meta.get("core_version", selected_version),
                target           = run_meta.get("target", ""),
                st_neural_art    = run_meta.get("st_neural_art", ""),
                memory_pool      = run_meta.get("memory_pool", ""),
                split_weights    = str(run_meta.get("split_weights", "")),
                allocate_activations = str(run_meta.get("allocate_activations", "")),
                allocate_states  = str(run_meta.get("allocate_states", "")),
                input_memory_alignment = run_meta.get("input_memory_alignment", ""),
                output_memory_alignment = run_meta.get("output_memory_alignment", ""),
                no_inputs_allocation = str(run_meta.get("no_inputs_allocation", "")),
                no_outputs_allocation = str(run_meta.get("no_outputs_allocation", "")),
                core_command     = run_meta.get("core_command", ""),
                run_id           = run_meta.get("run_id", ""),
                benchmark_id     = run_meta.get("benchmark_id", ""),
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
            trigger = getattr(client.bench_svc, "last_trigger", {}) or {}
            route = trigger.get("route", "")
            payload = trigger.get("payload", {})
            core_command = ""
            if route:
                import json
                core_command = f"POST {route} payload={json.dumps(payload, sort_keys=True, ensure_ascii=False)}"
            append_result(
                model_name=model["name"], model_dir=model["relative_dir"],
                type_framework=model["extension"].lstrip("."),
                board=board, optimization=optimization, compression=compression,
                inference_time_ms="N/A", ram_ko="N/A", rom_ko="N/A",
                macc="N/A", params="N/A",
                core_version=selected_version,
                target=core_options.get("target", ""),
                st_neural_art=core_options.get("st_neural_art", ""),
                memory_pool=core_options.get("memory_pool", ""),
                split_weights=str(core_options.get("split_weights", False)),
                allocate_activations=str(core_options.get("allocate_activations", False)),
                allocate_states=str(core_options.get("allocate_states", False)),
                input_memory_alignment=core_options.get("input_memory_alignment", ""),
                output_memory_alignment=core_options.get("output_memory_alignment", ""),
                no_inputs_allocation=str(core_options.get("no_inputs_allocation", False)),
                no_outputs_allocation=str(core_options.get("no_outputs_allocation", False)),
                core_command=core_command,
                status=f"ERREUR: {str(e)[:240]}",
            )

    print(f"\n  === BENCHMARK TERMINE ===")
    print(f"  Succes: {success_count} | Erreurs: {error_count}")
    print(f"  DB : {RESULTS_DB}")


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
        print("  [6] Exporter la base SQLite vers CSV")
        print("  [7] Tagger un benchmark en reference")
        print("  [8] Afficher la reference active")
        print("  [9] Historique versions (modele+board)")
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
        elif choice == "6":
            out = export_results_to_csv()
            print(f"  Export CSV termine: {out}")
        elif choice == "7":
            ident = input("  benchmark_id ou run_id > ").strip()
            ok = tag_benchmark(ident, tag_name="reference", active=True, deactivate_previous=True)
            print("  Reference enregistree." if ok else "  Identifiant introuvable.")
        elif choice == "8":
            model = input("  Modele (vide = tous) > ").strip()
            board = input("  Board (vide = tous) > ").strip()
            ref = get_active_reference(model_name=model, board=board)
            if not ref:
                print("  Aucune reference active.")
            else:
                print("  Reference active:")
                print(f"    - modele       : {ref.get('modele', '')}")
                print(f"    - board        : {ref.get('board', '')}")
                print(f"    - benchmark_id : {ref.get('benchmark_id', '')}")
                print(f"    - run_id       : {ref.get('run_id', '')}")
                print(f"    - date         : {ref.get('date', '')}")
        elif choice == "9":
            model = input("  Modele exact > ").strip()
            board = input("  Board exact > ").strip()
            opt = input("  Optimisation (vide=toutes) > ").strip()
            comp = input("  Compression (vide=toutes) > ").strip()
            history = get_version_history(model, board, opt, comp)
            if not history:
                print("  Aucun historique trouve.")
            else:
                print(f"  Historique ({len(history)} runs):")
                for row in history[:20]:
                    print(
                        "    - "
                        f"{row.get('date', '')} | bench={row.get('benchmark_id', '')} "
                        f"| run={row.get('run_id', '')} | status={row.get('status', '')}"
                    )
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
        print("  [3] Lancer un batch benchmark (multi-selection)")
        print("  [4] Voir les resultats")
        print("  [5] Visualiser les performances (graphiques)")
        print("  [6] Verifier l'authentification")
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
            from batch_benchmark import run_batch_benchmark
            run_batch_benchmark()
        elif choice == "4":
            show_results_menu()
        elif choice == "5":
            interactive_dashboard()
        elif choice == "6":
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
  python main.py --batch                Batch benchmark (multi-selection guidee)
  python main.py --results              Voir resultats
  python main.py --results --board STM32H747I-DISCO
  python main.py --visualize            Graphiques
  python main.py --models               Lister modeles
        """,
    )
    parser.add_argument("--benchmark",  action="store_true", help="Benchmark interactif simple")
    parser.add_argument("--batch",      action="store_true", help="Batch benchmark multi-selection")
    parser.add_argument("--results",    action="store_true", help="Afficher resultats")
    parser.add_argument("--visualize",  action="store_true", help="Dashboard graphique")
    parser.add_argument("--models",     action="store_true", help="Lister modeles disponibles")
    parser.add_argument("--board",      type=str, help="Filtrer par board")
    parser.add_argument("--core-version", type=str, help="Forcer une version STEdgeAI Core")
    parser.add_argument("--list-core-versions", action="store_true", help="Lister les versions Core disponibles")
    parser.add_argument("--diagnostic-run-id", type=str, help="Exporter un rapport de diagnostic consolide pour un run_id")
    parser.add_argument("--diagnostic-output", type=str, help="Dossier de sortie pour le rapport de diagnostic")
    parser.add_argument("--export-csv", action="store_true", help="Exporter les resultats SQLite vers le CSV")
    parser.add_argument("--tag-reference", type=str, help="Tagger un benchmark en reference (benchmark_id ou run_id)")
    parser.add_argument("--active-reference", action="store_true", help="Afficher la reference active")
    parser.add_argument("--history-model", type=str, help="Modele pour afficher l'historique")
    parser.add_argument("--history-board", type=str, help="Board pour afficher l'historique")
    parser.add_argument("--history-optimization", type=str, help="Filtre optimisation pour historique")
    parser.add_argument("--history-compression", type=str, help="Filtre compression pour historique")
    return parser.parse_args()


if __name__ == "__main__":
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ensure_storage_ready()

    args = parse_args()

    if args.benchmark:
        print(BANNER)
        run_benchmark(core_version=args.core_version or "")
    elif args.batch:
        print(BANNER)
        from batch_benchmark import run_batch_benchmark
        run_batch_benchmark(core_version=args.core_version or "")
    elif args.list_core_versions:
        from cloud_api import CloudClient
        versions = CloudClient.available_versions()
        print("Versions STEdgeAI Core disponibles:")
        for v in versions:
            print(f"  - {v}")
    elif args.diagnostic_run_id:
        from diagnostic_report import export_diagnostic_report
        report = export_diagnostic_report(args.diagnostic_run_id, args.diagnostic_output or "")
        print("Rapport de diagnostic genere:")
        print(f"  run_id        : {report['run_id']}")
        print(f"  summary       : {report['summary_json']}")
        print(f"  rows_csv      : {report['rows_csv']}")
        print(f"  events_jsonl  : {report['events_jsonl']}")
        print(f"  csv_rows      : {report['csv_rows_count']}")
        print(f"  events        : {report['events_count']}")
    elif args.export_csv:
        out = export_results_to_csv()
        print(f"Export termine: {out}")
    elif args.tag_reference:
        ok = tag_benchmark(args.tag_reference, tag_name="reference", active=True, deactivate_previous=True)
        print("Reference enregistree." if ok else "Identifiant introuvable.")
    elif args.active_reference:
        ref = get_active_reference(model_name="", board=args.board or "")
        if not ref:
            print("Aucune reference active.")
        else:
            print("Reference active:")
            print(f"  modele       : {ref.get('modele', '')}")
            print(f"  board        : {ref.get('board', '')}")
            print(f"  benchmark_id : {ref.get('benchmark_id', '')}")
            print(f"  run_id       : {ref.get('run_id', '')}")
            print(f"  date         : {ref.get('date', '')}")
    elif args.history_model and args.history_board:
        rows = get_version_history(
            args.history_model,
            args.history_board,
            args.history_optimization or "",
            args.history_compression or "",
        )
        print(f"Historique ({len(rows)} runs):")
        for row in rows[:50]:
            print(
                f"  - {row.get('date', '')} | bench={row.get('benchmark_id', '')} "
                f"| run={row.get('run_id', '')} | status={row.get('status', '')}"
            )
    elif args.results:
        display_results(filter_results(board=args.board) if args.board else None)
    elif args.visualize:
        plot_comparison_dashboard(board_filter=args.board)
    elif args.models:
        show_models_overview()
    else:
        main_menu()
