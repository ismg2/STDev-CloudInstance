"""Batch benchmark module — Interactive multi-selection for boards, optimizations, compressions."""

from config import OPTIMIZATION_OPTIONS, COMPRESSION_OPTIONS


def select_multiple_boards(boards: list) -> list:
    """Interactive multi-selection of boards with checkboxes.

    Args:
        boards: List of board names (from cloud API or fallback list)

    Returns:
        list[str]: Selected board names
    """
    selected = []

    while True:
        print(f"\n{'='*60}")
        print("  SELECTION DES BOARDS CIBLES (multi-selection)")
        print(f"{'='*60}")

        for i, board in enumerate(boards, 1):
            marker = " ✓" if board in selected else ""
            print(f"  [{i:2}] {board}{marker}")

        print(f"\n  [A] Selectionner TOUS les boards")
        print(f"  [C] Effacer la selection")
        print(f"  [OK] Valider ({len(selected)} board(s) selectionne(s))")
        print(f"  [Q] Annuler")

        choice = input("\n  Choix > ").strip().upper()

        if choice == "Q":
            return []
        elif choice == "OK":
            if not selected:
                print("\n  ⚠ Aucun board selectionne.")
                continue
            return selected
        elif choice == "A":
            selected = boards.copy()
            print(f"  → {len(selected)} board(s) selectionne(s).")
        elif choice == "C":
            selected = []
            print("  → Selection effacee.")
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(boards):
                board = boards[idx]
                if board in selected:
                    selected.remove(board)
                    print(f"  → {board} retire de la selection.")
                else:
                    selected.append(board)
                    print(f"  → {board} ajoute a la selection.")
            else:
                print("  Choix invalide.")
        else:
            print("  Choix invalide.")


def select_multiple_options(title: str, options: dict, default_key: str) -> list:
    """Interactive multi-selection from a dict {key: description}.

    Args:
        title: Section title (e.g., "OPTIMISATIONS")
        options: Dict of {key: description}
        default_key: The default option to pre-select

    Returns:
        list[str]: Selected option keys
    """
    keys = list(options.keys())
    selected = [default_key]  # Pre-select default

    while True:
        print(f"\n{'='*60}")
        print(f"  {title} (multi-selection)")
        print(f"{'='*60}")

        for i, (k, desc) in enumerate(options.items(), 1):
            marker = " ✓" if k in selected else ""
            default_marker = " (defaut)" if k == default_key else ""
            print(f"  [{i}] {k:<12} — {desc}{default_marker}{marker}")

        print(f"\n  [A] Selectionner TOUTES les options")
        print(f"  [D] Selectionner uniquement le defaut ({default_key})")
        print(f"  [C] Effacer la selection")
        print(f"  [OK] Valider ({len(selected)} option(s) selectionnee(s))")
        print(f"  [Q] Annuler")

        choice = input("\n  Choix > ").strip().upper()

        if choice == "Q":
            return []
        elif choice == "OK":
            if not selected:
                print("\n  ⚠ Aucune option selectionnee.")
                continue
            return selected
        elif choice == "A":
            selected = keys.copy()
            print(f"  → {len(selected)} option(s) selectionnee(s).")
        elif choice == "D":
            selected = [default_key]
            print(f"  → Seulement '{default_key}' selectionne.")
        elif choice == "C":
            selected = []
            print("  → Selection effacee.")
        elif choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(keys):
                key = keys[idx]
                if key in selected:
                    selected.remove(key)
                    print(f"  → '{key}' retire de la selection.")
                else:
                    selected.append(key)
                    print(f"  → '{key}' ajoute a la selection.")
            else:
                print("  Choix invalide.")
        else:
            print("  Choix invalide.")


def interactive_batch_benchmark():
    """Guided workflow for batch benchmark.

    Returns:
        dict or None: Configuration dict with keys:
            - models: list[dict]
            - boards: list[str]
            - optimizations: list[str]
            - compressions: list[str]
        Returns None if user cancels.
    """
    print("\n  === BENCHMARK EN BATCH (MODE GUIDE) ===\n")

    # Step 1: Select models
    print("  Etape 1/4 : Selection des modeles")
    from model_discovery import interactive_model_selection
    models = interactive_model_selection()
    if not models:
        print("  Batch annule.")
        return None

    print(f"\n  {len(models)} modele(s) selectionne(s):")
    for m in models:
        print(f"    - {m['relative_dir']}/{m['name']}")

    # Step 2: Select boards (multi)
    print("\n  Etape 2/4 : Selection des boards")
    from cloud_api import CloudClient
    from main import AVAILABLE_BOARDS
    try:
        client = CloudClient()
        boards_list = client.get_boards() or AVAILABLE_BOARDS
    except Exception as e:
        print(f"  Erreur d'authentification: {e}")
        return None

    boards = select_multiple_boards(boards_list)
    if not boards:
        print("  Batch annule.")
        return None

    print(f"\n  {len(boards)} board(s) selectionne(s): {', '.join(boards)}")

    # Step 3: Select optimizations (multi)
    print("\n  Etape 3/4 : Selection des optimisations")
    optimizations = select_multiple_options(
        "OPTIMISATIONS (-O)", OPTIMIZATION_OPTIONS, "balanced"
    )
    if not optimizations:
        print("  Batch annule.")
        return None

    print(f"\n  {len(optimizations)} optimisation(s) selectionnee(s): {', '.join(optimizations)}")

    # Step 4: Select compressions (multi)
    print("\n  Etape 4/4 : Selection des compressions")
    compressions = select_multiple_options(
        "COMPRESSIONS (-c)", COMPRESSION_OPTIONS, "lossless"
    )
    if not compressions:
        print("  Batch annule.")
        return None

    print(f"\n  {len(compressions)} compression(s) selectionnee(s): {', '.join(compressions)}")

    # Confirmation summary
    total_runs = len(models) * len(boards) * len(optimizations) * len(compressions)
    print(f"\n{'='*60}")
    print("  RESUME DU BATCH")
    print(f"{'='*60}")
    print(f"  Modeles        : {len(models)}")
    print(f"  Boards         : {len(boards)}")
    print(f"  Optimisations  : {len(optimizations)}")
    print(f"  Compressions   : {len(compressions)}")
    print(f"  {'─'*58}")
    print(f"  TOTAL BENCHMARKS : {total_runs}")
    print(f"{'='*60}")

    confirm = input("\n  Lancer le batch ? (O/n) > ").strip().upper()
    if confirm == "N":
        print("  Batch annule.")
        return None

    return {
        "models": models,
        "boards": boards,
        "optimizations": optimizations,
        "compressions": compressions,
    }


def run_batch_benchmark():
    """Execute batch benchmark with progress tracking."""
    from tqdm import tqdm
    from results_manager import append_result, ensure_csv_exists
    from cloud_api import CloudClient
    import datetime

    # Interactive configuration
    config = interactive_batch_benchmark()
    if not config:
        return

    models = config["models"]
    boards = config["boards"]
    optimizations = config["optimizations"]
    compressions = config["compressions"]

    # Initialize client
    try:
        client = CloudClient()
    except Exception as e:
        print(f"\n  Erreur: impossible de se connecter au cloud: {e}")
        return

    ensure_csv_exists()

    # Build queue
    queue = []
    for model in models:
        for board in boards:
            for opt in optimizations:
                for comp in compressions:
                    queue.append({
                        "model": model,
                        "board": board,
                        "optimization": opt,
                        "compression": comp,
                    })

    total = len(queue)
    success_count = 0
    error_count = 0

    print(f"\n{'='*60}")
    print(f"  EXECUTION DU BATCH — {total} benchmarks")
    print(f"{'='*60}\n")

    start_time = datetime.datetime.now()

    # Progress bar
    for i, task in enumerate(tqdm(queue, desc="  Benchmarks", unit="run"), 1):
        model = task["model"]
        board = task["board"]
        opt = task["optimization"]
        comp = task["compression"]

        task_name = f"{model['name']} | {board} | {opt}/{comp}"

        try:
            metrics = client.run_benchmark(
                model["path"], board,
                optimization=opt,
                compression=comp,
            )
            append_result(
                model_name       = model["name"],
                model_dir        = model["relative_dir"],
                type_framework   = model["extension"].lstrip("."),
                board            = board,
                optimization     = opt,
                compression      = comp,
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

        except Exception as e:
            error_count += 1
            print(f"\n  ❌ [{i}/{total}] {task_name}")
            print(f"     ERREUR: {str(e)[:80]}")
            append_result(
                model_name=model["name"], model_dir=model["relative_dir"],
                type_framework=model["extension"].lstrip("."),
                board=board, optimization=opt, compression=comp,
                inference_time_ms="N/A", ram_ko="N/A", rom_ko="N/A",
                macc="N/A", params="N/A",
                status=f"ERREUR: {str(e)[:100]}",
            )

    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n{'='*60}")
    print("  BATCH TERMINE")
    print(f"{'='*60}")
    print(f"  Total benchmarks : {total}")
    print(f"  Succes           : {success_count} ({100*success_count/total:.1f}%)")
    print(f"  Erreurs          : {error_count} ({100*error_count/total:.1f}%)")
    print(f"  Duree totale     : {duration/60:.1f} minutes ({duration:.0f}s)")
    print(f"  Temps moyen/run  : {duration/total:.1f}s")
    print(f"\n  Resultats sauvegardes dans: resultats/resultats.csv")
    print(f"{'='*60}\n")
