# Changelog

Toutes les évolutions notables du projet **PingPro (TT Ping Analyzer)** sont documentées dans ce fichier.

Le format s'inspire de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## [Non publié]

### Prévu
- Déploiement en production (hébergement backend + frontend)
- Mise en place d'une CI (lint, tests backend/frontend, build Docker)
- Phase 2 (fine-tuning balle) : remplacer le modèle par défaut — téléchargement Roboflow bloqué par la clé API / le format d'URL ; tant que `backend/models/ball_yolo.onnx` n'est pas fourni, la détection balle repose sur l'heuristique TTNet
- Phase 3 (différé) : filtre de Kalman joueurs + fallback Hough table ; le suivi COCO actuel suffit pour l'attribution gauche/droite

### Ajouts
- **Mode réel intégral** : suppression du module simulé `VideoProcessor` du pipeline d'analyse (`server.py`) — les résultats ne contiennent plus aucune donnée générée aléatoirement, uniquement TTNet + match_analysis + pose
- **Carte de placement conforme au visuel de référence** : pourcentages de répartition des rebonds autour de la table (3 tiers de longueur au-dessus, 3 tiers de largeur à gauche), légende « Topspin / Coupé en coup droit / revers » — onglet Impacts Balle & Placement

### Modifications
- `_classify_stroke_side` (`match_analysis.py`) : clés canoniques partagées frontend/overlay — `topspin_coup_droit`, `topspin_revers`, `coup_droit`, `revers` (les coups non-topspin n'apparaissent plus comme « inconnu »)
- Palette d'incrustation vidéo (`video_overlay.STROKE_COLORS_BGR`) : dérivée exactement de la palette hexadécimale du frontend (orange/bleu/jaune/vert/blanc)
- Statistique « impacts par camp » du frontend : basée sur les rebonds réels par camp (`player_stats`) au lieu de la grille de zones

### Suppressions
- Carte « Heatmap par zones de la table » du frontend (remplacée par la carte de placement des rebonds)

## [2.1.1] - 2026-09-08

### Corrections
- Environnement backend `backend/venv` cassé (lanceur retombé sur Python 3.14 après désinstallation de Python 3.11, paquets compilés cp311 incompatibles) : venv reconstruit intégralement sur Python 3.14, backend validé par le test d'intégration complet
- `backend/requirements.txt` : ajout de `httpx2` (requis par le TestClient de starlette pour `backend/tools/integration_test.py`)
- README : note Python 3.14 mise à jour (backend validé sous 3.14, repli 3.11/3.12 documenté)

## [2.1.0] - 2026-09-08

### Ajouts
- **Suivi de balle par modèle ONNX** : `backend/ball_tracker.py` (YOLO ONNX + suivi prédictif), repli automatique sur l'heuristique TTNet, pipeline hybride ONNX + heuristique frame par frame
- **Détection de table + homographie** : `backend/table_detector.py` — projection des impacts vers le repère réel ITTF (2,74 × 1,525 m)
- **Analyse de match** : `backend/match_analysis.py` — segmentation des échanges, carte de placement par zones, vitesses réelles en m/s, détection des rebonds, moments clés
- **Montage auto** : compilation `auto_edit.mp4` des échanges réellement détectés (FFmpeg concat), affichée dans l'onglet Match Compilé
- **Coach IA Pose 3D réelle** : extraction des *world landmarks* MediaPipe (mètres) dans `pose_analysis.py`, vue Three.js alimentée par les coordonnées monde
- **Bibliothèque de références** : `backend/references/*.json` (format remplaçable par des captures réelles), chargée par `pose_reference.py` avant le modèle synthétique
- **Endpoint `POST /api/plan`** : plan d'entraînement personnalisé (LLM OpenAI si clé configurée, sinon fallback statique structuré)
- **Rapport de pose enrichi** : le LLM reçoit désormais les données d'analyse de match (échanges, vitesses, placement)
- **Outils** : `backend/tools/export_ball_model.py` (fine-tuning + export ONNX), `backend/tools/integration_test.py`, `backend/tools/smoke_test_match_analysis.py`
- **Onglet frontend "Analyse de Match"** : heatmap de placement (SVG), vitesses, buckets d'échanges

### Corrections
- Heuristique de détection balle : la balle fusionnait avec les zones blanches du fond (masques couleur désormais traités séparément) — `ttnet_analysis.py`
- Homographie dégénérée (NaN) quand les quads détectés sont identiques — `table_detector.py`
- Sérialisation JSON de `numpy.float32` dans les résultats — `table_detector.py`, `ball_tracker.py`
- Segmentation d'échanges horodatée en temps vidéo (au lieu de l'horloge murale)

### Suppressions
- `.gitconfig` (identité git de l'agent Emergent)
- `.emergent/` (métadonnées Emergent)
- `test_4_corrections.py`, `test_result.md`, `test_results_page.html` (tests/journaux de l'ancien environnement, référençant des modules supprimés)

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
