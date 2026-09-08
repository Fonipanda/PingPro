# PingPro — Moteur d'analyse vidéo

Ce document décrit la réalité technique du moteur d'analyse (v2.1) : comment la
balle, la table et les échanges sont détectés, avec des chiffres **mesurés** sur
cette machine (CPU, vidéo synthétique 1280×720 à 30 fps).

## 1. Détection de la balle — pipeline hybride

La détection combine deux sources, frame par frame :

1. **Modèle ONNX** (`backend/ball_tracker.py`) : YOLO nano exporté en ONNX
   (`backend/models/ball_yolo.onnx`), exécuté via `onnxruntime` (CPU, ou
   DirectML sur iGPU AMD si `onnxruntime-directml` est installé). Un suivi
   prédictif (vitesse constante + gating) associe les détections entre frames.
2. **Heuristique TTNet** (`ttnet_analysis.BallDetector`) : masques HSV orange et
   blanc **traités séparément** (avant la v2.1, la balle fusionnait avec les
   zones blanches du fond), filtrage par taille + circularité.

Si le modèle ONNX ne détecte rien sur une frame (cas fréquent avec le modèle de
base COCO sur une petite balle), l'heuristique prend le relais. Si le fichier
modèle est absent, l'heuristique seule est utilisée.

### Chiffres mesurés

| Mesure | Valeur |
|---|---|
| Inférence ONNX (CPU, frame 1280×720) | ~39 ms/frame |
| Heuristique seule (même frame) | ~2–3 ms/frame |
| Modèle de base COCO seul (`yolov8n.onnx`) | ~2/36 frames détectées sur une petite balle |
| Pipeline hybride (ONNX + heuristique) | taux de détection élevé, précision limitée par l'heuristique |

**Conséquence honnête** : sans fine-tuning, la précision du suivi dépend
majoritairement de l'heuristique. Pour une vraie précision niveau "modèle
entraîné", fine-tunez sur un dataset Roboflow "table tennis ball" :

```bash
pip install ultralytics
python backend/tools/export_ball_model.py --dataset <chemin/dataset-yolo> --epochs 30
```

## 2. Détection de table et homographie (`backend/table_detector.py`)

- Masque couleur (bleu ou vert) + morphologie, plus grand contour convexe.
- Vote médian sur les quads détectés dans 8 frames échantillonnées, filtrage des
  quads aberrants, garde-fous contre les homographies dégénérées (NaN).
- Homographie vers le repère réel ITTF : 2,74 × 1,525 m, filet à x = 0.

Si la table n'est pas détectable, tout se dégrade proprement : vitesses en
pixels/s, placement indisponible.

## 3. Analyse de match (`backend/match_analysis.py`)

Entrées : positions de balle horodatées **en temps vidéo** (corrigé en v2.1,
avant : horloge murale).

- **Segmentation des échanges** : un silence de détection > 1,2 s clôt un
  échange ; durée minimale 0,8 s ; nombre de coups estimé par traversées du
  filet (changement de signe de dx).
- **Placement** : grille 2 moitiés × 3 zones longueur × 3 zones largeur,
  uniquement pour les impacts réellement sur la table (test point-in-quad).
- **Vitesses** : m/s via homographie (filtre des sauts hors table), pixels/s
  sinon, avec estimation approximative m/s si l'échelle de la table est connue.
- **Rebonds** : inversion de vitesse verticale de la balle projetée sur la table.
- **Moments clés** : plus long échange, vitesse max.

## 4. Montage auto

Les échanges détectés (marge ±0,5–1 s) sont découpés et concaténés par FFmpeg
(`-f concat`, inpoint/outpoint) → `auto_edit.mp4`. Nécessite FFmpeg installé ;
sinon les compilations sont simplement absentes du résultat.

## 5. Pose 3D et références

- MediaPipe Pose Landmarker (modèle `pose_landmarker.task`) : landmarks image +
  **world landmarks** (mètres, origine aux hanches) pour la vue 3D Three.js.
- Comparaison DTW avec `backend/references/<coup>.json`. Les fichiers livrés
  sont des bases synthétiques (3 poses clés par coup) : remplacez-les par des
  captures réelles pour une évaluation fiable.

## 6. Ce que ce moteur ne fait pas (encore)

- Pas de tracking multi-joueurs ni d'identification des joueurs.
- Pas d'estimation d'effet (spin).
- Pas de scoring automatique fiable (le score affiché reste une estimation).
- Pas de temps réel : une analyse complète prend plusieurs fois la durée de la
  vidéo sur CPU (l'échantillonnage 1 frame sur 5 réduit le coût, pas à 0).
