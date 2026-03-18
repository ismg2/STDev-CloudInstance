# Contexte Projet - CLI Model Zoo Benchmark (ST Edge AI Core 4.0)

## Vue d'ensemble

**Script Python CLI interactif pour benchmarker des modèles AI sur des boards STM32 physiques** via l'API REST du [ST Edge AI Developer Cloud](https://stedgeai-dc.st.com).

### Objectif
Permettre aux développeurs de tester leurs modèles AI (TensorFlow Lite, ONNX, Keras) sur du **hardware STM32 réel** hébergé chez STMicroelectronics, sans avoir besoin de posséder physiquement les boards.

### Flux de travail
```
Modèles locaux (.tflite/.onnx/.h5/.keras)
           ↓
    CLI interactif (ce projet)
           ↓
ST Edge AI Developer Cloud (API REST)
           ↓
Boards STM32 physiques (STM32H747I-DISCO, STM32N6570-DK, etc.)
           ↓
Résultats : inference time · RAM · ROM · MACC · Accuracy
           ↓
Export CSV + Graphiques comparatifs (matplotlib)
```

---

## Architecture du projet

### Fichiers principaux

| Fichier | Rôle | Technologies |
|---------|------|--------------|
| `main.py` | Point d'entrée CLI avec menus interactifs | argparse, menus guidés |
| `auth.py` | Authentification OAuth2/SSO ST | Gestion Bearer token, cache `~/.stmai_token` |
| `cloud_api.py` | Client API REST STEdgeAI Developer Cloud | requests, polling async |
| `config.py` | Configuration (endpoints, paramètres CLI) | Constantes, mapping CLI ST Edge AI Core 4.0 |
| `model_discovery.py` | Navigation interactive dans `modeles/` | Scan récursif, sélection guidée |
| `batch_benchmark.py` | **[NOUVEAU]** Batch benchmark multi-selection | Multi-select boards/opts/comps, queue, tqdm |
| `results_manager.py` | Gestion des résultats CSV | pandas, append incrémental |
| `dashboard.py` | Visualisation graphique | matplotlib (barres, comparatifs) |

### Dossiers

```
STDev-CloudInstance/
├── main.py                    # CLI entry point
├── auth.py                    # OAuth2/Bearer authentication
├── cloud_api.py               # REST API client
├── config.py                  # Endpoints & CLI params
├── model_discovery.py         # Model scanner & selector
├── batch_benchmark.py         # Batch benchmark multi-selection
├── results_manager.py         # CSV results manager
├── dashboard.py               # Matplotlib visualizations
├── requirements.txt           # Dependencies (requests, pandas, matplotlib, tqdm)
├── CLAUDE.md                  # Contexte complet du projet (ce fichier)
├── README.md                  # Documentation utilisateur complète
├── PLAN.md                    # Plan de développement (5 sessions)
├── Documentation/
│   └── ST Edge AI Core 4.0/   # Doc officielle ST (HTML, 70+ fichiers)
├── modeles/                   # Modèles utilisateur (organisés par sous-dossiers)
│   ├── classification/
│   ├── detection/
│   └── custom/
└── resultats/                 # Résultats exportés
    └── resultats.csv          # CSV incrémental (historique complet)
```

---

## Technologies & dépendances

### Stack Python
- **requests** ≥2.31.0 — HTTP client pour API REST
- **pandas** ≥2.0.0 — Gestion CSV des résultats
- **matplotlib** ≥3.7.0 — Graphiques comparatifs
- **tqdm** ≥4.65.0 — Barres de progression CLI

### Formats de modèles supportés
| Extension | Framework | Notes |
|-----------|-----------|-------|
| `.tflite` | TensorFlow Lite | Recommandé pour MCU |
| `.h5` | Keras | Modèle complet |
| `.keras` | Keras | Format SavedModel |
| `.onnx` | ONNX | 102 opérateurs supportés (voir doc) |
| `.pb` | TensorFlow | SavedModel format |

---

## API REST — Endpoints utilisés

### Base URL
```
https://stedgeai-dc.st.com/
```

### Authentification
- **SSO ST** : `https://sso.st.com`
- **Client ID** : `oidc_prod_client_app_stm32ai`
- **Login callback** : `/api/user_service/login/callback`
- **Token refresh** : `/api/user_service/login/refresh`
- **Token local** : `~/.stmai_token` (cache Bearer, refresh auto)

### Services principaux

#### 1. FileService (`/api/file`)
- **Upload modèle** : `POST /api/file/files/models`
- **Upload validation inputs** : `POST /api/file/files/validation/inputs`
- **Upload validation outputs** : `POST /api/file/files/validation/outputs`
- **Download generated files** : `GET /api/file/files/generated`

#### 2. STM32AI Service (`/api/{version}/stm32ai`)
- **Analyze** : `POST /api/{version}/stm32ai/analyze`
- **Generate** : `POST /api/{version}/stm32ai/generate`
- **Validate** : `POST /api/{version}/stm32ai/validate`

#### 3. Benchmark Service (`/api/benchmark`)
- **List boards** : `GET /api/benchmark/boards`
- **Submit benchmark** : `POST /api/benchmark`
- **Polling résultats** : polling GET sur URL callback

#### 4. Versions
- **Versions disponibles** : `GET /assets/versions.json`
- **Version courante** : `4.0.0` (ST Edge AI Core 4.0)

---

## Paramètres CLI — ST Edge AI Core 4.0

### Optimisation (`-O` / `--optimization`)
| Valeur | Description |
|--------|-------------|
| `balanced` | **Défaut** — Équilibre RAM et temps d'inférence |
| `ram` | Minimise l'utilisation RAM |
| `time` | Minimise la latence d'inférence |
| `size` | Minimise la taille du modèle |

### Compression (`-c` / `--compression`)
| Valeur | Description |
|--------|-------------|
| `lossless` | **Défaut** — Compression structurelle sans perte |
| `none` | Aucune compression |
| `low` | Facteur ~4× sur couches denses |
| `medium` | Facteur ~8×, plus agressive |
| `high` | Compression extrême |

### Types de données
- `float32`, `int8`, `uint8` (pour `--input-data-type` / `--output-data-type`)

---

## Métriques retournées

### Depuis l'API (evaluation_metrics.html)
- **acc** — Accuracy (classification)
- **rmse** — Root Mean Square Error
- **mae** — Mean Absolute Error
- **l2r** — L2 relative error
- **snr** — Signal to Noise Ratio
- **nse** — Nash-Sutcliffe efficiency
- **f1_score** — F1 score
- **variance** — Variance

### Colonnes CSV (`resultats/resultats.csv`)
```csv
modele;dossier;type_framework;board;optimization;compression;
inference_time_ms;ram_ko;rom_ko;macc;params;accuracy;rmse;mae;l2r;date;status
```

| Colonne | Source API | Description |
|---------|------------|-------------|
| `inference_time_ms` | `exec_time.duration_ms` | Temps d'inférence mesuré sur board réelle (ms) |
| `ram_ko` | `memory_footprint.activations + io + kernel_ram` | RAM totale (Ko) |
| `rom_ko` | `memory_footprint.weights + kernel_flash` | Flash/ROM totale (Ko) |
| `macc` | somme `nodes[].macc` | Opérations Multiply-Accumulate |
| `params` | somme `nodes[].params` | Nombre de paramètres du modèle |
| `accuracy` | `val_metrics[].acc` | Précision du modèle (%) |
| `rmse` | `val_metrics[].rmse` | Root Mean Square Error |
| `mae` | `val_metrics[].mae` | Mean Absolute Error |
| `l2r` | `val_metrics[].l2r` | Erreur relative L2 |

---

## Boards STM32 disponibles

Les boards sont récupérées dynamiquement depuis `/api/benchmark/boards`. Exemples typiques :

| Board | Coeur | RAM | Flash | Cas d'usage |
|-------|-------|-----|-------|-------------|
| STM32H747I-DISCO | Cortex-M7 480 MHz | 1 MB | 2 MB | Référence MCU haute perf |
| STM32N6570-DK | Neural-ART NPU | - | - | Modèles avec accélérateur NPU |
| STM32MP257F-EV1 | Cortex-A35 Linux | - | - | Modèles MPU/Linux |
| NUCLEO-H743ZI2 | Cortex-M7 | 1 MB | 2 MB | Prototypage standard |
| STM32F746G-DISCO | Cortex-M7 216 MHz | 340 KB | 1 MB | MCU entrée de gamme |

---

## Flux d'exécution détaillé

### 1. Authentification
```python
# auth.py
1. Vérifier si token existe dans ~/.stmai_token
2. Si non → Login interactif (username/password via prompt)
3. Si oui → Vérifier validité token
4. Si expiré → Refresh automatique via /login/refresh
5. Retourner Bearer token valide
```

### 2. Découverte de modèles
```python
# model_discovery.py
1. Scanner récursivement modeles/ (.tflite, .h5, .onnx, .keras, .pb)
2. Organiser par sous-dossiers (classification/, detection/, etc.)
3. Afficher menu interactif de sélection
4. Retourner chemin du modèle sélectionné + métadonnées
```

### 3. Benchmark
```python
# cloud_api.py
1. Upload modèle → POST /api/file/files/models
2. Récupérer liste boards → GET /api/benchmark/boards
3. Sélection board cible (menu interactif)
4. Submit benchmark → POST /api/benchmark
   - Paramètres : optimization, compression, board_name, model_path
5. Polling résultats (wait_for_run)
   - GET callback URL toutes les 5s
   - Timeout 600s
6. Parser résultats JSON (inference_time, memory_footprint, nodes, val_metrics)
```

### 4. Export résultats
```python
# results_manager.py
1. Créer DataFrame pandas avec colonnes standardisées
2. Append dans resultats/resultats.csv (mode incrémental)
3. Pas d'écrasement des anciens résultats
4. Horodatage automatique (colonne "date")
```

### 5. Visualisation
```python
# dashboard.py
1. Charger resultats/resultats.csv avec pandas
2. Filtres disponibles : par board, par dossier de modèles
3. Graphiques matplotlib :
   - Barres comparatives inference_time_ms
   - Barres groupées RAM/ROM
   - Accuracy (si disponible)
   - Dashboard complet (subplot 2x2)
```

---

## Commandes CLI disponibles

### Mode interactif (par défaut)
```bash
python main.py
```
Affiche menu avec options :
1. Voir les modèles disponibles
2. Lancer un benchmark
3. Voir les résultats
4. Visualiser les performances (graphiques)
5. Vérifier l'authentification
Q. Quitter

### Commandes directes (argparse)
```bash
python main.py --benchmark                          # Lancer benchmark guidé simple
python main.py --batch                              # Batch benchmark (multi-selection)
python main.py --results                            # Afficher tableau résultats
python main.py --results --board STM32H747I-DISCO   # Filtrer par board
python main.py --visualize                          # Ouvrir dashboard graphique
python main.py --models                             # Lister modèles disponibles
```

---

## Batch Benchmark (Fonctionnalité clé)

### Vue d'ensemble

Le **batch benchmark** permet de tester **plusieurs modèles** sur **plusieurs boards** avec **plusieurs configurations** en une seule exécution.

**Problème résolu :** Avant, pour tester 10 modèles sur 3 boards avec 2 optimisations = 60 runs manuels. Maintenant : **1 seule commande**.

### Workflow interactif guidé

```bash
python main.py --batch
```

**Étapes :**

1. **Sélection modèles** (multi-select avec checkboxes ✓)
   - Navigation dans `modeles/` comme pour le benchmark simple
   - `[1]` à `[N]` : Toggle sélection d'un modèle
   - `[A]` : Sélectionner tous les modèles du dossier
   - `[T]` : Sélectionner tous récursivement
   - `[V]` : Voir la sélection actuelle
   - `[OK]` : Valider

2. **Sélection boards** (multi-select)
   - Liste des boards disponibles (depuis cloud API)
   - `[1]` à `[N]` : Toggle sélection d'un board
   - `[A]` : Sélectionner tous les boards
   - `[C]` : Effacer la sélection
   - `[OK]` : Valider

3. **Sélection optimisations** (multi-select, défaut: `balanced`)
   - `balanced`, `ram`, `time`, `size`
   - Pré-sélection : `balanced`
   - `[A]` : Sélectionner toutes
   - `[D]` : Reset au défaut uniquement
   - `[OK]` : Valider

4. **Sélection compressions** (multi-select, défaut: `lossless`)
   - `none`, `lossless`, `low`, `medium`, `high`
   - Pré-sélection : `lossless`
   - Même interface que optimisations

5. **Confirmation et exécution**
   - Résumé :
     ```
     Modèles       : 3
     Boards        : 2
     Optimisations : 2
     Compressions  : 1
     ──────────────────
     TOTAL BENCHMARKS : 12
     ```
   - `(O/n)` pour lancer
   - Barre de progression temps réel (tqdm)
   - Gestion d'erreurs : continue même si un benchmark échoue
   - Rapport final : succès/erreurs, durée totale, temps moyen/run

### Exemple concret

```
Sélection :
  - 3 modèles : mobilenet_v1.tflite, resnet50.tflite, efficientnet.tflite
  - 2 boards : STM32H747I-DISCO, STM32N6570-DK
  - 2 optimisations : balanced, time
  - 1 compression : lossless

Queue générée :
  mobilenet_v1.tflite × STM32H747I-DISCO × balanced × lossless
  mobilenet_v1.tflite × STM32H747I-DISCO × time × lossless
  mobilenet_v1.tflite × STM32N6570-DK × balanced × lossless
  mobilenet_v1.tflite × STM32N6570-DK × time × lossless
  resnet50.tflite × STM32H747I-DISCO × balanced × lossless
  ... (12 benchmarks au total)

Exécution :
  Benchmarks: 100%|██████████████| 12/12 [45:30<00:00, 227s/run]

Résultat :
  Succès  : 11 (91.7%)
  Erreurs : 1 (8.3%)
  Durée   : 45.5 minutes (227s/run en moyenne)
```

### Implémentation technique

**Fichier :** `batch_benchmark.py`

**Fonctions principales :**

```python
def select_multiple_boards(boards: list) -> list:
    """Multi-select interactif pour boards."""
    # Interface avec checkboxes, [A]ll, [C]lear, [OK]

def select_multiple_options(title: str, options: dict, default_key: str) -> list:
    """Multi-select générique pour optimizations/compressions."""
    # Interface avec checkboxes, [A]ll, [D]efault, [C]lear, [OK]

def interactive_batch_benchmark() -> dict | None:
    """Workflow complet guidé (4 étapes)."""
    # Retourne config dict ou None si annulé

def run_batch_benchmark():
    """Exécution du batch avec tqdm et gestion d'erreurs."""
    # Build queue, run avec progress bar, stats finales
```

**Intégration dans `main.py` :**
- Menu principal : option `[3]`
- CLI argparse : `--batch`

---

## État actuel du développement

### ✅ Fonctionnalités implémentées
- Authentification OAuth2/Bearer avec cache token
- Scanner de modèles avec navigation interactive
- **Batch benchmark** avec multi-sélection guidée (modèles, boards, opts, comps)
- Client API REST complet (FileService, BenchmarkService, STM32AIService)
- Export CSV incrémental des résultats
- Dashboard matplotlib avec graphiques comparatifs
- CLI interactif + mode argparse
- Documentation complète (README.md, PLAN.md, CLAUDE.md)
- Gestion des erreurs et timeouts
- Support multi-boards
- Polling async des benchmarks
- Barre de progression temps réel (tqdm)

### 📋 Plan de développement (PLAN.md)
- **Session 1** ✅ : Scaffolding & Authentification
- **Session 2** ✅ : Découverte des modèles & Menus CLI
- **Session 3** ✅ : Intégration API STEdgeAI Developer Cloud
- **Session 4** ✅ : Gestion des résultats CSV
- **Session 5** ✅ : Dashboard de visualisation

---

## Améliorations possibles

### 1. ~~**Batch Benchmark**~~ ✅ IMPLÉMENTÉ
Fonctionnalité batch avec multi-sélection interactive maintenant disponible. Voir section "Batch Benchmark" ci-dessus.

---

### 2. **Model Validator** 🎯 PROCHAINE PRIORITÉ
**Pourquoi :** Éviter les uploads inutiles de modèles incompatibles.

**Fonctionnalité :**
- Vérification pré-upload :
  - Opérateurs supportés (cross-check avec `Documentation/ST Edge AI Core 4.0/supported_ops_*.html`)
  - Taille du modèle (< 100 MB recommandé)
  - Format du fichier valide
- Rapport de compatibilité avant benchmark

---

### 3. **Skill : Results Analyzer**
**Pourquoi :** Les résultats CSV s'accumulent mais pas d'analyse avancée.

**Fonctionnalité :**
- Comparaisons croisées :
  - Quel modèle a le meilleur ratio accuracy/inference_time ?
  - Quel modèle est le plus efficace en RAM ?
- Graphiques avancés :
  - Pareto front (accuracy vs latency)
  - Heatmaps (modèles × boards)
- Export rapport PDF/HTML

---

### 4. **Skill : Benchmark Monitor**
**Pourquoi :** Les benchmarks peuvent prendre 5-10 minutes. Pas de monitoring en temps réel.

**Fonctionnalité :**
- Websocket/polling live du statut
- Notification fin de benchmark (desktop, email, webhook)
- Dashboard temps réel (Streamlit/Gradio)

---

### 5. **Skill : Model Optimizer Assistant**
**Pourquoi :** Aider à améliorer les modèles avant benchmark.

**Fonctionnalité :**
- Suggestions d'optimisation basées sur les résultats passés
- Quantization automatique (float32 → int8)
- Pruning suggestions
- Conversion automatique (Keras → TFLite optimisé)

---

## Liens utiles

- [ST Edge AI Developer Cloud](https://stedgeai-dc.st.com)
- [Créer un compte myST](https://my.st.com)
- [STM32 AI Model Zoo (officiel)](https://github.com/STMicroelectronics/stm32ai-modelzoo)
- [STM32 AI Model Zoo Services (backend référence)](https://github.com/STMicroelectronics/stm32ai-modelzoo-services)
- [Doc locale ST Edge AI Core 4.0](Documentation/ST%20Edge%20AI%20Core%204.0/index.html)

---

## Notes techniques

### Sécurité
- ⚠️ **Ne jamais committer le token** : `~/.stmai_token` est en dehors du repo
- ⚠️ **Ne jamais hardcoder les credentials** : utiliser variables d'env ou prompt interactif
- ✅ Token Bearer auto-refresh transparent

### Performance
- Polling benchmark : interval 5s, timeout 600s (10 min max)
- Cache token : évite re-login à chaque exécution
- CSV incrémental : pas de rechargement complet à chaque ajout

### Limitations connues
- Pas de support multi-utilisateur (token unique)
- Pas de parallélisation des benchmarks (queue séquentielle)
- Graphiques matplotlib basiques (pas de dashboard web interactif)
- Pas de validation offline des opérateurs (nécessite upload pour savoir si compatible)

---

**Dernière mise à jour :** 2026-03-18
**Version ST Edge AI Core :** 4.0.0
**Auteur :** ismg2 (Ismail Guedir)
