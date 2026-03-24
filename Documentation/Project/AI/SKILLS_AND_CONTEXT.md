# Skills And Context Map

## Goal
Donner a une IA de reprise une vue immediate de "ou trouver quoi" dans ce repo.

## Core Context Files
- Documentation/Project/Context/PROJECT_CONTEXT.md: contexte produit complet, architecture, endpoints, workflow.
- Documentation/Project/Planning/PROJECT_HISTORY.md: plan historique des sessions.
- Documentation/Project/AI/AI_HANDOFF.md: etat technique actuel, conventions, commandes utiles.

## ST Documentation Sources
- Documentation/ST Edge AI Core 4.0/: documentation technique officielle HTML.
- Documentation/ST Edge AI Dev Cloud/ST_EdgeAI_Developer_Cloud_FULL.md: synthese API REST (user/file/stm32ai/benchmark/project).

## Code Entry Points
- main.py: CLI interactif + arguments directs.
- app/cloud_api.py: auth cloud calls, benchmark trigger/poll, parse resultats.
- app/results_manager.py: SQLite principal, migration CSV, tagging reference/versioning.
- app/batch_benchmark.py: orchestration multi-modeles/multi-boards/multi-options.

## Key Decisions Already Implemented
- Choix compute mode garde sous controle utilisateur (auto/cpu/npu/both selon contexte).
- Politique memoire par defaut: interne (memory_pool vide).
- Storage principal: SQLite (resultats/resultats.db), CSV conserve pour export/compatibilite.
- Erreurs actionnables: hints ecrits en console + status + JSONL.
- Parsing robuste: safe conversion/round pour eviter les erreurs de type string.
