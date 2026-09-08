"""Test d'intégration bout en bout : upload -> analyse -> résultats.

Valide : pipeline TTNet (ONNX ou heuristique), analyse de match, montage auto,
plan d'entraînement, rapport de pose. Nécessite numpy/opencv/mediapipe (+ffmpeg
optionnel pour les compilations)."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

import server

client = TestClient(server.app)


def make_video(path, fps=30, seconds=6.0):
    import cv2
    import numpy as np
    w, h = 1280, 720
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    total = int(fps * seconds)
    quad = np.array([[340, 260], [940, 260], [1100, 560], [180, 560]], dtype=np.int32)
    for i in range(total):
        t = i / fps
        frame = np.full((h, w, 3), 235, dtype=np.uint8)
        cv2.fillPoly(frame, [quad], (200, 120, 0))
        cv2.line(frame, (640, 260), (640, 560), (255, 255, 255), 3)
        phase = (t % 4.0)
        if phase < 3.0:
            bx = 360 + int(phase * 180)
            by = int(500 - 160 * np.sin(np.pi * phase / 3.0) - 20)
            cv2.circle(frame, (bx, by), 7, (30, 120, 255), -1)
        writer.write(frame)
    writer.release()


def main():
    video_path = Path(__file__).resolve().parent.parent / "uploads" / "_integration_test.mp4"
    make_video(video_path)

    t0 = time.time()
    with open(video_path, "rb") as f:
        r = client.post(
            "/api/analyze",
            files={"video": ("test.mp4", f, "video/mp4")},
            data={"player_side": "droite", "skill_level": "intermediaire"},
        )
    assert r.status_code == 200, r.text
    analysis_id = r.json()["analysis_id"]
    print("analysis_id:", analysis_id)

    for _ in range(300):
        s = client.get(f"/api/analysis/{analysis_id}/status").json()
        if s["status"] in ("completed", "failed"):
            break
        time.sleep(0.5)
    print(f"status: {s['status']} ({time.time() - t0:.0f}s), step: {s.get('current_step')}")
    assert s["status"] == "completed", s

    res = client.get(f"/api/analysis/{analysis_id}/results").json()
    ma = res.get("match_analysis")
    assert ma, "match_analysis absent"
    print("table_detected:", ma["table_detected"])
    print("rallies:", ma["rally_summary"]["total_rallies"], "| speed:", ma["ball_speed"].get("max_speed_ms"), "m/s")
    print("compilations:", sorted((res.get("video_compilations") or {}).keys()))
    print("training_plan source:", res.get("training_plan", {}).get("source"))
    print("pose_report présent:", bool(res.get("pose_report")))
    assert res.get("training_plan"), "training_plan absent"

    # Endpoint /api/plan
    plan = client.post(
        "/api/plan",
        json={"goal": "competition", "priority": "service_remise", "weekly_frequency": 4},
    )
    assert plan.status_code == 200, plan.text
    print("/api/plan source:", plan.json().get("source"))

    video_path.unlink(missing_ok=True)
    print("INTEGRATION_TEST_OK")


if __name__ == "__main__":
    main()
