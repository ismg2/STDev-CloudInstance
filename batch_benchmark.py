"""Batch benchmark module — Interactive multi-selection for boards, optimizations, compressions."""

from config import OPTIMIZATION_OPTIONS, COMPRESSION_OPTIONS


def _is_npu_board_name(board_name: str) -> bool:
    upper = (board_name or "").upper()
    return any(kw in upper for kw in ("N6", "N6570", "NEURAL-ART", "NEURAL_ART", "NPU"))


def select_compute_mode_for_boards(boards: list) -> dict:
    """Select compute mode per board.

    For NPU boards, allows auto/cpu/npu/both.
    For non-NPU boards, allows auto/cpu.
    """
    modes = {}
    print(f"\n{'='*60}")
    print("  MODE DE CALCUL PAR BOARD")
    print(f"{'='*60}")
    print("  Reco: auto pour 1er passage; sur board NPU tu peux choisir BOTH pour comparer CPU vs NPU.")

    for board in boards:
        is_npu = _is_npu_board_name(board)
        print(f"\n  Board: {board}")
        if is_npu:
            options = {
                "auto": "Auto (NPU privilegie)",
                "cpu": "Force CPU",
                "npu": "Force NPU",
                "both": "Lancer CPU + NPU",
            }
        else:
            options = {
                "auto": "Auto (equivalent CPU)",
                "cpu": "Force CPU",
            }

        keys = list(options.keys())
        for i, key in enumerate(keys, 1):
            marker = " (defaut)" if key == "auto" else ""
            print(f"    [{i}] {key:<5} - {options[key]}{marker}")

        choice = input("  Choix [Entree=auto] > ").strip()
        if not choice:
            modes[board] = "auto"
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(keys):
            modes[board] = keys[int(choice) - 1]
        elif choice.lower() in options:
            modes[board] = choice.lower()
        else:
            print("  Choix invalide, auto applique.")
            modes[board] = "auto"

    return modes


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


def interactive_batch_benchmark(core_version: str = ""):
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
        client = CloudClient(version=core_version or None)
        boards_list = client.get_boards() or AVAILABLE_BOARDS
    except Exception as e:
        print(f"  Erreur d'authentification: {e}")
        return None

    boards = select_multiple_boards(boards_list)
    if not boards:
        print("  Batch annule.")
        return None

    print(f"\n  {len(boards)} board(s) selectionne(s): {', '.join(boards)}")

    # Step 3: Select core versions (multi)
    versions = CloudClient.available_versions()
    versions_map = {v: "Version STEdgeAI Core" for v in versions}
    default_version = core_version or client.version
    print("\n  Etape 3/5 : Selection des versions Core")
    selected_versions = select_multiple_options(
        "VERSIONS CORE", versions_map, default_version
    )
    if not selected_versions:
        print("  Batch annule.")
        return None

    # Step 4: Select optimizations (multi)
    print("\n  Etape 3/4 : Selection des optimisations")
    optimizations = select_multiple_options(
        "OPTIMISATIONS (-O)", OPTIMIZATION_OPTIONS, "balanced"
    )
    if not optimizations:
        print("  Batch annule.")
        return None

    print(f"\n  {len(optimizations)} optimisation(s) selectionnee(s): {', '.join(optimizations)}")

    # Step 5: Select compressions (multi)
    print("\n  Etape 5/5 : Selection des compressions")
    compressions = select_multiple_options(
        "COMPRESSIONS (-c)", COMPRESSION_OPTIONS, "lossless"
    )
    if not compressions:
        print("  Batch annule.")
        return None

    print(f"\n  {len(compressions)} compression(s) selectionnee(s): {', '.join(compressions)}")

    memory_analysis = None
    if models:
        try:
            representative = models[0]
            ref_version = selected_versions[0]
            print(
                "\n  Analyse memoire de reference "
                f"({representative['name']} | Core {ref_version} | {optimizations[0]}/{compressions[0]})..."
            )
            analysis_client = client if ref_version == client.version else CloudClient(version=ref_version)
            memory_analysis = analysis_client.run_analyze(
                representative["path"],
                optimization=optimizations[0],
                compression=compressions[0],
            )
        except Exception as e:
            print(f"  Analyse memoire ignoree ({e}).")

    from main import collect_simple_core_preferences
    simple_preferences = collect_simple_core_preferences(memory_analysis=memory_analysis)
    board_modes = select_compute_mode_for_boards(boards)

    # Confirmation summary
    mode_multiplier = 0
    for board in boards:
        mode_multiplier += 2 if board_modes.get(board) == "both" else 1
    total_runs = len(models) * len(selected_versions) * len(optimizations) * len(compressions) * mode_multiplier
    print(f"\n{'='*60}")
    print("  RESUME DU BATCH")
    print(f"{'='*60}")
    print(f"  Modeles        : {len(models)}")
    print(f"  Boards         : {len(boards)}")
    print(f"  Versions Core  : {len(selected_versions)}")
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
        "versions": selected_versions,
        "optimizations": optimizations,
        "compressions": compressions,
        "simple_preferences": simple_preferences,
        "board_modes": board_modes,
    }


def run_batch_benchmark(core_version: str = ""):
    """Execute batch benchmark with progress tracking."""
    from tqdm import tqdm
    from results_manager import append_result, ensure_storage_ready
    from cloud_api import CloudClient
    from config import RESULTS_DB
    import datetime

    # Interactive configuration
    config = interactive_batch_benchmark(core_version=core_version)
    if not config:
        return

    models = config["models"]
    boards = config["boards"]
    versions = config["versions"]
    optimizations = config["optimizations"]
    compressions = config["compressions"]
    simple_preferences = config.get("simple_preferences", {"compute_mode": "auto", "split_weights": False, "allocate_activations": False})
    board_modes = config.get("board_modes", {board: "auto" for board in boards})

    # Initialize clients per requested version
    client_cache = {}
    try:
        for version in versions:
            client_cache[version] = CloudClient(version=version)
    except Exception as e:
        print(f"\n  Erreur: impossible de se connecter au cloud: {e}")
        return

    ensure_storage_ready()

    # Build queue
    queue = []
    from main import build_core_options_for_board

    for model in models:
        for board in boards:
            mode = board_modes.get(board, "auto")
            mode_variants = ["cpu", "npu"] if mode == "both" else [mode]
            for version in versions:
                for mode_variant in mode_variants:
                    prefs = dict(simple_preferences)
                    prefs["compute_mode"] = mode_variant
                    core_bundle = build_core_options_for_board(board, prefs)
                    for opt in optimizations:
                        for comp in compressions:
                            queue.append({
                                "model": model,
                                "board": board,
                                "version": version,
                                "compute_mode": mode_variant,
                                "core_bundle": core_bundle,
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
    try:
        for i, task in enumerate(tqdm(queue, desc="  Benchmarks", unit="run"), 1):
            model = task["model"]
            board = task["board"]
            version = task["version"]
            compute_mode = task.get("compute_mode", "auto")
            core_bundle = task.get("core_bundle", {"cloud_args": {}, "mode_info": {}, "notes": []})
            core_options = core_bundle.get("cloud_args", {})
            opt = task["optimization"]
            comp = task["compression"]
            client = client_cache[version]

            task_name = f"{model['name']} | {board} | {compute_mode} | v{version} | {opt}/{comp}"

            try:
                metrics = client.run_benchmark(
                    model["path"], board,
                    optimization=opt,
                    compression=comp,
                    **core_options,
                )
                run_meta = metrics.get("_run_meta", {})
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
                    core_version     = run_meta.get("core_version", version),
                    target           = run_meta.get("target", core_options.get("target", "")),
                    st_neural_art    = run_meta.get("st_neural_art", core_options.get("st_neural_art", "")),
                    memory_pool      = run_meta.get("memory_pool", core_options.get("memory_pool", "")),
                    split_weights    = str(run_meta.get("split_weights", core_options.get("split_weights", False))),
                    allocate_activations = str(run_meta.get("allocate_activations", core_options.get("allocate_activations", False))),
                    allocate_states  = str(run_meta.get("allocate_states", core_options.get("allocate_states", False))),
                    input_memory_alignment = run_meta.get("input_memory_alignment", core_options.get("input_memory_alignment", "")),
                    output_memory_alignment = run_meta.get("output_memory_alignment", core_options.get("output_memory_alignment", "")),
                    no_inputs_allocation = str(run_meta.get("no_inputs_allocation", core_options.get("no_inputs_allocation", False))),
                    no_outputs_allocation = str(run_meta.get("no_outputs_allocation", core_options.get("no_outputs_allocation", False))),
                    core_command     = run_meta.get("core_command", ""),
                    run_id           = run_meta.get("run_id", ""),
                    benchmark_id     = run_meta.get("benchmark_id", ""),
                    status           = "OK",
                )
                success_count += 1

            except Exception as e:
                error_count += 1
                print(f"\n  ❌ [{i}/{total}] {task_name}")
                print(f"     ERREUR: {str(e)[:80]}")
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
                    board=board, optimization=opt, compression=comp,
                    inference_time_ms="N/A", ram_ko="N/A", rom_ko="N/A",
                    macc="N/A", params="N/A",
                    core_version=version,
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
    except KeyboardInterrupt:
        print("\n\n  Batch interrompu par l'utilisateur. Sauvegarde des resultats partiels.")

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
    print(f"\n  Resultats sauvegardes dans: {RESULTS_DB}")
    print(f"{'='*60}\n")
