# Modèle de détection de balle

Placez ici un modèle YOLO fine-tuné sur des balles de tennis de table, exporté
au format ONNX sous le nom **`ball_yolo.onnx`** (entrée image 1x3xHxW, sortie
YOLOv8/11 standard `(1, 4+nc, N)`).

Sans ce fichier, PingPro utilise automatiquement l'heuristique de détection
existante (`ttnet_analysis.BallDetector`) : aucune fonctionnalité n'est perdue.

## Générer le modèle (optionnel, nécessite un GPU pour l'entraînement)

```bash
pip install ultralytics
python ../tools/export_ball_model.py --dataset <chemin/vers/dataset-yolo>
```

Sources de datasets publics : recherchez "table tennis ball" sur Roboflow Universe
(export format YOLO). Un fine-tuning court de `yolov8n` / `yolo11n` (20-50 epochs)
suffit généralement pour la balle.

## Export sans ré-entraînement (test rapide)

```bash
pip install ultralytics
yolo export model=yolov8n.pt format=onnx
```

Puis copiez `yolov8n.onnx` ici sous le nom `ball_yolo.onnx`. Sans fine-tuning,
la classe détectée est COCO "sports ball" : le détecteur n'applique aucun filtre
de classe, donc cela fonctionne, avec une précision moindre que sur un modèle
spécialisé.
