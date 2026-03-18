# CLI Model Zoo Benchmark — ST Edge AI Developer Cloud

Script Python interactif pour **benchmarker tes modèles AI** (TFLite, ONNX, Keras, H5)
sur des boards STM32 réelles via le [ST Edge AI Developer Cloud](https://stedgeai-dc.st.com).

---

## Ce que fait ce projet

```
Tes modèles (.tflite, .onnx...)
        ↓
  Ce script CLI
        ↓
ST Edge AI Developer Cloud (API REST)
        ↓
Boards STM32 physiques chez ST
        ↓
Résultats : inference time, RAM, ROM, MACC
        ↓
Fichier CSV + Graphiques comparatifs
```

---

## Prérequis

- Python 3.8 ou supérieur
- Un compte **myST** gratuit → [https://my.st.com](https://my.st.com)
- Connexion internet

---

## Installation pas à pas

### 1. Récupérer le projet

**Méthode A — Télécharger le ZIP (débutant)**
```
GitHub → bouton vert "Code" → Download ZIP → extraire le dossier
```

**Méthode B — Git clone (recommandé)**
```bash
git clone https://github.com/ismg2/STDev-CloudInstance.git
cd STDev-CloudInstance
```

### 2. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

> Si tu as plusieurs versions de Python : `pip3 install -r requirements.txt`

### 3. Lancer le script

```bash
python main.py
```

> Sur Mac/Linux : `python3 main.py`

---

## Utilisation

### Menu interactif (mode par défaut)

```bash
python main.py
```

Tu arrives sur un menu guidé :
```
══════════════════════════════════════════════════════
  MENU PRINCIPAL
══════════════════════════════════════════════════════
  [1] Voir les modèles disponibles
  [2] Lancer un benchmark
  [3] Voir les résultats
  [4] Visualiser les performances (graphiques)
  [5] Vérifier l'authentification
  [Q] Quitter
```

### Commandes directes (mode ligne de commande)

```bash
python main.py --benchmark       # Lancer un benchmark directement
python main.py --results         # Afficher les résultats CSV
python main.py --visualize       # Ouvrir les graphiques
python main.py --models          # Lister les modèles disponibles
python main.py --results --board STM32H747I-DISCO   # Filtrer par board
```

---

## Organiser ses modèles

Place tes modèles dans le dossier `modeles/` avec des sous-dossiers pour t'organiser :

```
modeles/
├── classification/
│   ├── mobilenet_v1.tflite
│   └── efficientnet_lite.tflite
├── detection/
│   ├── ssd_mobilenet.tflite
│   └── yolo_tiny.onnx
└── custom/
    └── mon_modele.h5
```

**Formats supportés :** `.tflite`, `.h5`, `.onnx`, `.keras`, `.pb`

Le script navigue interactivement dans ces dossiers au moment de choisir quoi benchmarker.

---

## Authentification (Bearer Token)

**Tes credentials ne sont JAMAIS stockés en clair dans le code.**

Au premier lancement, le script demande ton email/mot de passe myST :
```
[Auth] Connexion au ST Edge AI Developer Cloud
  Email (username myST) : ton@email.com
  Mot de passe          : ********
```

Ensuite, le token Bearer est sauvegardé chiffré dans `~/.stmai_token` et
**réutilisé automatiquement** (refresh silencieux) lors des prochains lancements.

### Variables d'environnement (optionnel — pour automatisation)

```bash
export stmai_username="ton@email.com"
export stmai_password="ton_mot_de_passe"
python main.py --benchmark
```

> ⚠️ Ne jamais committer ces variables. Utilise un fichier `.env` non versionné.

---

## Résultats

Tous les résultats sont sauvegardés dans `resultats/resultats.csv` :

```
modele;dossier;board;inference_time_ms;ram_ko;rom_ko;macc;precision;date;status
mobilenet_v1.tflite;classification;STM32H747I-DISCO;12.3;245.5;890.2;28500000;N/A;2026-03-18 16:00:00;OK
```

| Colonne | Description |
|---------|-------------|
| `modele` | Nom du fichier modèle |
| `dossier` | Sous-dossier dans `modeles/` |
| `board` | Board STM32 utilisée |
| `inference_time_ms` | Temps d'inférence en millisecondes |
| `ram_ko` | Consommation RAM en Ko |
| `rom_ko` | Consommation Flash/ROM en Ko |
| `macc` | Nombre d'opérations (Multiply-Accumulate) |
| `precision` | Précision/accuracy si disponible |
| `date` | Horodatage du benchmark |
| `status` | OK ou message d'erreur |

---

## Visualisation graphique

```bash
python main.py --visualize
```

Ou depuis le menu `[4]`. Tu obtiens des graphiques comparatifs :

- **Temps d'inférence** — barres par modèle/board
- **Mémoire (RAM + ROM)** — barres groupées
- **Précision** — si des valeurs sont renseignées

---

## Structure du projet

```
STDev-CloudInstance/
├── main.py              # Point d'entrée — menus CLI interactifs
├── auth.py              # Authentification OAuth2/Bearer (ST SSO)
├── cloud_api.py         # Client API REST STEdgeAI Developer Cloud
├── config.py            # Endpoints, chemins, configuration
├── model_discovery.py   # Navigation interactive dans modeles/
├── results_manager.py   # Lecture/écriture CSV des résultats
├── dashboard.py         # Graphiques matplotlib
├── requirements.txt     # Dépendances Python
├── modeles/             # ← Mets tes modèles ici
└── resultats/           # ← CSV généré automatiquement ici
```

---

## FAQ

**Q : J'ai une erreur `ModuleNotFoundError`**
```bash
pip install -r requirements.txt
```

**Q : Le login échoue avec "identifiants invalides"**
→ Vérifie ton compte sur [my.st.com](https://my.st.com). Après 5 échecs, le compte est bloqué temporairement.

**Q : Comment supprimer le token sauvegardé (pour changer de compte) ?**
```bash
rm ~/.stmai_token
```

**Q : Le benchmark est lent (>5 minutes)**
→ Normal. Le modèle est uploadé, compilé, flashé sur une vraie board STM32 chez ST, puis mesuré. La queue peut être longue.

**Q : Mon modèle `.onnx` n'est pas accepté**
→ Vérifie que ton modèle est compatible avec STEdgeAI Core. Certains opérateurs ne sont pas supportés sur MCU.

**Q : Puis-je utiliser le script sans connexion internet ?**
→ Non. Le benchmark se passe sur les serveurs ST.

---

## Boards STM32 disponibles

Les boards disponibles sont récupérées automatiquement depuis le cloud au lancement.
Exemples typiques :

| Board | CPU | Usage |
|-------|-----|-------|
| STM32H747I-DISCO | Cortex-M7 480MHz | Référence |
| STM32N6570-DK | Neural-ART NPU | Modèles NPU |
| STM32MP257F-EV1 | Cortex-A35 | Linux/MPU |
| NUCLEO-H743ZI2 | Cortex-M7 | Prototypage |

---

## Accéder à ce projet depuis son poste (Cloud → Local)

Ce projet tourne sur une **instance cloud** (machine virtuelle accessible via navigateur).
Pour travailler dessus depuis ton ordinateur :

### Option 1 — Télécharger le ZIP depuis GitHub
```
https://github.com/ismg2/STDev-CloudInstance
→ Code → Download ZIP
```

### Option 2 — Cloner avec Git
```bash
git clone https://github.com/ismg2/STDev-CloudInstance.git
```

### Option 3 — VS Code + extension GitHub (sans Git installé)
1. Ouvre [github.dev/ismg2/STDev-CloudInstance](https://github.dev/ismg2/STDev-CloudInstance)
2. Un VS Code dans le navigateur s'ouvre — tu peux éditer directement

### Best practices quand le push Git échoue

| Problème | Cause probable | Solution |
|----------|----------------|----------|
| `403 Permission denied` | Token GitHub expiré / mauvaise config remote | Recheck le remote : `git remote -v` |
| `rejected non-fast-forward` | La branche distante a avancé | `git pull --rebase` puis `git push` |
| Push impossible mais commits faits | Tout est sauvé localement | `git bundle create backup.bundle --all` → fichier portable |
| Perte de connexion pendant le push | Réseau | `git push` est idempotent, relance simplement |

**Règle d'or : si le push échoue, les commits locaux sont intacts. `git log` pour vérifier.**

---

## Liens utiles

- [ST Edge AI Developer Cloud](https://stedgeai-dc.st.com)
- [Créer un compte myST](https://my.st.com)
- [STM32 Model Zoo](https://github.com/STMicroelectronics/stm32ai-modelzoo)
- [Documentation STEdgeAI](https://wiki.st.com/stm32mcu/wiki/AI:Getting_started_with_ST_Edge_AI_Developer_Cloud)
