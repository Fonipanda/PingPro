"""
Export d'un modèle de détection de balle vers ONNX pour PingPro.

Usage :
    pip install ultralytics
    python export_ball_model.py --dataset <chemin/dataset-yolo> [--epochs 30]
    # ou sans dataset :
    python export_ball_model.py --base yolov8n.pt

Le fichier backend/models/ball_yolo.onnx est ensuite remplacé par le résultat.
"""

import argparse
import shutil
from pathlib import Path

BACKEND_MODELS_DIR = Path(__file__).resolve().parent.parent / "backend" / "models"


def main():
    parser = argparse.ArgumentParser(description="Export YOLO -> ONNX pour PingPro")
    parser.add_argument("--dataset", help="Chemin d'un dataset YOLO (data.yaml) pour fine-tuning")
    parser.add_argument("--base", default="yolov8n.pt", help="Poids de base (défaut: yolov8n.pt)")
    parser.add_argument("--epochs", type=int, default=30, help="Epochs de fine-tuning")
    args = parser.parse_args()

    try:
        from ultralytics import YOLO
    except ImportError:
        raise SystemExit("Installez d'abord : pip install ultralytics")

    if args.dataset:
        model = YOLO(args.base)
        model.train(data=args.dataset, epochs=args.epochs, imgsz=640)
        weights = Path(model.trainer.best)
    else:
        weights = Path(args.base)

    exported = YOLO(str(weights)).export(format="onnx", imgsz=640)
    BACKEND_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKEND_MODELS_DIR / "ball_yolo.onnx"
    shutil.copyfile(exported, target)
    print(f"Modèle exporté vers {target}")


if __name__ == "__main__":
    main()
