"""
Benchmark de détection de balle : heuristique TTNet vs modèle ONNX (si présent).

Usage :
    python tools/bench_ball_detection.py <chemin_video> [--stride 3] [--max 1500]

Affiche, pour la même sélection de frames :
- heuristique : % de frames avec au moins un candidat ;
- ONNX (si backend/models/ball_yolo.onnx existe) : % de frames avec détection ;
- accord heuristique/ONNX (distance < 60 px) — utile pour valider un fine-tuning.
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from ball_tracker import get_onnx_ball_detector  # noqa: E402
from ttnet_analysis import BallDetector  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("--stride", type=int, default=3)
    parser.add_argument("--max", type=int, default=1500)
    args = parser.parse_args()

    heuristic = BallDetector()
    onnx_detector = get_onnx_ball_detector()

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        raise SystemExit(f"Vidéo illisible : {args.video}")

    frames_done = 0
    frames_seen = 0
    h_hits = 0
    o_hits = 0
    agree_hits = h_o = 0
    h_positions: list = []
    o_positions: list = []

    while frames_done < args.max:
        ret, frame = cap.read()
        if not ret:
            break
        if frames_seen % args.stride != 0:
            frames_seen += 1
            continue
        frames_seen += 1
        frames_done += 1

        h_cands = heuristic.detect_ball_global(frame)
        h_pos = max(h_cands, key=lambda c: c[2])[:2] if h_cands else None
        h_hits += h_pos is not None
        h_positions.append(h_pos)

        if onnx_detector is not None:
            o_cands = onnx_detector.detect(frame)
            o_pos = (o_cands[0][0], o_cands[0][1]) if o_cands else None
            o_hits += o_pos is not None
            o_positions.append(o_pos)
            if h_pos and o_pos:
                h_o += 1
                if np.hypot(h_pos[0] - o_pos[0], h_pos[1] - o_pos[1]) < 60:
                    agree_hits += 1

    cap.release()
    n = max(1, frames_done)
    print(f"Frames analysées : {frames_done} (stride {args.stride})")
    print(f"Heuristique : {h_hits / n:.1%} de frames avec candidat")
    if onnx_detector is not None:
        print(f"ONNX        : {o_hits / n:.1%} de frames avec détection")
        if h_o:
            print(f"Accord (< 60 px) sur frames communes : {agree_hits / h_o:.1%}")
    else:
        print("ONNX : modèle absent (backend/models/ball_yolo.onnx) — voir tools/export_ball_model.py")


if __name__ == "__main__":
    main()
