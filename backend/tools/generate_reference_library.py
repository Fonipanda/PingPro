"""Génère les fichiers de référence initiaux dans backend/references/ à partir
des modèles synthétiques de secours. À relancer après capture de vraies
références pour maintenir le format."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pose_reference import _build_reference_sequence, JOINT_NAMES

out = Path(__file__).resolve().parent.parent / "references"
out.mkdir(exist_ok=True)
for stroke in ["forehand_topspin", "backhand", "serve"]:
    seq = _build_reference_sequence(stroke)
    if seq is None:
        continue
    data = {"joint_names": JOINT_NAMES, "source": "synthetic_baseline", "frames": seq.tolist()}
    (out / f"{stroke}.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    print("wrote", stroke, seq.shape)
