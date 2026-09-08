"""Smoke test du suivi joueurs : modèle chargé + inférence sans crash + net_x."""
import sys
from pathlib import Path

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from players_tracker import PlayersTracker, net_x_from_quad  # noqa: E402

tracker = PlayersTracker()
assert tracker.detector is not None, "yolov8n.onnx absent — générez-le (voir models/README.md)"

frame = np.full((720, 1280, 3), 40, dtype=np.uint8)
res = tracker.process_frame(frame, 0.0)
assert res["available"] is True
assert res["left"] is None and res["right"] is None  # personne sur fond uni

quad = np.array([[100, 600], [900, 600], [980, 300], [20, 300]], dtype=np.float32)
nx = net_x_from_quad(quad, 1280)
assert 450 < nx < 550, f"net_x inattendu: {nx}"

print("PLAYERS_TRACKER_OK — net_x:", round(nx, 1))
