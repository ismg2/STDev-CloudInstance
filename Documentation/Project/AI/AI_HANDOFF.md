# AI Handoff

## What This Project Is
CLI Python pour benchmarker des modeles AI sur le ST Edge AI Developer Cloud, avec mode simple et batch.

## Current Functional State
- Compute mode explicite conserve:
  - simple mode: auto/cpu/npu
  - batch mode: auto/cpu/npu/both pour boards NPU
- Politique memoire par defaut: interne (memory_pool vide)
- Bench trace complete: core_command + run_id + benchmark_id
- Storage principal: SQLite (resultats/resultats.db)
- CSV: export/compatibilite (resultats/resultats.csv)
- Erreurs actionnables: message + hint utilisateur
- Parsing robuste: safe round/int pour eviter erreurs sur strings

## File-Level Responsibilities
- main.py
  - menu principal, CLI args, benchmark simple, operations reference/history/export
- app/batch_benchmark.py
  - configuration batch interactive, expansion queue, execution multi-combinaisons
- app/cloud_api.py
  - HTTP calls cloud, validation options board, polling benchmark, parser metrics, logging JSONL
- app/results_manager.py
  - schema SQLite, migration CSV->DB, append/load/filter, tags reference, version history
- app/dashboard.py
  - visualisation matplotlib a partir de load_results
- app/diagnostic_report.py
  - export consolide par run_id (rows + events)

## Data Locations
- DB principal: resultats/resultats.db
- CSV export: resultats/resultats.csv
- logs JSONL: resultats/logs/benchmarks.jsonl

## Commands For Next AI
- Lancer menu interactif: python main.py
- Benchmark simple: python main.py --benchmark
- Batch: python main.py --batch
- Afficher resultats: python main.py --results
- Export CSV depuis SQLite: python main.py --export-csv
- Tag reference: python main.py --tag-reference <benchmark_id_or_run_id>
- Lire reference active: python main.py --active-reference
- Historique versions: python main.py --history-model <modele> --history-board <board>
- Tests: python run_ci_tests.py

## Safety Notes
- Ne pas supprimer les logs JSONL: utiles pour diagnostic backend.
- Ne pas rebasculer sur CSV-only: SQLite est la source de verite.
- Garder les choix compute mode visibles pour utilisateur (demande explicite).

## Where To Start If You Continue Development
1. Lire Documentation/Project/START_HERE.md
2. Lire Documentation/Project/AI/SKILLS_AND_CONTEXT.md
3. Valider l'etat avec python run_ci_tests.py
4. Appliquer changements incrementaux avec tests associes

## Version Workflow Policy
- Requirements intake file: Documentation/Project/Planning/REQUIREMENTS_BACKLOG.md
- Process file: Documentation/Project/Planning/REQUIREMENTS_WORKFLOW.md
- Version roadmap: Documentation/Project/Planning/VERSION_ROADMAP.md
- Changelog: Documentation/Project/Releases/CHANGELOG.md
- Branch model:
  - integration branch per version: release/vX.Y
  - feature branches merged into release/vX.Y
  - release branch merged to main at release close
- PR target policy:
  - feature PR -> release/vX.Y
  - release PR -> main

## Release Snapshot
- Active release branch: release/v1.1
- Legacy baseline to keep downloadable: v1.0.0 (Git tag + GitHub Release)
