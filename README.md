# CLI Model Zoo Benchmark — ST Edge AI Core 4.0

Script Python interactif pour **benchmarker tes modèles AI** sur des boards STM32 réelles
via le [ST Edge AI Developer Cloud](https://stedgeai-dc.st.com).

> Basé sur **ST Edge AI Core 4.0** — Documentation officielle incluse dans `Documentation/`

---

## Ce que fait ce projet

```
Tes modèles (.tflite / .onnx / .h5 / .keras)
             ↓
    Ce script CLI interactif
             ↓
  ST Edge AI Developer Cloud (API REST)
             ↓
  Boards STM32 physiques chez ST
    STM32H747I-DISCO, STM32N6570-DK...
             ↓
Résultats : inference time · RAM · ROM · MACC · Accuracy
             ↓
  CSV automatique + Graphiques comparatifs
```

---

## Prérequis

- **Python 3.8+**
- Un compte **myST** gratuit → [https://my.st.com](https://my.st.com)
- Connexion internet

---

## Installation

### 1. Récupérer le projet

```bash
git clone https://github.com/ismg2/STDev-CloudInstance.git
cd STDev-CloudInstance
```

Ou : GitHub → bouton vert **Code** → **Download ZIP** → extraire.

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Lancer

```bash
python main.py
```

---

## Utilisation

### Menu interactif (mode par défaut)

```bash
python main.py
```

```
╔══════════════════════════════════════════════════════╗
║       CLI Model Zoo Benchmark                        ║
║       ST Edge AI Core 4.0 — Developer Cloud          ║
╚══════════════════════════════════════════════════════╝

══════════════════════════════════════════════════
  MENU PRINCIPAL
══════════════════════════════════════════════════
  [1] Voir les modèles disponibles
  [2] Lancer un benchmark
  [3] Lancer un batch benchmark (multi-selection)
  [4] Voir les résultats
  [5] Visualiser les performances (graphiques)
  [6] Vérifier l'authentification
  [Q] Quitter
```

### Commandes directes

```bash
python main.py --benchmark                          # Benchmark guidé simple
python main.py --batch                              # Batch benchmark (multi-selection)
python main.py --results                            # Tableau des résultats
python main.py --results --board STM32H747I-DISCO   # Filtrer par board
python main.py --visualize                          # Graphiques
python main.py --models                             # Lister les modèles
```

### 🚀 Mode Batch (Nouveau!)

Le **batch benchmark** permet de tester **plusieurs modèles** sur **plusieurs boards** avec **plusieurs configurations** en une seule fois.

**Exemple d'utilisation :**

```bash
python main.py --batch
```

**Workflow guidé :**

1. **Sélection des modèles** (multi-selection avec checkboxes)
   - Navigue dans tes dossiers `modeles/`
   - Sélectionne un par un ou tous d'un coup
   - `[A]` = sélectionner tous · `[T]` = récursif · `[OK]` = valider

2. **Sélection des boards** (multi-selection)
   - Choisis une ou plusieurs boards STM32
   - `[A]` = sélectionner toutes · `[OK]` = valider

3. **Sélection des optimisations** (multi-selection)
   - `balanced`, `ram`, `time`, `size`
   - Par défaut : `balanced` pré-sélectionné

4. **Sélection des compressions** (multi-selection)
   - `none`, `lossless`, `low`, `medium`, `high`
   - Par défaut : `lossless` pré-sélectionné

5. **Confirmation et lancement**
   - Résumé du batch : `3 modèles × 2 boards × 2 opts × 1 comp = 12 benchmarks`
   - Barre de progression en temps réel (tqdm)
   - Rapport final avec statistiques (succès/erreurs, durée moyenne)

**Exemple concret :**
```
3 modèles (mobilenet_v1.tflite, resnet50.tflite, efficientnet.tflite)
× 2 boards (STM32H747I-DISCO, STM32N6570-DK)
× 2 optimisations (balanced, time)
× 1 compression (lossless)
= 12 benchmarks automatiques
```

Tous les résultats sont sauvegardés dans `resultats/resultats.csv` au fur et à mesure.

---

## Organiser ses modèles

Place tes fichiers dans `modeles/` avec des sous-dossiers :

```
modeles/
├── classification/
│   ├── mobilenet_v1.tflite
│   └── efficientnet_lite.tflite
├── detection/
│   └── ssd_mobilenet.onnx
└── custom/
    └── mon_reseau.h5
```

**Formats supportés :**

| Extension | Framework | Notes |
|-----------|-----------|-------|
| `.tflite` | TensorFlow Lite | Recommandé pour MCU |
| `.h5`     | Keras | Modèle complet |
| `.keras`  | Keras | Format SavedModel |
| `.onnx`   | ONNX | 102 opérateurs supportés |
| `.pb`     | TensorFlow | SavedModel format |

---

## Options de compilation ST Edge AI Core 4.0

Au moment d'un benchmark, le script te propose :

### Optimisation (`-O`)

| Option | Description |
|--------|-------------|
| `balanced` | **Défaut** — équilibre RAM et latence |
| `ram` | Minimise la consommation RAM |
| `time` | Minimise le temps d'inférence |
| `size` | Minimise la taille du modèle |

### Compression (`-c`)

| Option | Description |
|--------|-------------|
| `lossless` | **Défaut** — compression structurelle sans perte |
| `none` | Aucune compression |
| `low` | Facteur ~4× sur les couches denses |
| `medium` | Facteur ~8×, plus agressive |
| `high` | Compression extrême |

---

## Authentification (Bearer Token)

**Tes credentials ne sont jamais stockés en clair.**

Au premier lancement :
```
[Auth] Connexion au ST Edge AI Developer Cloud
  Email (username myST) : ton@email.com
  Mot de passe          : ••••••••
[Auth] Connexion réussie!
```

Le token Bearer OAuth2 est ensuite **mis en cache** dans `~/.stmai_token` et
**rafraîchi automatiquement** à chaque session. Tu ne retapes tes credentials que si
le token expire complètement (tous les ~30 jours).

### Automatisation (CI/CD)

```bash
export stmai_username="ton@email.com"
export stmai_password="ton_mot_de_passe"
python main.py --benchmark
```

> ⚠️ N'ajoute **jamais** ces variables dans le code ou dans un fichier versionné.

### Supprimer le token mis en cache

```bash
rm ~/.stmai_token
```

---

## Résultats CSV

Tous les résultats s'accumulent dans `resultats/resultats.csv` :

```
modele;dossier;type_framework;board;optimization;compression;
inference_time_ms;ram_ko;rom_ko;macc;params;accuracy;rmse;mae;l2r;date;status
```

| Colonne | Source | Description |
|---------|--------|-------------|
| `inference_time_ms` | `exec_time.duration_ms` | Temps d'inférence sur board réelle (ms) |
| `ram_ko` | `memory_footprint.activations + io + kernel_ram` | RAM totale (Ko) |
| `rom_ko` | `memory_footprint.weights + kernel_flash` | Flash/ROM totale (Ko) |
| `macc` | somme `nodes[].macc` | Opérations Multiply-Accumulate |
| `params` | somme `nodes[].params` | Nombre de paramètres |
| `accuracy` | `val_metrics[].acc` | Précision du modèle (%) |
| `rmse` | `val_metrics[].rmse` | Root Mean Square Error |
| `mae` | `val_metrics[].mae` | Mean Absolute Error |
| `l2r` | `val_metrics[].l2r` | Erreur relative L2 |

---

## Visualisation graphique

```bash
python main.py --visualize
```

Graphiques disponibles :
- **Temps d'inférence** — barres par modèle/board
- **RAM + ROM** — barres groupées comparatives
- **Accuracy** — si disponible dans les résultats
- **Dashboard complet** — tous les graphiques côte à côte
- **Filtrage par board**

---

## Structure du projet

```
STDev-CloudInstance/
├── main.py               # Menus CLI interactifs + argparse
├── auth.py               # Authentification OAuth2/SSO ST
├── cloud_api.py          # Client API REST STEdgeAI Developer Cloud
├── config.py             # Endpoints, paramètres CLI, chemins
├── model_discovery.py    # Navigation interactive dans modeles/
├── results_manager.py    # CSV résultats (pandas)
├── dashboard.py          # Graphiques matplotlib
├── requirements.txt      # Dépendances Python
├── Documentation/
│   └── ST Edge AI Core 4.0/   # Doc officielle ST (HTML)
├── modeles/              # ← Place tes modèles ici
└── resultats/            # ← CSV généré automatiquement
```

---

## Comment accéder à ses fichiers (cloud → local)

> **Contexte :** Ce projet tourne sur une instance cloud accessible via navigateur.
> Tes fichiers sont hébergés sur cette machine virtuelle ET sur GitHub.

### Schéma

```
TON NAVIGATEUR (Claude Code)
        │
        ▼
INSTANCE CLOUD  (/home/user/STDev-CloudInstance/)
        │
        │  git push
        ▼
GITHUB  (github.com/ismg2/STDev-CloudInstance)
        │
        │  git clone / Download ZIP
        ▼
TON PC LOCAL
```

### Récupérer le projet sur ton PC

**Option A — ZIP (débutant, sans Git)**
```
https://github.com/ismg2/STDev-CloudInstance
→ Bouton vert "Code" → Download ZIP → Extraire
```

**Option B — Git clone**
```bash
git clone https://github.com/ismg2/STDev-CloudInstance.git
```

**Option C — Éditer directement dans le navigateur**
```
https://github.dev/ismg2/STDev-CloudInstance
```
VS Code s'ouvre dans le navigateur, sans rien installer.

---

## Best practices Git — Que faire si le push échoue ?

| Erreur | Cause | Solution |
|--------|-------|----------|
| `403 Permission denied` | Token GitHub expiré ou mauvais remote | Vérifier : `git remote -v` · Re-auth GitHub |
| `rejected non-fast-forward` | Remote a avancé (commit d'un autre) | `git pull --rebase origin main` puis `git push` |
| `RPC failed HTTP 403` | Session proxy expirée (instance cloud) | Attendre et réessayer · La session se renouvelle |
| Push échoue mais commit fait | **Rien n'est perdu !** | `git log` confirme les commits locaux |

**Règle d'or : le push est idempotent. Si ça échoue, relance. Le commit local est toujours là.**

### Créer une sauvegarde portable si tout échoue

```bash
# Archive complète avec historique git
git bundle create ~/STDev-CloudInstance.bundle --all

# Restaurer sur un autre PC
git clone STDev-CloudInstance.bundle STDev-CloudInstance
```

---

## FAQ

**Q : Erreur `ModuleNotFoundError`**
```bash
pip install -r requirements.txt
```

**Q : Login échoue "identifiants invalides"**
→ Vérifie sur [my.st.com](https://my.st.com). Après 5 échecs le compte est bloqué temporairement.

**Q : Le benchmark prend 5-10 minutes**
→ Normal. Le modèle est compilé avec ST Edge AI Core, flashé sur une board STM32 physique chez ST, puis mesuré. La queue peut être longue aux heures de pointe.

**Q : Mon modèle est refusé**
→ Vérifie la compatibilité des opérateurs dans `Documentation/ST Edge AI Core 4.0/supported_ops_tflite.html`

**Q : Quelle version STEdgeAI est utilisée ?**
→ La dernière version disponible est détectée automatiquement au démarrage (actuellement **4.0.0**).

**Q : Changer de compte myST**
```bash
rm ~/.stmai_token
```

---

## Boards STM32 disponibles

Les boards sont récupérées automatiquement depuis le cloud. Exemples typiques :

| Board | Coeur | Cas d'usage |
|-------|-------|-------------|
| STM32H747I-DISCO | Cortex-M7 480 MHz | Référence MCU haute perf |
| STM32N6570-DK | Neural-ART NPU | Modèles avec accélérateur NPU |
| STM32MP257F-EV1 | Cortex-A35 Linux | Modèles MPU/Linux |
| NUCLEO-H743ZI2 | Cortex-M7 | Prototypage standard |
| STM32F746G-DISCO | Cortex-M7 216 MHz | MCU entrée de gamme |

---

## Liens

- [ST Edge AI Developer Cloud](https://stedgeai-dc.st.com)
- [Créer un compte myST](https://my.st.com)
- [STM32 AI Model Zoo](https://github.com/STMicroelectronics/stm32ai-modelzoo)
- [STMicroelectronics Model Zoo Services](https://github.com/STMicroelectronics/stm32ai-modelzoo-services)
- [ST Edge AI Core 4.0 — Doc locale](Documentation/ST%20Edge%20AI%20Core%204.0/index.html)
