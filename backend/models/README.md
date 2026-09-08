# Modèles ONNX de PingPro (moteur v3)

Deux modèles optionnels, avec repli propre si absents :

| Fichier | Rôle | Repli si absent |
|---|---|---|
| `ball_yolo.onnx` | Détection de balle (YOLO fine-tuné "table tennis ball") | Heuristique couleur/forme (`ttnet_analysis.BallDetector`) |
| `yolov8n.onnx` | Détection des **joueurs** (COCO, classe `person`) pour le suivi gauche/droite | Suivi joueurs indisponible (stats adverses non calculées) |

Les fichiers sont **hors git** (dépôt léger) — régénération documentée ci-dessous.

## 1. Balle fine-tunée (`ball_yolo.onnx`)

```bash
# a) Télécharger un dataset (compte Roboflow gratuit, clé API)
set ROBOFLOW_API_KEY=xxxxxxxx
pip install roboflow
python ../tools/export_ball_model.py --download-roboflow "madianou-kqrfk/table-tennis-ball-detection" --version 1

# b) Entraîner — recommandé : Google Colab (GPU gratuit)
#    Ouvrez ../tools/colab_train_ball.ipynb sur colab.research.google.com,
#    exécutez-le, récupérez best.pt, puis ici :
python ../tools/export_ball_model.py --weights best.pt

#    Entraînement local possible mais long sur CPU :
python ../tools/export_ball_model.py --dataset ../datasets/ball/data.yaml --epochs 40
```

Benchmark avant/après sur une vraie vidéo :

```bash
python ../tools/bench_ball_detection.py <chemin/vers/video.mp4>
```

## 2. Joueurs (`yolov8n.onnx`)

Export simple du YOLO de base (classe `person` du COCO, pas d'entraînement requis) :

```bash
pip install ultralytics
python ../tools/export_ball_model.py --base yolov8n.pt --out yolov8n.onnx
```

## Note ONNX Runtime

`onnxruntime` (CPU) est installé par défaut. Sur un iGPU AMD, décommentez
`onnxruntime-directml` dans `backend/requirements.txt` pour l'accélération DirectML.
