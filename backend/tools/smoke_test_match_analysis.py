"""Smoke test : vidéo synthétique (table bleue + balle orange) -> détection table,
homographie, segmentation d'échanges, vitesses. Nécessite numpy + opencv."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np

from table_detector import TableDetector
from ttnet_analysis import TTNetAnalyzer
from match_analysis import build_match_analysis

OUT = Path(__file__).resolve().parent.parent / "uploads" / "_smoke_test.mp4"


def make_video(path: Path, fps: int = 30, seconds: float = 6.0) -> None:
    w, h = 1280, 720
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    total = int(fps * seconds)
    # Table bleue en perspective (travaillée)
    quad = np.array([[340, 260], [940, 260], [1100, 560], [180, 560]], dtype=np.int32)

    for i in range(total):
        t = i / fps
        frame = np.full((h, w, 3), 235, dtype=np.uint8)
        cv2.fillPoly(frame, [quad], (200, 120, 0))  # bleu BGR
        cv2.line(frame, (640, 260), (640, 560), (255, 255, 255), 3)
        # Balle orange : rebond parabolique sur la table pendant 0-3s puis pause
        phase = (t % 4.0)
        if phase < 3.0:
            bx = 360 + int(phase * 180)
            by = int(500 - 160 * np.sin(np.pi * phase / 3.0) - 20)
            cv2.circle(frame, (bx, by), 7, (30, 120, 255), -1)  # orange BGR
        writer.write(frame)
    writer.release()


def main():
    make_video(OUT)
    cap = cv2.VideoCapture(str(OUT))
    ret, frame = cap.read()
    cap.release()
    quad = TableDetector().detect_quad(frame)
    assert quad is not None, "Table non détectée sur la frame de test"
    print("Quad détecté :", quad.tolist())

    analyzer = TTNetAnalyzer()
    results = analyzer.analyze_video_real(str(OUT), max_frames=200)
    ma = build_match_analysis(results, str(OUT))
    print("Table détectée :", ma["table_detected"])
    print("Détections balle :", ma["total_ball_detections"])
    print("Échanges :", ma["rally_summary"])
    print("Vitesses :", ma["ball_speed"])
    if ma["placement"]["available"]:
        print("Zones placement :", ma["placement"]["zones"])
    print("SMOKE_TEST_OK")
    OUT.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
