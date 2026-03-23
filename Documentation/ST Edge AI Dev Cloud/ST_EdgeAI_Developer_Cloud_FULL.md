# ST Edge AI Developer Cloud (STEDGEAI-DC)
> Documentation complète de la plateforme et de ses APIs REST  
> Source : fichiers HTML officiels stedgeai-dc.st.com · Année : 2026 · STMicroelectronics

---

## TABLE DES MATIÈRES

1. [Vue d'ensemble de la plateforme](#1-vue-densemble-de-la-plateforme)
2. [Navigation et sections de la documentation](#2-navigation-et-sections-de-la-documentation)
3. [Architecture des micro-services REST](#3-architecture-des-micro-services-rest)
4. [API — User Service](#4-api--user-service)
5. [API — File Service](#5-api--file-service)
6. [API — STM32AI Service](#6-api--stm32ai-service)
7. [API — Quantization Service](#7-api--quantization-service)
8. [API — Benchmark Service](#8-api--benchmark-service)
9. [API — Project Service](#9-api--project-service)
10. [Authentification et licence](#10-authentification-et-licence)
11. [Écosystème et ressources associées](#11-écosystème-et-ressources-associées)
12. [Résumé des endpoints par service](#12-résumé-des-endpoints-par-service)

---

## 1. VUE D'ENSEMBLE DE LA PLATEFORME

| Champ | Valeur |
|---|---|
| **Nom** | ST Edge AI Developer Cloud |
| **Abréviation** | STEDGEAI-DC |
| **URL plateforme** | https://stedgeai-dc.st.com/ |
| **Spécification API** | OpenAPI 3.0.x (OAS3) |
| **Base URL serveurs** | https://stm32ai-cs.st.com/ |
| **Authentification** | OIDC (OpenID Connect) via MyST · Tokens JWT |
| **Coût** | Gratuit, y compris usage commercial |
| **Infrastructure** | Microsoft Azure Cloud |

### Description
ST Edge AI Developer Cloud est une plateforme en ligne permettant d'**analyser, optimiser, valider, quantifier, benchmarker et générer** du code embarqué C pour des modèles d'intelligence artificielle destinés aux dispositifs STMicroelectronics (STM32 MCU/MPU/NPU, Stellar automotive, MEMS ISPU).

Tous les services sont exposés via une **API REST OpenAPI 3.0** permettant l'intégration dans des pipelines MLOps/CI-CD. Un **wrapper Python** est également disponible.

---

## 2. NAVIGATION ET SECTIONS DE LA DOCUMENTATION

La plateforme propose les sections de navigation suivantes :

| Section | Description |
|---|---|
| **Home** | Page d'accueil de la plateforme |
| **Documentation → User Manual** | Manuel utilisateur complet |
| **Documentation → ST Edge AI Core Documentation** | Documentation du moteur ST Edge AI Core |
| **Documentation → APIs** | Documentation interactive OpenAPI (Swagger UI) de chaque service REST |
| **Documentation → Python Interface** | Interface et wrapper Python pour l'API |
| **Settings** | Paramètres utilisateur |

### Menu API Selection (sous-sections APIs)
La documentation interactive Swagger expose **6 micro-services** distincts :

1. User Service
2. File Service
3. STM32AI Service
4. Quantization Service
5. Benchmark Service
6. Project Service

---

## 3. ARCHITECTURE DES MICRO-SERVICES REST

```
stedgeai-dc.st.com (Frontend Angular)
        │
        ├── /api/user_service/     → User Service
        ├── /api/file/             → File Service
        ├── /api/stm32ai/          → STM32AI Service
        ├── /api/quantize/         → Quantization Service
        ├── /api/benchmark/        → Benchmark Service
        └── /api/project/          → Project Service

Base serveur backend : https://stm32ai-cs.st.com/
```

Chaque micro-service expose sa propre documentation OpenAPI 3.0 accessible via :
- **HTML Swagger UI** : `GET /docs`
- **JSON brut** : `GET /api`

---

## 4. API — USER SERVICE

**Titre :** User Service API  
**Version :** 1.0  
**Spec :** OAS3  
**URL spec :** `https://stedgeai-dc.st.com/api/user_service//api`  
**Serveur :** `https://stm32ai-cs.st.com/api/user_service`  
**Description :** Endpoints pour authentifier un utilisateur basé sur un token fourni dans la requête.

---

### 4.1 Documentation

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/docs` | Retourne la doc OpenAPI 3.0.x en HTML (Swagger UI) |
| `GET` | `/api` | Retourne la doc OpenAPI 3.0.x en JSON |

---

### 4.2 Misc

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/assets/{asset}` | Récupère un utilisateur par ID |

---

### 4.3 Login API

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/login/callback` | Reçoit un code MyST + URL callback, retourne un `TokenSet` |
| `GET` | `/login/callback` | Reçoit un code MyST + URL callback, retourne un `TokenSet` |
| `POST` | `/login/refresh` | Reçoit un refresh token, retourne un nouveau `TokenSet` |
| `POST` | `/login/authenticate` | Récupère les informations de l'utilisateur |
| `GET` | `/login/authenticate` | Vérifie si le token est valide |

---

### 4.4 User API

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/user/license` | Pour chaque licence, retourne la date d'acceptation (si acceptée) |
| `POST` | `/user/license` | Accepte une licence |
| `GET` | `/user/user` | Vérifie si le token est valide |

---

### 4.5 Schemas (User Service)

| Schema | Description |
|---|---|
| `PostAuthenticate` | Corps de la requête d'authentification |
| `PostAuthenticateResponse` | Réponse de l'authentification |
| `PostCallback` | Corps du callback MyST |
| `TokenSet` | Ensemble de tokens OIDC (access, refresh, id token) |

---

## 5. API — FILE SERVICE

**Titre :** File Service API  
**Version :** 1.0  
**Spec :** OAS3  
**URL spec :** `https://stedgeai-dc.st.com/api/file//api`  
**Serveur :** `https://stm32ai-cs.st.com/api/file/`  
**Description :** Endpoint pour uploader, télécharger et supprimer des modèles et fichiers de validation dans Azure Storage.

---

### 5.1 Models API

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/files/models` | Liste les modèles disponibles dans Azure Storage |
| `POST` | `/files/models` | Upload un modèle dans Azure Storage |
| `GET` | `/files/models/{filename}` | Télécharge un modèle depuis Azure Storage |
| `DELETE` | `/files/models/{filename}` | Supprime un modèle dans Azure Storage |

---

### 5.2 Validation Inputs API

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/files/validation/inputs` | Liste les fichiers d'entrée de validation disponibles |
| `POST` | `/files/validation/inputs` | Upload un fichier d'entrée de validation |
| `GET` | `/files/validation/inputs/{filename}` | Télécharge un fichier d'entrée de validation |
| `DELETE` | `/files/validation/inputs/{filename}` | Supprime un fichier d'entrée de validation |

---

### 5.3 Validation Outputs API

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/files/validation/outputs` | Liste les fichiers de sortie de validation disponibles |
| `POST` | `/files/validation/outputs` | Upload un fichier de sortie de validation |
| `GET` | `/files/validation/outputs/{filename}` | Télécharge un fichier de sortie de validation |
| `DELETE` | `/files/validation/outputs/{filename}` | Supprime un fichier de sortie de validation |

---

## 6. API — STM32AI SERVICE

**Titre :** STM32AI Service API  
**Version :** 1.0  
**Spec :** OAS3  
**URL spec :** `https://stedgeai-dc.st.com/api//stm32ai/api`  
**Serveur :** `https://stm32ai-cs.st.com/api/stm32ai`  
**Description :** Endpoint pour analyser et valider des modèles via le runtime STM32AI.

---

### 6.1 Analyze API

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analyze` | Exécute la commande STM32AI Analyze (analyse du modèle : RAM, Flash, MACCs) |

---

### 6.2 Validate API

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/api/validate` | Exécute la commande STM32AI Validate (validation du modèle sur cible) |

---

### 6.3 Generate API

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/api/generate` | Exécute la commande STM32AI Generate (génération du code C embarqué) |

---

### 6.4 Runtime API endpoint

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/api/run/{id}` | Retourne les résultats STM32AI pour un job donné (par ID) |
| `GET` | `/api/previous/{hash}` | Pour un hash de fichier donné, retourne un tableau des résultats précédents |

---

## 7. API — QUANTIZATION SERVICE

**Titre :** Quantize Service API  
**Version :** 1.0  
**Spec :** OAS3  
**URL spec :** `https://stedgeai-dc.st.com/api/quantize//api`  
**Serveur :** `https://stm32ai-cs.st.com/api/quantize/`  
**Description :** Service de quantification pour modèles Keras et ONNX.

---

### 7.1 Quantize API

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/quantize` | Quantifie un modèle ONNX ou Keras (endpoint générique) |
| `POST` | `/quantize/onnx_runtime` | Quantifie spécifiquement un modèle ONNX |
| `POST` | `/quantize/tflite` | Quantifie spécifiquement un modèle Keras (vers TFLite INT8) |

---

## 8. API — BENCHMARK SERVICE

**Titre :** Benchmark Service API  
**Version :** 1.0  
**Spec :** OAS3  
**URL spec :** `https://stedgeai-dc.st.com/api/benchmark//api`  
**Serveur :** `https://stm32ai-cs.st.com/api/benchmark`  
**Description :** Endpoint pour planifier un benchmark sur des boards STM32 réelles hébergées dans le board farm ST.

---

### 8.1 Queues API

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/queues` | Liste toutes les queues disponibles dans tous les board farms |
| `GET` | `/messagesCount/{queue}` | Retourne le nombre de messages dans une queue donnée |

---

### 8.2 Boards API

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/boards` | Retourne toutes les boards disponibles dans le service |

---

### 8.3 Benchmark API

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/benchmark` | Retourne les benchmarks effectués par un utilisateur donné |
| `POST` | `/benchmark/{queue}` | Planifie (schedule) un benchmark dans une queue |
| `DELETE` | `/benchmark/{benchmarkId}` | Supprime un benchmark de la base de données |
| `GET` | `/benchmark/{benchmarkId}` | Retourne la progression / le résultat d'un benchmark par ID |

---

## 9. API — PROJECT SERVICE

**Titre :** Project Service API  
**Version :** 1.0  
**Spec :** OAS3  
**URL spec :** `https://stedgeai-dc.st.com/api//project//api`  
**Serveur :** `https://stm32ai-cs.st.com/api/project/`  
**Description :** Endpoint pour créer des projets STM32CubeMX/IDE ou générer des firmwares.

---

### 9.1 Boards API

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/boards/{boardName}` | Retourne les informations d'une board si supportée par le générateur |
| `GET` | `/boards` | Liste les boards supportées par le générateur de firmware/projet |

---

### 9.2 Firmwares API

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/firmware` | Génère un ZIP contenant le ou les firmwares à flasher sur une cible spécifique |

---

### 9.3 Project Generation API

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/project` | Génère un ZIP contenant : projet STM32CubeIDE + fichiers config STM32CubeMX + réseau uploadé |

---

### 9.4 Schemas (Project Service)

| Schema | Description |
|---|---|
| `BoardInformation` | Informations sur une board (nom, MCU, capacités) |
| `MCU` | Informations sur le microcontrôleur de la board |

---

## 10. AUTHENTIFICATION ET LICENCE

### Mécanisme OIDC / MyST

L'authentification repose sur **OpenID Connect (OIDC)** via le portail MyST de STMicroelectronics.

**Flux d'authentification :**
```
1. Redirection vers my.st.com (MyST login)
2. MyST retourne un code d'autorisation + URL callback
3. POST /login/callback  →  reçoit le TokenSet (access_token, refresh_token, id_token)
4. Les tokens sont utilisés dans le header Authorization: Bearer <token> pour tous les appels API
5. POST /login/refresh  →  renouvelle le TokenSet avec le refresh_token
6. GET  /login/authenticate  →  vérifie la validité du token
```

### Tokens disponibles
- **Accès aux tokens OIDC** : Copie possible depuis les Settings de l'application (`Copy OIDC tokens to clipboard`)
- **TokenSet** contient : access token, refresh token, id token

### Licence logicielle
Avant d'utiliser les services, l'utilisateur doit accepter la :
> **Software License Agreement For Access to ST Edge AI Developer Cloud**

- `GET /user/license` — vérifie les licences acceptées et leurs dates
- `POST /user/license` — accepte une licence

---

## 11. ÉCOSYSTÈME ET RESSOURCES ASSOCIÉES

### Liens directs depuis la plateforme

| Ressource | Description |
|---|---|
| **STM32 Model Zoo** | Collection de modèles pré-entraînés pour STM32 MCU/MPU |
| **ISPU Model Zoo** | Collection de modèles pré-entraînés pour capteurs MEMS ISPU |
| **ST Edge AI Suite** | Suite complète d'outils ST pour l'IA embarquée |
| **ST Community** | Forum et communauté STMicroelectronics |
| **Terms of Use** | Conditions d'utilisation |
| **Privacy Portal** | Portail de confidentialité |

### Documents référencés dans la navigation

| Document | Section |
|---|---|
| **User Manual** | Documentation → User Manual |
| **ST Edge AI Core Documentation** | Documentation → ST Edge AI Core Documentation |
| **Python Interface** | Documentation → Python Interface |

### Autres outils du ST Edge AI Suite

| Outil | Type | Cible |
|---|---|---|
| STM32Cube AI Studio | Desktop | STM32 MCU |
| X-CUBE-AI | Package STM32CubeMX | STM32 MCU (Cortex-M) |
| X-LINUX-AI | Framework Linux | STM32 MPU |
| NanoEdge AI Studio | AutoML Desktop/Cloud | STM32 MCU |
| StellarStudioAI | Desktop | Stellar automotive MCU |
| MEMS Studio | Desktop | Capteurs MEMS |
| ST AIoT Craft | Cloud | IoT sensor-to-cloud |

---

## 12. RÉSUMÉ DES ENDPOINTS PAR SERVICE

Tableau consolidé de **tous les endpoints REST** de la plateforme :

### User Service — `https://stm32ai-cs.st.com/api/user_service`

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/docs` | Documentation HTML Swagger |
| `GET` | `/api` | Documentation JSON OpenAPI |
| `GET` | `/assets/{asset}` | Récupère un asset/utilisateur par ID |
| `POST` | `/login/callback` | Callback MyST → TokenSet |
| `GET` | `/login/callback` | Callback MyST → TokenSet |
| `POST` | `/login/refresh` | Rafraîchit le TokenSet |
| `POST` | `/login/authenticate` | Récupère les infos utilisateur |
| `GET` | `/login/authenticate` | Vérifie la validité du token |
| `GET` | `/user/license` | Liste les licences et dates d'acceptation |
| `POST` | `/user/license` | Accepte une licence |
| `GET` | `/user/user` | Vérifie la validité du token |

---

### File Service — `https://stm32ai-cs.st.com/api/file/`

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/files/models` | Liste les modèles |
| `POST` | `/files/models` | Upload un modèle |
| `GET` | `/files/models/{filename}` | Télécharge un modèle |
| `DELETE` | `/files/models/{filename}` | Supprime un modèle |
| `GET` | `/files/validation/inputs` | Liste les fichiers d'entrée validation |
| `POST` | `/files/validation/inputs` | Upload un fichier d'entrée validation |
| `GET` | `/files/validation/inputs/{filename}` | Télécharge un fichier d'entrée validation |
| `DELETE` | `/files/validation/inputs/{filename}` | Supprime un fichier d'entrée validation |
| `GET` | `/files/validation/outputs` | Liste les fichiers de sortie validation |
| `POST` | `/files/validation/outputs` | Upload un fichier de sortie validation |
| `GET` | `/files/validation/outputs/{filename}` | Télécharge un fichier de sortie validation |
| `DELETE` | `/files/validation/outputs/{filename}` | Supprime un fichier de sortie validation |

---

### STM32AI Service — `https://stm32ai-cs.st.com/api/stm32ai`

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analyze` | Analyse le modèle (RAM, Flash, MACCs) |
| `POST` | `/api/validate` | Valide le modèle sur runtime |
| `POST` | `/api/generate` | Génère le code C embarqué |
| `GET` | `/api/run/{id}` | Résultats d'un job par ID |
| `GET` | `/api/previous/{hash}` | Résultats précédents pour un hash de fichier |

---

### Quantization Service — `https://stm32ai-cs.st.com/api/quantize/`

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/quantize` | Quantifie un modèle ONNX ou Keras (générique) |
| `POST` | `/quantize/onnx_runtime` | Quantifie un modèle ONNX |
| `POST` | `/quantize/tflite` | Quantifie un modèle Keras → TFLite INT8 |

---

### Benchmark Service — `https://stm32ai-cs.st.com/api/benchmark`

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/queues` | Liste toutes les queues du board farm |
| `GET` | `/messagesCount/{queue}` | Nombre de messages dans une queue |
| `GET` | `/boards` | Liste toutes les boards disponibles |
| `GET` | `/benchmark` | Benchmarks de l'utilisateur courant |
| `POST` | `/benchmark/{queue}` | Planifie un benchmark |
| `DELETE` | `/benchmark/{benchmarkId}` | Supprime un benchmark |
| `GET` | `/benchmark/{benchmarkId}` | Progression/résultat d'un benchmark |

---

### Project Service — `https://stm32ai-cs.st.com/api/project/`

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/boards/{boardName}` | Infos d'une board supportée |
| `GET` | `/boards` | Liste des boards supportées |
| `POST` | `/firmware` | Génère un ZIP de firmware(s) à flasher |
| `POST` | `/project` | Génère un ZIP projet STM32CubeIDE/CubeMX |

---

## NOTES TECHNIQUES

- **Format API :** OpenAPI 3.0.x (OAS3)
- **Authentification API :** Bearer Token (OIDC via MyST)
- **Stockage modèles :** Azure Storage (privé par utilisateur)
- **Rétention modèles :** 6 mois après inactivité, puis suppression automatique
- **Accès board farm :** Via queues (système de file d'attente asynchrone)
- **Résultats benchmark :** Polling par `GET /benchmark/{benchmarkId}` jusqu'à complétion
- **Résultats STM32AI :** Polling par `GET /api/run/{id}` jusqu'à complétion
- **Sorties projet :** ZIP contenant projet STM32CubeIDE + config CubeMX + réseau IA

---

*Document généré depuis les fichiers HTML officiels de stedgeai-dc.st.com · 2026 · STMicroelectronics*  
*Tous droits réservés © 2026 — STMicroelectronics*
