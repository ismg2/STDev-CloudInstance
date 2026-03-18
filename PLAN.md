# Plan de Développement - CLI Model Zoo Benchmark

## Vue d'ensemble
Script Python CLI interactif pour gérer, benchmarker et visualiser les performances
de modèles AI via le ST Edge AI Developer Cloud.

---

## Session 1 : Scaffolding & Authentification
- Structure du projet (dossiers, __init__.py, requirements.txt)
- Module d'authentification OAuth2/Bearer (réutilise le token ~/.stmai_token)
- Configuration (endpoints, boards cibles, settings par défaut)
- Point d'entrée principal `main.py`

## Session 2 : Découverte des modèles & Menus CLI interactifs
- Scanner récursif du dossier `modeles/` (.tflite, .h5, .onnx, .keras)
- Navigation interactive avec sous-dossiers (prompt guidé)
- Sélection de modèle(s) pour benchmark
- Sélection de board cible STM32

## Session 3 : Intégration API STEdgeAI Developer Cloud
- Upload de modèle via `/api/file`
- Analyse via `/api/{version}/stm32ai/analyze`
- Benchmark via `/api/benchmark`
- Polling des résultats (wait_for_run)
- Parsing des métriques : inference time, RAM, ROM, MACC

## Session 4 : Gestion des résultats CSV
- Export automatique dans `resultats/resultats.csv`
- Colonnes : modèle, board, inference_time_ms, ram_kb, rom_kb, macc, precision, date
- Ajout incrémental (append) sans écraser les anciens résultats
- Commande pour lister/filtrer les résultats existants

## Session 5 : Dashboard de visualisation
- Interface graphique simple (matplotlib + tkinter)
- Graphiques : barres comparatives inference time, memory, precision
- Filtres par board, par dossier de modèles
- Lancement via commande CLI `--visualize`

---

## Architecture fichiers
```
STDev-CloudInstance/
├── main.py                    # Point d'entrée CLI
├── requirements.txt
├── config.py                  # Configuration & endpoints
├── auth.py                    # Authentification Bearer/OAuth2
├── model_discovery.py         # Scan et sélection de modèles
├── cloud_api.py               # Client API STEdgeAI Cloud
├── results_manager.py         # Gestion CSV des résultats
├── dashboard.py               # Visualisation graphique
├── modeles/                   # Dossier modèles (avec sous-dossiers)
│   └── exemple/
│       └── .gitkeep
├── resultats/                 # Dossier résultats
│   └── .gitkeep
└── PLAN.md
```

## Authentification
- Réutilisation du token Bearer stocké dans `~/.stmai_token`
- Si token expiré → refresh automatique via `/login/refresh`
- Si pas de token → login interactif (username/password en prompt, jamais en clair dans le code)
- Support variables d'env `stmai_username` / `stmai_password` (optionnel)
