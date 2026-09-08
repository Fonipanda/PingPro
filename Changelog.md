# Changelog

Toutes les évolutions notables du projet **PingPro (TT Ping Analyzer)** sont documentées dans ce fichier.

Le format s'inspire de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## [Non publié]

### Prévu
- Déploiement en production (hébergement backend + frontend)
- Mise en place d'une CI (lint, tests backend/frontend, build Docker)
- Enrichissement des analyses (nouvelles métriques TTNet et comparaisons de référence)

### Ajouts
- (à compléter)

### Modifications
- (à compléter)

### Corrections
- (à compléter)

## [2.0.0] - 2026-09-08

### Ajouts
- Consolidation du projet dans le dépôt `C:\Users\franc\PingPro` (transfert depuis l'espace de travail Verdent)
- Analyse de pose MediaPipe avec visualisation 3D et comparaison à une vidéo de référence
- Mode démo/mock permettant de tester l'UI sans backend
- Conteneurisation Docker complète : backend FastAPI (`backend/Dockerfile`) et frontend nginx (`frontend/Dockerfile`, `frontend/nginx.conf`)
- Fichier `Changelog.md` pour tracer les évolutions passées et à venir

### Suppressions
- Fichiers issus de l'ancienne version : `run_app.py`, `QUICKSTART.md`, `scripts/`, `.run/`, `origin_txt/`
- Modules backend non utilisés par la version actuelle : `spin_estimation.py`, `table_tennis_rules.py`, `anythingllm_integration.py`, `real_time_ttnet_analyzer.py`, `tt3d_advanced_analysis.py`, `backend/README.md`
- Composants frontend non référencés : `ReportExport.js`, `VideoGallery.js`
- Doublon de lockfile : `frontend/package-lock.json` (Yarn est le gestionnaire officiel, `yarn.lock` conservé)
- Doublon de fichier d'environnement : `backend/env.example` et `frontend/env.example` (remplacés par `.env.example`)

## [1.2.0] - 2026-09-07

### Ajouts
- Mode démo/mock pour tester l'interface sans backend opérationnel

## [1.1.0] - 2026-09-07

### Ajouts
- Intégration de l'analyse de pose MediaPipe avec visualisation 3D
- Comparaison avec des vidéos de référence

## [1.0.0] - 2026-09-07

### Ajouts
- MVP : upload de vidéo, analyse TTNet et tableau de bord
- Suppression des modules temps réel/streaming
- Ajout de la configuration Docker
