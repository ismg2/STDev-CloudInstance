# CLI Model Zoo Benchmark - ST Edge AI Developer Cloud

CLI Python pour lancer des benchmarks de modeles AI sur des boards STM32 via ST Edge AI Developer Cloud.

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
- Index central: Documentation/Project/INDEX.md
- Handoff IA: Documentation/Project/AI/AI_HANDOFF.md
- Skills + contexte IA: Documentation/Project/AI/SKILLS_AND_CONTEXT.md
- Contexte projet detaille: Documentation/Project/Context/PROJECT_CONTEXT.md
- Plan de developpement: Documentation/Project/Planning/DEVELOPMENT_PLAN.md
- Docs ST Edge AI Core: Documentation/ST Edge AI Core 4.0/
- Synthese API Dev Cloud: Documentation/ST Edge AI Dev Cloud/ST_EdgeAI_Developer_Cloud_FULL.md

## Structure Projet (Vue Claire)

```text
STDev-CloudInstance/
|-- main.py
|-- batch_benchmark.py
|-- cloud_api.py
|-- results_manager.py
|-- dashboard.py
|-- diagnostic_report.py
|-- model_discovery.py
|-- auth.py
|-- config.py
|-- tests/
|-- modeles/
|-- resultats/
|-- Documentation/
|   |-- Project/
|   |   |-- INDEX.md
|   |   |-- AI/
|   |   |   |-- AI_HANDOFF.md
|   |   |   `-- SKILLS_AND_CONTEXT.md
|   |   |-- Context/
|   |   |   `-- PROJECT_CONTEXT.md
|   |   `-- Planning/
|   |       `-- DEVELOPMENT_PLAN.md
|   |-- ST Edge AI Core 4.0/
|   `-- ST Edge AI Dev Cloud/
|-- README.md
|-- CLAUDE.md  (redirect)
`-- PLAN.md    (redirect)
```

## Notes Pour Reprise IA
Pour une reprise rapide par une autre IA:
1. Lire Documentation/Project/INDEX.md
2. Lire Documentation/Project/AI/AI_HANDOFF.md
3. Executer python run_ci_tests.py
4. Continuer en gardant SQLite comme source de verite
