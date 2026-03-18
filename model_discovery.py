"""Model discovery module - scans and navigates model directories."""

import os

from config import MODELS_DIR, MODEL_EXTENSIONS


def scan_models(root_dir=None):
    """Scan a directory recursively for model files.

    Returns:
        list[dict]: List of dicts with keys: name, path, extension, relative_dir
    """
    root_dir = root_dir or MODELS_DIR
    models = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in sorted(filenames):
            ext = os.path.splitext(fname)[1].lower()
            if ext in MODEL_EXTENSIONS:
                full_path = os.path.join(dirpath, fname)
                rel_dir = os.path.relpath(dirpath, MODELS_DIR)
                if rel_dir == ".":
                    rel_dir = "(racine)"
                models.append({
                    "name": fname,
                    "path": full_path,
                    "extension": ext,
                    "relative_dir": rel_dir,
                })
    return models


def list_subdirs(root_dir=None):
    """List immediate subdirectories of a directory.

    Returns:
        list[str]: Sorted list of subdirectory names.
    """
    root_dir = root_dir or MODELS_DIR
    if not os.path.isdir(root_dir):
        return []
    return sorted([
        d for d in os.listdir(root_dir)
        if os.path.isdir(os.path.join(root_dir, d)) and not d.startswith(".")
    ])


def list_models_in_dir(directory):
    """List model files in a specific directory (non-recursive).

    Returns:
        list[dict]: Model dicts for models directly in this directory.
    """
    models = []
    if not os.path.isdir(directory):
        return models
    for fname in sorted(os.listdir(directory)):
        ext = os.path.splitext(fname)[1].lower()
        if ext in MODEL_EXTENSIONS:
            full_path = os.path.join(directory, fname)
            rel_dir = os.path.relpath(directory, MODELS_DIR)
            if rel_dir == ".":
                rel_dir = "(racine)"
            models.append({
                "name": fname,
                "path": full_path,
                "extension": ext,
                "relative_dir": rel_dir,
            })
    return models


def interactive_model_selection():
    """Interactive CLI navigation to select model(s).

    Returns:
        list[dict]: Selected model(s).
    """
    if not os.path.isdir(MODELS_DIR):
        print(f"\n  Erreur: Le dossier '{MODELS_DIR}' n'existe pas.")
        print(f"  Creez-le et placez-y vos modeles (.tflite, .h5, .onnx, .keras)")
        return []

    current_dir = MODELS_DIR
    selected = []

    while True:
        print(f"\n{'='*60}")
        print(f"  Dossier actuel: {os.path.relpath(current_dir, MODELS_DIR) or '(racine)'}")
        print(f"{'='*60}")

        subdirs = list_subdirs(current_dir)
        models = list_models_in_dir(current_dir)

        options = []
        idx = 1

        # Show subdirectories
        if subdirs:
            print("\n  Sous-dossiers:")
            for d in subdirs:
                print(f"    [{idx}] 📁 {d}/")
                options.append(("dir", os.path.join(current_dir, d)))
                idx += 1

        # Show models
        if models:
            print("\n  Modeles disponibles:")
            for m in models:
                marker = " ✓" if m in selected else ""
                print(f"    [{idx}] 🤖 {m['name']} ({m['extension']}){marker}")
                options.append(("model", m))
                idx += 1

        if not subdirs and not models:
            print("\n  (Aucun modele ni sous-dossier ici)")

        # Navigation options
        print(f"\n  [R] Remonter au dossier parent")
        print(f"  [A] Selectionner TOUS les modeles de ce dossier")
        print(f"  [T] Selectionner TOUS les modeles (recursif)")
        print(f"  [V] Voir la selection actuelle ({len(selected)} modele(s))")
        print(f"  [OK] Valider la selection")
        print(f"  [Q] Quitter")

        choice = input("\n  Choix > ").strip().upper()

        if choice == "Q":
            return []
        elif choice == "OK":
            if not selected:
                print("\n  ⚠ Aucun modele selectionne.")
                continue
            return selected
        elif choice == "R":
            parent = os.path.dirname(current_dir)
            if parent >= MODELS_DIR:
                current_dir = parent
            else:
                print("  Vous etes deja a la racine.")
        elif choice == "A":
            for m in models:
                if m not in selected:
                    selected.append(m)
            print(f"  → {len(models)} modele(s) ajoute(s) a la selection.")
        elif choice == "T":
            all_models = scan_models(current_dir)
            for m in all_models:
                if m not in selected:
                    selected.append(m)
            print(f"  → {len(all_models)} modele(s) ajoute(s) (recursif).")
        elif choice == "V":
            if selected:
                print("\n  Selection actuelle:")
                for i, m in enumerate(selected, 1):
                    print(f"    {i}. {m['relative_dir']}/{m['name']}")
            else:
                print("\n  Aucun modele selectionne.")
        elif choice.isdigit():
            idx_choice = int(choice) - 1
            if 0 <= idx_choice < len(options):
                opt_type, opt_val = options[idx_choice]
                if opt_type == "dir":
                    current_dir = opt_val
                elif opt_type == "model":
                    if opt_val in selected:
                        selected.remove(opt_val)
                        print(f"  → {opt_val['name']} retire de la selection.")
                    else:
                        selected.append(opt_val)
                        print(f"  → {opt_val['name']} ajoute a la selection.")
            else:
                print("  Choix invalide.")
        else:
            print("  Choix invalide.")
