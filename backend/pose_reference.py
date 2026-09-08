"""
Comparaison de pose avec un modèle de référence.
Utilise Dynamic Time Warping (DTW) pour aligner temporellement deux séquences
de landmarks et calculer un score de similarité.

Les références sont lues depuis backend/references/<stroke_type>.json
(bibliothèque remplaçable par des références capturées sur de vrais joueurs).
Sans fichier, un modèle synthétique de secours est utilisé.
"""

import json
import logging
import math
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

REFERENCES_DIR = Path(__file__).parent / "references"


def _extract_pose_sequence(frames: List[Dict], joint_names: List[str]) -> np.ndarray:
    """Extrait une matrice T x N joints x 2 coordonnées normalisées."""
    sequence = []
    for frame in frames:
        poses = frame.get("poses", [])
        if not poses:
            continue
        landmarks = poses[0]
        coords = []
        for name in joint_names:
            found = False
            for idx, lm in enumerate(landmarks):
                # indices standards MediaPipe
                if (
                    (name == "right_shoulder" and idx == 12)
                    or (name == "right_elbow" and idx == 14)
                    or (name == "right_wrist" and idx == 16)
                    or (name == "right_hip" and idx == 24)
                    or (name == "right_knee" and idx == 26)
                    or (name == "left_shoulder" and idx == 11)
                    or (name == "left_elbow" and idx == 13)
                    or (name == "left_wrist" and idx == 15)
                    or (name == "left_hip" and idx == 23)
                    or (name == "left_knee" and idx == 25)
                    or (name == "nose" and idx == 0)
                ):
                    coords.extend([lm["x"], lm["y"]])
                    found = True
                    break
            if not found:
                coords.extend([0.0, 0.0])
        sequence.append(coords)
    return np.array(sequence)


def _dtw_distance(seq_a: np.ndarray, seq_b: np.ndarray) -> float:
    """DTW simple avec distance euclidienne."""
    n, m = len(seq_a), len(seq_b)
    if n == 0 or m == 0:
        return float("inf")

    dtw = np.full((n + 1, m + 1), float("inf"))
    dtw[0, 0] = 0.0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = np.linalg.norm(seq_a[i - 1] - seq_b[j - 1])
            dtw[i, j] = cost + min(dtw[i - 1, j], dtw[i, j - 1], dtw[i - 1, j - 1])

    return float(dtw[n, m])


def _load_reference_from_library(stroke_type: str) -> Optional[np.ndarray]:
    """
    Charge une référence depuis backend/references/<stroke_type>.json.
    Format attendu :
    {
      "joint_names": ["right_shoulder", ...],   # optionnel, défaut JOINT_NAMES
      "frames": [[x, y, x, y, ...], ...]        # T x (2 * len(joint_names))
    }
    """
    path = REFERENCES_DIR / f"{stroke_type}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        joint_names = data.get("joint_names", JOINT_NAMES)
        seq = np.array(data["frames"], dtype=float)
        if seq.ndim != 2 or seq.shape[1] != 2 * len(joint_names):
            logger.warning(f"Référence invalide ({path.name}) : dimensions inattendues")
            return None
        logger.info(f"Référence chargée depuis la bibliothèque : {path.name}")
        return seq
    except Exception as e:
        logger.warning(f"Erreur de lecture de la référence {path.name}: {e}")
        return None


def _build_reference_sequence(stroke_type: str) -> Optional[np.ndarray]:
    """
    Référence de secours synthétique (utilisée uniquement si la bibliothèque
    backend/references/ ne contient pas le coup demandé).
    Valeurs normalisées approximatives [x, y] dans [0, 1].
    """
    refs = {
        "forehand_topspin": [
            # armé
            [0.55, 0.35, 0.45, 0.45, 0.40, 0.55, 0.55, 0.60, 0.55, 0.75, 0.45, 0.35, 0.35, 0.45, 0.30, 0.55, 0.45, 0.60, 0.45, 0.75, 0.50, 0.10],
            # frappe
            [0.55, 0.35, 0.60, 0.42, 0.70, 0.48, 0.55, 0.60, 0.60, 0.72, 0.45, 0.35, 0.40, 0.45, 0.35, 0.55, 0.45, 0.60, 0.50, 0.72, 0.50, 0.10],
            # accompagnement
            [0.55, 0.35, 0.65, 0.40, 0.75, 0.45, 0.55, 0.60, 0.62, 0.70, 0.45, 0.35, 0.42, 0.45, 0.38, 0.55, 0.45, 0.60, 0.52, 0.70, 0.50, 0.10],
        ],
        "backhand": [
            [0.45, 0.35, 0.35, 0.45, 0.30, 0.55, 0.45, 0.60, 0.45, 0.75, 0.55, 0.35, 0.45, 0.45, 0.40, 0.55, 0.55, 0.60, 0.55, 0.75, 0.50, 0.10],
            [0.45, 0.35, 0.40, 0.42, 0.35, 0.48, 0.45, 0.60, 0.40, 0.72, 0.55, 0.35, 0.60, 0.42, 0.70, 0.48, 0.55, 0.60, 0.60, 0.72, 0.50, 0.10],
            [0.45, 0.35, 0.42, 0.40, 0.38, 0.45, 0.45, 0.60, 0.38, 0.70, 0.55, 0.35, 0.62, 0.40, 0.75, 0.45, 0.55, 0.60, 0.62, 0.70, 0.50, 0.10],
        ],
        "serve": [
            [0.50, 0.30, 0.55, 0.40, 0.60, 0.50, 0.50, 0.55, 0.50, 0.70, 0.50, 0.30, 0.45, 0.40, 0.40, 0.50, 0.50, 0.55, 0.50, 0.70, 0.50, 0.10],
            [0.50, 0.30, 0.50, 0.35, 0.50, 0.42, 0.50, 0.55, 0.50, 0.68, 0.50, 0.30, 0.45, 0.38, 0.42, 0.45, 0.50, 0.55, 0.50, 0.68, 0.50, 0.10],
            [0.50, 0.30, 0.48, 0.33, 0.45, 0.38, 0.50, 0.55, 0.50, 0.65, 0.50, 0.30, 0.47, 0.35, 0.45, 0.40, 0.50, 0.55, 0.50, 0.65, 0.50, 0.10],
        ],
    }
    seq = refs.get(stroke_type)
    return np.array(seq) if seq else None


def get_reference_sequence(stroke_type: str) -> Optional[np.ndarray]:
    """Référence prioritaire depuis la bibliothèque, sinon modèle synthétique."""
    ref = _load_reference_from_library(stroke_type)
    if ref is not None:
        return ref
    return _build_reference_sequence(stroke_type)


JOINT_NAMES = [
    "right_shoulder",
    "right_elbow",
    "right_wrist",
    "right_hip",
    "right_knee",
    "left_shoulder",
    "left_elbow",
    "left_wrist",
    "left_hip",
    "left_knee",
    "nose",
]


def compare_with_reference(
    frames: List[Dict],
    stroke_type: str = "forehand_topspin",
) -> Dict[str, Any]:
    """
    Compare la séquence de poses utilisateur avec un modèle de référence.
    """
    user_seq = _extract_pose_sequence(frames, JOINT_NAMES)
    ref_seq = get_reference_sequence(stroke_type)

    if ref_seq is None or len(user_seq) == 0:
        return {
            "stroke_type": stroke_type,
            "similarity_score": 0.0,
            "distance": None,
            "observations": ["Modèle de référence ou séquence utilisateur indisponible"],
        }

    distance = _dtw_distance(user_seq, ref_seq)
    # Normalisation grossière : distance divisée par la longueur et le nombre de joints
    normalized = distance / max(1, len(user_seq) * len(JOINT_NAMES))
    # Score entre 0 et 100
    score = max(0.0, 100.0 - normalized * 500)

    observations = []
    if score >= 80:
        observations.append("Mouvement proche du modèle de référence")
    elif score >= 60:
        observations.append("Mouvement correct avec quelques écarts")
    else:
        observations.append("Mouvement à retravailler par rapport au modèle")

    # Convert reference sequence to landmarks format
    reference_landmarks = []
    for frame in ref_seq:
        lms = []
        for i in range(0, len(frame), 2):
            lms.append({"x": frame[i], "y": frame[i + 1], "z": 0, "visibility": 1.0})
        reference_landmarks.append(lms)

    return {
        "stroke_type": stroke_type,
        "similarity_score": round(score, 1),
        "distance": round(distance, 2),
        "normalized_distance": round(normalized, 4),
        "user_frames": len(user_seq),
        "reference_frames": len(ref_seq),
        "reference_landmarks": reference_landmarks[:3],
        "observations": observations,
    }


def suggest_improvements(pose_data: Dict, comparison: Dict) -> List[str]:
    """Génère des suggestions basiques à partir des écarts de pose."""
    suggestions = []
    angles = pose_data.get("contact_angles", {})

    elbow = angles.get("elbow")
    if elbow is not None:
        if elbow < 80:
            suggestions.append("Le coude est très fléchi au contact ; essayez de tendre un peu plus le bras pour plus de contrôle.")
        elif elbow > 150:
            suggestions.append("Le bras est presque tendu au contact ; un coude légèrement plus fléchi peut aider à engager le topspin.")

    knee = angles.get("knee")
    if knee is not None:
        if knee > 160:
            suggestions.append("Les jambes sont quasi tendues ; fléchissez davantage les genoux pour descendre le centre de gravité.")

    kinetic_chain = pose_data.get("kinetic_chain", {})
    if not kinetic_chain.get("sequential_order_ok", True):
        suggestions.append("La chaîne cinétique pourrait être plus séquentielle : démarrez la frappe par la rotation du bassin avant celle des épaules.")

    if not suggestions:
        suggestions.append("Continuez à travailler la régularité du geste avec ce mouvement comme référence.")

    return suggestions[:4]
