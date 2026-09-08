"""
Export d'un modèle de détection de balle vers ONNX pour PingPro (moteur v3).

Usage :
    # 1) Télécharger un dataset Roboflow (nécessite ROBOFLOW_API_KEY, compte gratuit)
    python export_ball_model.py --download-roboflow "madianou-kqrfk/table-tennis-ball-detection" --version 1

    # 2) Fine-tuner localement (CPU : long) puis exporter en ONNX
    python export_ball_model.py --dataset datasets/ball/data.yaml --epochs 40 --imgsz 640

    # 3) Sans dataset : exporter le YOLO de base (utile pour la classe "person")
    python export_ball_model.py --base yolov8n.pt --out yolov8n.onnx

Recommandé : entraîner sur Google Colab (GPU gratuit) avec
backend/tools/colab_train_ball.ipynb, puis copier le .pt ici et exporter :
    python export_ball_model.py --weights best.pt

Le fichier backend/models/ball_yolo.onnx est ensuite remplacé par le résultat.
"""

import argparse
import shutil
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
BACKEND_MODELS_DIR = BACKEND_DIR / "models"
DATASETS_DIR = BACKEND_DIR / "datasets"


def download_roboflow(workspace_project: str, version: int, api_key: str) -> Path:
    """Télécharge un dataset Roboflow au format YOLOv8 dans backend/datasets/ball/."""
    import os

    from roboflow import Roboflow

    key = api_key or os.environ.get("ROBOFLOW_API_KEY")
    if not key:
        raise SystemExit(
            "ROBOFLOW_API_KEY manquante. Créez un compte gratuit sur roboflow.com, "
            "puis : set ROBOFLOW_API_KEY=xxxxxxxx"
        )
    rf = Roboflow(api_key=key)
    workspace, project = workspace_project.split("/", 1)
    ds = rf.workspace(workspace).project(project).version(version).download("yolov8")
    target = DATASETS_DIR / "ball"
    if target.exists():
        shutil.rmtree(target)
    shutil.move(str(ds.location), str(target))
    yaml_path = target / "data.yaml"
    print(f"Dataset prêt : {yaml_path}")
    return yaml_path


def ensure_val_split(dataset_yaml: Path) -> None:
    """Garantit un split val (Roboflow fournit train/valid/test ; certains non)."""
    import yaml

    data = yaml.safe_load(dataset_yaml.read_text(encoding="utf-8"))
    root = dataset_yaml.parent
    if data.get("val"):
        return
    if data.get("test"):
        data["val"] = data["test"]
    else:
        # déplace 15 % de train vers val
        train_img_dir = root / str(data.get("train", "train/images"))
        val_img_dir = root / "valid/images"
        val_lbl_dir = root / "valid/labels"
        val_img_dir.mkdir(parents=True, exist_ok=True)
        val_lbl_dir.mkdir(parents=True, exist_ok=True)
        images = sorted(train_img_dir.glob("*.jpg")) + sorted(train_img_dir.glob("*.png"))
        step = max(1, len(images) // 7)
        for img in images[::step]:
            lbl = train_img_dir.parent / "labels" / (img.stem + ".txt")
            shutil.move(str(img), str(val_img_dir / img.name))
            if lbl.exists():
                shutil.move(str(lbl), str(val_lbl_dir / lbl.name))
        data["val"] = "valid/images"
    with open(dataset_yaml, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)


def main():
    parser = argparse.ArgumentParser(description="Export YOLO -> ONNX pour PingPro")
    parser.add_argument(
        "--download-roboflow",
        metavar="WORKSPACE/PROJECT",
        help="Télécharge le dataset Roboflow indiqué dans backend/datasets/ball/",
    )
    parser.add_argument("--version", type=int, default=1, help="Version du dataset Roboflow")
    parser.add_argument("--roboflow-key", default=None, help="Clé API Roboflow (ou env ROBOFLOW_API_KEY)")
    parser.add_argument("--dataset", help="Chemin d'un data.yaml YOLO pour fine-tuning")
    parser.add_argument("--weights", help="Poids déjà entraînés (.pt) : export seul")
    parser.add_argument("--base", default="yolov8n.pt", help="Poids de base (défaut: yolov8n.pt)")
    parser.add_argument("--epochs", type=int, default=40, help="Epochs de fine-tuning")
    parser.add_argument("--imgsz", type=int, default=640, help="Taille d'entrée (défaut: 640)")
    parser.add_argument(
        "--out",
        default="ball_yolo.onnx",
        help="Nom du fichier de sortie dans backend/models/ (défaut: ball_yolo.onnx)",
    )
    args = parser.parse_args()

    if args.download_roboflow:
        download_roboflow(args.download_roboflow, args.version, args.roboflow_key)
        return

    try:
        from ultralytics import YOLO
    except ImportError:
        raise SystemExit("Installez d'abord : pip install ultralytics")

    if args.weights:
        weights = Path(args.weights)
    elif args.dataset:
        ensure_val_split(Path(args.dataset))
        model = YOLO(args.base)
        model.train(
            data=args.dataset,
            epochs=args.epochs,
            imgsz=args.imgsz,
            patience=10,
            # petites balles : augmentation adaptée
            degrees=5,
            scale=0.3,
            translate=0.1,
            fliplr=0.5,
            mosaic=1.0,
            close_mosaic=10,
        )
        weights = Path(model.trainer.best)
    else:
        weights = Path(args.base)

    exported = YOLO(str(weights)).export(format="onnx", imgsz=args.imgsz)
    BACKEND_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKEND_MODELS_DIR / args.out
    shutil.copyfile(exported, target)
    print(f"Modèle exporté vers {target}")


if __name__ == "__main__":
    main()
