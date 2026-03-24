# CLI Model Zoo Benchmark - ST Edge AI Developer Cloud

CLI Python pour lancer des benchmarks de modeles AI sur des boards STM32 via ST Edge AI Developer Cloud.

## Demarrage Rapide: Process Requirement + Dev
1. Ouvrir le point d'entree documentation: Documentation/Project/START_HERE.md
2. Rediger/choisir un requirement: Documentation/Project/Planning/REQUIREMENTS_BACKLOG.md
3. Suivre le guide d'iteration: Documentation/Project/REQUIREMENT_TO_RELEASE_GUIDE.md
4. Implementer dans le code (sources dans app/) puis lancer les tests:

```bash
python run_ci_tests.py
```

5. Mettre a jour changelog + note de release: Documentation/Project/Releases/

## Objectif
- Uploader un modele (.tflite/.onnx/.h5/.keras)
- Lancer benchmark sur board physique STM32
- Recuperer metriques (latence, RAM, ROM, MACC, etc.)
- Conserver les resultats de maniere robuste (SQLite)
- Visualiser et comparer les runs

## Etat Actuel (Important)
- Controle compute mode conserve pour utilisateur:
  - mode simple: auto/cpu/npu
  - mode batch: auto/cpu/npu/both pour boards NPU
- Politique memoire par defaut: interne (memory_pool vide)
- Erreurs actionnables: hints affiches dans les messages d'echec
- Tracabilite benchmark: core_command + run_id + benchmark_id
- Stockage principal: SQLite
- CSV conserve pour export/compatibilite

## Versioning Et Releases
- Branche courante de release: release/v1.1
- Baseline stable a conserver: v1.0.0 (a publier via tag + GitHub Release)
- Flux Git recommande:
  1. Ajouter/clarifier requirement dans Documentation/Project/Planning/REQUIREMENTS_BACKLOG.md
  2. Creer branche feature depuis release/vX.Y
  3. Ouvrir PR vers release/vX.Y
  4. Lancer regression complete: python run_ci_tests.py
  5. Finaliser release notes puis PR release/vX.Y -> main

## Workflow Requirements (Step-by-Step)
- Guide complet: Documentation/Project/REQUIREMENT_TO_RELEASE_GUIDE.md
- Guide Obsidian (demarrage rapide): Documentation/Project/OBSIDIAN_QUICK_START.md
- Backlog requirements: Documentation/Project/Planning/REQUIREMENTS_BACKLOG.md
- Process complet: Documentation/Project/Planning/REQUIREMENTS_WORKFLOW.md
- Roadmap versions: Documentation/Project/Planning/VERSION_ROADMAP.md
- Changelog: Documentation/Project/Releases/CHANGELOG.md
- Notes de release par version: Documentation/Project/Releases/
- Traceability requirements/tests: Documentation/Project/Traceability/REQUIREMENTS_TO_TESTS.md
- Traceability requirements/releases: Documentation/Project/Traceability/REQUIREMENTS_TO_RELEASES.md

## Installation
1. Installer dependances:

```bash
pip install -r requirements.txt
```

2. Lancer le menu principal:

```bash
python main.py
```

## Commandes Principales

```bash
python main.py --benchmark
python main.py --batch
python main.py --results
python main.py --results --board STM32H747I-DISCO
python main.py --visualize
python main.py --models
python main.py --list-core-versions
```

### Commandes Resultats / Reference / Versioning

```bash
python main.py --export-csv
python main.py --tag-reference <benchmark_id_or_run_id>
python main.py --active-reference
python main.py --history-model <modele> --history-board <board>
python main.py --history-model <modele> --history-board <board> --history-optimization balanced --history-compression lossless
```

### Tests

```bash
python run_ci_tests.py
```

## Donnees Et Stockage
- Base principale: resultats/resultats.db
- Export CSV: resultats/resultats.csv
- Logs benchmark JSONL: resultats/logs/benchmarks.jsonl

## Organisation Documentation
- Point d'entree documentation: Documentation/Project/START_HERE.md
- Handoff IA: Documentation/Project/AI/AI_HANDOFF.md
- Skills + contexte IA: Documentation/Project/AI/SKILLS_AND_CONTEXT.md
- Contexte projet detaille: Documentation/Project/Context/PROJECT_CONTEXT.md
- Historique projet: Documentation/Project/Planning/PROJECT_HISTORY.md
- Backlog requirements: Documentation/Project/Planning/REQUIREMENTS_BACKLOG.md
- Workflow requirements: Documentation/Project/Planning/REQUIREMENTS_WORKFLOW.md
- Roadmap versions: Documentation/Project/Planning/VERSION_ROADMAP.md
- Changelog: Documentation/Project/Releases/CHANGELOG.md
- Release v1.0.0: Documentation/Project/Releases/v1.0.0.md
- Docs ST Edge AI Core: Documentation/ST Edge AI Core 4.0/
- Synthese API Dev Cloud: Documentation/ST Edge AI Dev Cloud/ST_EdgeAI_Developer_Cloud_FULL.md

## Structure Projet (Vue Claire)

```text
STDev-CloudInstance/
|-- main.py
|-- app/
|   |-- __init__.py
|   |-- auth.py
|   |-- batch_benchmark.py
|   |-- cloud_api.py
|   |-- config.py
|   |-- dashboard.py
|   |-- diagnostic_report.py
|   |-- model_discovery.py
|   `-- results_manager.py
|-- tests/
|-- modeles/
|-- resultats/
|-- Obsidian/
|   |-- Dashboard/
|   |-- Requirements/
|   `-- Templates/
|-- Documentation/
|   |-- Project/
|   |   |-- START_HERE.md
|   |   |-- REQUIREMENT_TO_RELEASE_GUIDE.md
|   |   `-- OBSIDIAN_QUICK_START.md
|   |   |-- AI/
|   |   |   |-- AI_HANDOFF.md
|   |   |   `-- SKILLS_AND_CONTEXT.md
|   |   |-- Context/
|   |   |   `-- PROJECT_CONTEXT.md
|   |   |-- Releases/
|   |   |   |-- CHANGELOG.md
|   |   |   `-- v1.0.0.md
|   |   `-- Planning/
|   |       |-- PROJECT_HISTORY.md
|   |       |-- REQUIREMENTS_BACKLOG.md
|   |       |-- REQUIREMENTS_WORKFLOW.md
|   |       `-- VERSION_ROADMAP.md
|   |-- Traceability/
|   |   |-- REQUIREMENTS_TO_TESTS.md
|   |   `-- REQUIREMENTS_TO_RELEASES.md
|   |-- ST Edge AI Core 4.0/
|   `-- ST Edge AI Dev Cloud/
|-- README.md
|-- CONTRIBUTING.md
|-- .github/
|   `-- PULL_REQUEST_TEMPLATE.md
|-- CLAUDE.md  (redirect)
`-- PLAN.md    (redirect)
```

## Notes Pour Reprise IA
Pour une reprise rapide par une autre IA:
1. Lire Documentation/Project/START_HERE.md
2. Lire Documentation/Project/REQUIREMENT_TO_RELEASE_GUIDE.md
3. Lire Documentation/Project/AI/AI_HANDOFF.md
4. Executer python run_ci_tests.py
5. Continuer en gardant SQLite comme source de verite
