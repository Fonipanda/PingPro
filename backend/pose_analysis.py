"""
Analyse de pose avec MediaPipe pour PingPro.
Extrait les landmarks 3D, calcule les angles articulaires, la chaîne cinétique
et génère des visualisations 2D.
"""

import base64
import io
import logging
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

# MediaPipe imports
import mediapipe as mp
from mediapipe.tasks.python.vision import PoseLandmarker, RunningMode, PoseLandmarkerOptions
from mediapipe.tasks.python import BaseOptions

logger = logging.getLogger(__name__)

# MediaPipe Pose landmarks indices
MP_POSE_LANDMARKS = {
    "NOSE": 0,
    "LEFT_SHOULDER": 11,
    "RIGHT_SHOULDER": 12,
    "LEFT_ELBOW": 13,
    "RIGHT_ELBOW": 14,
    "LEFT_WRIST": 15,
    "RIGHT_WRIST": 16,
    "LEFT_HIP": 23,
    "RIGHT_HIP": 24,
    "LEFT_KNEE": 25,
    "RIGHT_KNEE": 26,
    "LEFT_ANKLE": 27,
    "RIGHT_ANKLE": 28,
    "LEFT_FOOT_INDEX": 31,
    "RIGHT_FOOT_INDEX": 32,
}

# Connexions du squelette pour la visualisation
SKELETON_CONNECTIONS = [
    ("LEFT_SHOULDER", "RIGHT_SHOULDER"),
    ("LEFT_SHOULDER", "LEFT_ELBOW"),
    ("RIGHT_SHOULDER", "RIGHT_ELBOW"),
    ("LEFT_ELBOW", "LEFT_WRIST"),
    ("RIGHT_ELBOW", "RIGHT_WRIST"),
    ("LEFT_SHOULDER", "LEFT_HIP"),
    ("RIGHT_SHOULDER", "RIGHT_HIP"),
    ("LEFT_HIP", "RIGHT_HIP"),
    ("LEFT_HIP", "LEFT_KNEE"),
    ("RIGHT_HIP", "RIGHT_KNEE"),
    ("LEFT_KNEE", "LEFT_ANKLE"),
    ("RIGHT_KNEE", "RIGHT_ANKLE"),
]


def _get_landmark(landmarks: List[Dict[str, float]], name: str) -> Optional[Dict[str, float]]:
    idx = MP_POSE_LANDMARKS.get(name)
    if idx is None or idx >= len(landmarks):
        return None
    return landmarks[idx]


def _angle_3points(a: Dict[str, float], b: Dict[str, float], c: Dict[str, float]) -> float:
    """Calcule l'angle ABC en degrés."""
    ba = np.array([a["x"] - b["x"], a["y"] - b["y"], a.get("z", 0) - b.get("z", 0)])
    bc = np.array([c["x"] - b["x"], c["y"] - b["y"], c.get("z", 0) - b.get("z", 0)])
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba == 0 or norm_bc == 0:
        return 0.0
    cosine = np.dot(ba, bc) / (norm_ba * norm_bc)
    cosine = np.clip(cosine, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


def _distance_2d(a: Dict[str, float], b: Dict[str, float]) -> float:
    return math.sqrt((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2)


def _landmark_to_dict(lm) -> Dict[str, float]:
    return {
        "x": lm.x,
        "y": lm.y,
        "z": lm.z,
        "visibility": getattr(lm, "visibility", 1.0),
        "presence": getattr(lm, "presence", 1.0),
    }


class PoseAnalyzer:
    def __init__(self, model_asset_path: Optional[str] = None):
        """Initialise le PoseLandmarker de MediaPipe."""
        if model_asset_path is None:
            # Utilise le modèle par défaut fourni avec mediapipe
            model_path = Path(__file__).parent / "pose_landmarker.task"
            if not model_path.exists():
                # Télécharge le modèle si nécessaire
                import urllib.request
                url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task"
                logger.info(f"Downloading pose landmarker model to {model_path}")
                urllib.request.urlretrieve(url, model_path)
            model_asset_path = str(model_path)

        base_options = BaseOptions(model_asset_path=model_asset_path)
        options = PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=RunningMode.VIDEO,
            num_poses=2,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = PoseLandmarker.create_from_options(options)

    def close(self):
        """Ferme le landmarker de manière idempotente (safe à appeler plusieurs fois)."""
        try:
            if self.landmarker is not None:
                self.landmarker.close()
        except Exception as e:
            logger.warning(f"Error closing PoseLandmarker: {e}")
        finally:
            self.landmarker = None

    def extract_landmarks(
        self,
        video_path: str,
        sample_rate: int = 5,
        max_frames: int = 1000,
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Extrait les landmarks 3D pour chaque frame échantillonnée.
        Retourne la liste des frames et le fps de la vidéo.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frames: List[Dict[str, Any]] = []
        frame_idx = 0
        processed = 0

        try:
            while frame_idx < frame_count and processed < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % sample_rate == 0:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    results = self.landmarker.detect_for_video(mp_image, int(frame_idx * 1000 / fps))

                    detected_poses = []
                    if results.pose_landmarks:
                        for pose in results.pose_landmarks:
                            detected_poses.append([_landmark_to_dict(lm) for lm in pose])

                    frames.append(
                        {
                            "frame_idx": frame_idx,
                            "timestamp": round(frame_idx / fps, 3),
                            "poses": detected_poses,
                        }
                    )
                    processed += 1

                frame_idx += 1
        finally:
            cap.release()
            self.close()
        return frames, fps

    @staticmethod
    def calculate_joint_angles(landmarks: List[Dict[str, float]]) -> Dict[str, float]:
        """Calcule les angles articulaires principaux pour un seul joueur."""
        angles = {}

        # Côté droit (raquette pour un droitier)
        shoulder = _get_landmark(landmarks, "RIGHT_SHOULDER")
        elbow = _get_landmark(landmarks, "RIGHT_ELBOW")
        wrist = _get_landmark(landmarks, "RIGHT_WRIST")
        hip = _get_landmark(landmarks, "RIGHT_HIP")
        knee = _get_landmark(landmarks, "RIGHT_KNEE")
        ankle = _get_landmark(landmarks, "RIGHT_ANKLE")
        left_shoulder = _get_landmark(landmarks, "LEFT_SHOULDER")
        left_hip = _get_landmark(landmarks, "LEFT_HIP")
        nose = _get_landmark(landmarks, "NOSE")

        if shoulder and elbow and wrist:
            angles["elbow"] = _angle_3points(shoulder, elbow, wrist)
        if hip and shoulder and elbow:
            angles["shoulder_elbow"] = _angle_3points(hip, shoulder, elbow)
        if hip and knee and ankle:
            angles["knee"] = _angle_3points(hip, knee, ankle)
        if shoulder and hip and knee:
            angles["hip_flexion"] = _angle_3points(shoulder, hip, knee)
        if left_shoulder and shoulder and hip:
            angles["shoulder_abduction"] = _angle_3points(left_shoulder, shoulder, hip)
        if left_hip and hip and shoulder:
            angles["hip_abduction"] = _angle_3points(left_hip, hip, shoulder)
        if nose and shoulder and hip:
            angles["trunk_forward_lean"] = _angle_3points(nose, shoulder, hip)
        if left_shoulder and shoulder and hip:
            # Torsion approximative épaules-hanches
            angles["trunk_rotation"] = _angle_3points(left_shoulder, shoulder, hip)

        # Hauteur du centre de masse (approximée par le centre des hanches)
        if hip and ankle and shoulder:
            hip_height = hip["y"]
            body_height = _distance_2d(shoulder, ankle)
            angles["center_of_mass_height_ratio"] = round(hip_height / max(body_height, 1e-6), 3)

        return angles

    @staticmethod
    def detect_stroke_phases(frames: List[Dict[str, Any]], dominant_side: str = "right") -> Dict[str, Any]:
        """
        Détecte les phases du geste (armé, frappe, accompagnement) à partir
        de la vitesse du poignet et de la rotation du tronc.
        """
        wrist_name = "RIGHT_WRIST" if dominant_side == "right" else "LEFT_WRIST"
        shoulder_name = "RIGHT_SHOULDER" if dominant_side == "right" else "LEFT_SHOULDER"
        hip_name = "RIGHT_HIP" if dominant_side == "right" else "LEFT_HIP"

        speeds = []
        rotations = []
        timestamps = []

        prev_wrist = None
        prev_time = None
        for frame in frames:
            poses = frame.get("poses", [])
            if not poses:
                continue
            # Prend la pose principale (première détectée)
            landmarks = poses[0]
            wrist = _get_landmark(landmarks, wrist_name)
            shoulder = _get_landmark(landmarks, shoulder_name)
            hip = _get_landmark(landmarks, hip_name)

            if wrist is None or shoulder is None or hip is None:
                continue

            if prev_wrist is not None and prev_time is not None:
                dt = frame["timestamp"] - prev_time
                if dt > 0:
                    speed = _distance_2d(wrist, prev_wrist) / dt
                    speeds.append(speed)
                else:
                    speeds.append(0.0)
            else:
                speeds.append(0.0)

            # Rotation approximative : angle horizontal épaule-hanche-bras
            rotation = math.atan2(shoulder["y"] - hip["y"], shoulder["x"] - hip["x"])
            rotations.append(rotation)
            timestamps.append(frame["timestamp"])

            prev_wrist = wrist
            prev_time = frame["timestamp"]

        if not speeds:
            return {"phases": {}, "contact_frame": None}

        speeds = np.array(speeds)
        contact_idx = int(np.argmax(speeds))

        # Détecter l'armé (vitesse croissante avant le contact)
        # et l'accompagnement (vitesse décroissante après le contact)
        backswing_idx = max(0, contact_idx - 1)
        for i in range(contact_idx - 1, -1, -1):
            if speeds[i] < speeds[i + 1]:
                backswing_idx = i
            else:
                break

        follow_through_idx = min(len(speeds) - 1, contact_idx + 1)
        for i in range(contact_idx + 1, len(speeds)):
            if speeds[i] < speeds[i - 1]:
                follow_through_idx = i
            else:
                break

        return {
            "phases": {
                "backswing": {
                    "start_timestamp": timestamps[backswing_idx] if timestamps else 0,
                    "frame_idx": backswing_idx,
                },
                "contact": {
                    "timestamp": timestamps[contact_idx] if timestamps else 0,
                    "frame_idx": contact_idx,
                    "max_wrist_speed": float(speeds[contact_idx]) if len(speeds) else 0.0,
                },
                "follow_through": {
                    "end_timestamp": timestamps[follow_through_idx] if timestamps else 0,
                    "frame_idx": follow_through_idx,
                },
            },
            "contact_frame": contact_idx,
            "dominant_side": dominant_side,
        }

    @staticmethod
    def calculate_kinetic_chain(frames: List[Dict[str, Any]], dominant_side: str = "right") -> Dict[str, Any]:
        """
        Calcule la chaîne cinétique : instants et vitesses maximales des segments
        bassin → épaules → avant-bras.
        """
        hip_name = "RIGHT_HIP" if dominant_side == "right" else "LEFT_HIP"
        shoulder_name = "RIGHT_SHOULDER" if dominant_side == "right" else "LEFT_SHOULDER"
        elbow_name = "RIGHT_ELBOW" if dominant_side == "right" else "LEFT_ELBOW"
        wrist_name = "RIGHT_WRIST" if dominant_side == "right" else "LEFT_WRIST"

        segments = {
            "hips": hip_name,
            "shoulders": shoulder_name,
            "forearm": wrist_name,  # proxy: vitesse du poignet
        }

        results = {}
        prev_points = {}
        prev_time = None
        max_speeds = {name: 0.0 for name in segments}
        max_times = {name: 0.0 for name in segments}

        for frame in frames:
            poses = frame.get("poses", [])
            if not poses:
                continue
            landmarks = poses[0]
            time = frame["timestamp"]

            for seg_name, lm_name in segments.items():
                point = _get_landmark(landmarks, lm_name)
                if point is None:
                    continue
                if seg_name in prev_points and prev_time is not None:
                    dt = time - prev_time
                    if dt > 0:
                        speed = _distance_2d(point, prev_points[seg_name]) / dt
                        if speed > max_speeds[seg_name]:
                            max_speeds[seg_name] = speed
                            max_times[seg_name] = time
                prev_points[seg_name] = point

            prev_time = time

        for seg_name in segments:
            results[seg_name] = {
                "max_speed": round(max_speeds[seg_name], 3),
                "timestamp": round(max_times[seg_name], 3),
            }

        # Ordre séquentiel idéal : hips avant shoulders avant forearm
        order_ok = max_times["hips"] <= max_times["shoulders"] <= max_times["forearm"]
        results["sequential_order_ok"] = bool(order_ok)
        results["quality_score"] = 100 if order_ok else 50

        return results

    @staticmethod
    def detect_players(frames: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Pour l'analyse de match : détecte les deux joueurs et leur position moyenne.
        """
        positions = {"left": [], "right": []}
        for frame in frames:
            for pose in frame.get("poses", []):
                left_hip = _get_landmark(pose, "LEFT_HIP")
                right_hip = _get_landmark(pose, "RIGHT_HIP")
                if left_hip and right_hip:
                    center_x = (left_hip["x"] + right_hip["x"]) / 2
                    side = "left" if center_x < 0.5 else "right"
                    positions[side].append(
                        {
                            "x": center_x,
                            "y": (left_hip["y"] + right_hip["y"]) / 2,
                            "timestamp": frame["timestamp"],
                        }
                    )

        heatmap = {}
        for side, pts in positions.items():
            if not pts:
                continue
            xs = [p["x"] for p in pts]
            ys = [p["y"] for p in pts]
            heatmap[side] = {
                "avg_x": round(sum(xs) / len(xs), 3),
                "avg_y": round(sum(ys) / len(ys), 3),
                "positions": pts[:200],  # limite pour la taille du JSON
            }

        return heatmap

    def generate_overlay_frame(
        self,
        video_path: str,
        frame_idx: int,
        landmarks: List[Dict[str, float]],
        output_size: Optional[Tuple[int, int]] = None,
    ) -> str:
        """
        Génère une image du squelette 2D encodée en base64.
        """
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return ""

        if output_size:
            frame = cv2.resize(frame, output_size)
            scale_x = output_size[0] / frame.shape[1]
            scale_y = output_size[1] / frame.shape[0]
        else:
            scale_x, scale_y = 1.0, 1.0

        h, w = frame.shape[:2]
        for connection in SKELETON_CONNECTIONS:
            a = _get_landmark(landmarks, connection[0])
            b = _get_landmark(landmarks, connection[1])
            if a and b:
                pt1 = (int(a["x"] * w * scale_x), int(a["y"] * h * scale_y))
                pt2 = (int(b["x"] * w * scale_x), int(b["y"] * h * scale_y))
                cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

        for name, idx in MP_POSE_LANDMARKS.items():
            if idx < len(landmarks):
                lm = landmarks[idx]
                x = int(lm["x"] * w * scale_x)
                y = int(lm["y"] * h * scale_y)
                cv2.circle(frame, (x, y), 4, (0, 0, 255), -1)

        # Conversion en base64
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        buffer = io.BytesIO()
        pil_img.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


def analyze_video_pose(
    video_path: str,
    analysis_id: str,
    player_side: str = "droite",
    compilations_dir: str = "compilations",
    sample_rate: int = 5,
) -> Dict[str, Any]:
    """
    Fonction principale : analyse la pose sur une vidéo et retourne un dict structuré.
    """
    dominant_side = "right" if player_side in ("droite", "right") else "left"
    analyzer = PoseAnalyzer()

    try:
        frames, fps = analyzer.extract_landmarks(video_path, sample_rate=sample_rate)
    except Exception as e:
        logger.error(f"Pose extraction failed: {e}")
        return {"error": str(e)}

    if not frames:
        return {"error": "No pose detected"}

    # Phase de frappe et frame de contact
    phase_data = PoseAnalyzer.detect_stroke_phases(frames, dominant_side)

    # Angles au moment du contact
    contact_frame_idx = phase_data.get("contact_frame") or 0
    contact_frame = frames[min(contact_frame_idx, len(frames) - 1)]
    contact_angles = {}
    if contact_frame.get("poses"):
        contact_angles = PoseAnalyzer.calculate_joint_angles(contact_frame["poses"][0])

    # Chaîne cinétique
    kinetic_chain = PoseAnalyzer.calculate_kinetic_chain(frames, dominant_side)

    # Heatmap de placement (match)
    player_heatmap = PoseAnalyzer.detect_players(frames)

    # Générer des frames overlay
    out_dir = Path(compilations_dir) / analysis_id / "pose_frames"
    out_dir.mkdir(parents=True, exist_ok=True)
    overlay_paths = []
    key_indices = [
        phase_data.get("phases", {}).get("backswing", {}).get("frame_idx", 0),
        contact_frame_idx,
        phase_data.get("phases", {}).get("follow_through", {}).get("frame_idx", 0),
    ]
    key_indices = list(set([max(0, min(idx, len(frames) - 1)) for idx in key_indices]))

    for idx in key_indices:
        frame = frames[idx]
        if not frame.get("poses"):
            continue
        b64 = analyzer.generate_overlay_frame(
            video_path, frame["frame_idx"], frame["poses"][0], output_size=(640, 480)
        )
        if b64:
            path = out_dir / f"frame_{frame['frame_idx']}.jpg"
            with open(path, "wb") as f:
                f.write(base64.b64decode(b64))
            overlay_paths.append(str(path))

    return {
        "fps": fps,
        "sample_rate": sample_rate,
        "total_frames_analyzed": len(frames),
        "dominant_side": dominant_side,
        "contact_angles": contact_angles,
        "phases": phase_data.get("phases", {}),
        "kinetic_chain": kinetic_chain,
        "player_heatmap": player_heatmap,
        "overlay_frames": overlay_paths,
        "frames": frames[:200],  # limit payload size for comparison/3D view
    }


# Compatibility alias for legacy import
PoseLandmarkerResult = mp.tasks.vision.PoseLandmarkerResult
