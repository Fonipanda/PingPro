"""
Détection et suivi des deux joueurs (gauche / droite) pour PingPro.

- Détection : YOLO générique exporté ONNX (classe `person` du COCO), même
  mécanique que le détecteur de balle. Le fichier attendu est
  backend/models/yolov8n.onnx (base COCO, 80 classes) — voir
  backend/models/README.md.
- Attribution de camp : la ligne de filet (milieu de la table en image, via le
  quad de la table si disponible, sinon le centre de l'image) sépare les deux
  moitiés ; chaque personne est assignée à "gauche" ou "droite".
- Suivi : les identités sont stabilisées sur la vidéo par association au plus
  proche centroid (hystérésis simple).

Si le modèle est absent, `analyze_players()` retourne {"available": False}
et le reste du pipeline se dégrade proprement (comportement v2).
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "models"
PERSON_MODEL_PATH = MODELS_DIR / "yolov8n.onnx"

PERSON_CLASS_ID = 0  # COCO


def _create_session(model_path: Path):
    import onnxruntime as ort

    available = ort.get_available_providers()
    preferred = [p for p in ("DmlExecutionProvider", "CPUExecutionProvider") if p in available]
    if not preferred:
        preferred = available
    logger.info(f"Players ONNX model providers: {preferred}")
    return ort.InferenceSession(str(model_path), providers=preferred)


class YoloPersonDetector:
    """Détecteur de personnes YOLO ONNX (sortie YOLOv8/11 : (1, 4+nc, N))."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: float = 0.35,
        input_size: int = 640,
    ):
        path = Path(model_path) if model_path else PERSON_MODEL_PATH
        if not path.exists():
            raise FileNotFoundError(f"Modèle personnes introuvable: {path}")
        self.session = _create_session(path)
        self.input_name = self.session.get_inputs()[0].name
        shape = self.session.get_inputs()[0].shape
        self.input_size = input_size
        if isinstance(shape, list) and len(shape) == 4 and isinstance(shape[2], int):
            self.input_size = shape[2]
        self.conf_threshold = conf_threshold

    def _letterbox(self, frame: np.ndarray) -> Tuple[np.ndarray, float, int, int]:
        h, w = frame.shape[:2]
        scale = min(self.input_size / w, self.input_size / h)
        new_w, new_h = int(round(w * scale)), int(round(h * scale))
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        padded = np.full((self.input_size, self.input_size, 3), 114, dtype=np.uint8)
        pad_x, pad_y = (self.input_size - new_w) // 2, (self.input_size - new_h) // 2
        padded[pad_y : pad_y + new_h, pad_x : pad_x + new_w] = resized
        return padded, scale, pad_x, pad_y

    def _nms(self, boxes: np.ndarray, scores: np.ndarray, iou_thr: float = 0.5) -> List[int]:
        if len(boxes) == 0:
            return []
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(int(i))
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
            order = order[1:][iou <= iou_thr]
        return keep

    def detect(self, frame: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
        """Retourne les boîtes personnes [(x1, y1, x2, y2, conf)] en pixels d'origine."""
        padded, scale, pad_x, pad_y = self._letterbox(frame)
        blob = cv2.dnn.blobFromImage(padded, 1.0 / 255.0, swapRB=True)
        outputs = self.session.run(None, {self.input_name: blob})
        pred = outputs[0]
        if pred.ndim == 3:
            pred = pred[0]
        if pred.shape[0] < pred.shape[1]:
            pred = pred.T
        boxes_cxcywh = pred[:, :4]
        class_scores = pred[:, 4:]
        class_ids = np.argmax(class_scores, axis=1)
        scores = class_scores[np.arange(len(class_scores)), class_ids]

        mask = (class_ids == PERSON_CLASS_ID) & (scores >= self.conf_threshold)
        boxes_cxcywh, scores = boxes_cxcywh[mask], scores[mask]
        if len(scores) == 0:
            return []

        xy, wh = boxes_cxcywh[:, :2], boxes_cxcywh[:, 2:]
        boxes_xyxy = np.concatenate([xy - wh / 2, xy + wh / 2], axis=1)
        keep = self._nms(boxes_xyxy, scores)

        results: List[Tuple[int, int, int, int, float]] = []
        ih, iw = frame.shape[:2]
        for i in keep:
            x1, y1, x2, y2 = boxes_xyxy[i]
            x1 = max(0, (x1 - pad_x) / scale)
            y1 = max(0, (y1 - pad_y) / scale)
            x2 = min(iw, (x2 - pad_x) / scale)
            y2 = min(ih, (y2 - pad_y) / scale)
            results.append((int(x1), int(y1), int(x2), int(y2), float(scores[i])))
        results.sort(key=lambda b: b[4], reverse=True)
        return results

    def close(self):
        pass


class PlayersTracker:
    """Suit jusqu'à 2 joueurs et les assigne aux camps gauche / droite."""

    def __init__(self, net_x: Optional[float] = None, frame_width: int = 1920):
        self.detector: Optional[YoloPersonDetector] = None
        try:
            self.detector = YoloPersonDetector()
        except Exception as e:
            logger.info(f"Suivi des joueurs indisponible ({e}).")
        self.net_x = net_x if net_x is not None else frame_width / 2.0
        # état des identités : camp -> (cx, cy)
        self.tracks: Dict[str, Optional[Tuple[float, float]]] = {"left": None, "right": None}

    def _assign_sides(
        self, boxes: List[Tuple[int, int, int, int, float]]
    ) -> Dict[str, Optional[Tuple[int, int, int, int, float]]]:
        """Assigne au plus 1 box par camp (le plus proche du track existant)."""
        left_candidates = [b for b in boxes if (b[0] + b[2]) / 2 < self.net_x]
        right_candidates = [b for b in boxes if (b[0] + b[2]) / 2 >= self.net_x]

        def pick(cands, side):
            if not cands:
                return None
            track = self.tracks.get(side)
            if track is None:
                return max(cands, key=lambda b: b[4])
            return min(cands, key=lambda b: ((b[0] + b[2]) / 2 - track[0]) ** 2 + ((b[1] + b[3]) / 2 - track[1]) ** 2)

        assignment = {"left": pick(left_candidates, "left"), "right": pick(right_candidates, "right")}
        # mise à jour des tracks (lissage)
        for side, box in assignment.items():
            if box is not None:
                cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                prev = self.tracks.get(side)
                self.tracks[side] = (cx, cy) if prev is None else (0.7 * prev[0] + 0.3 * cx, 0.7 * prev[1] + 0.3 * cy)
        return assignment

    def process_frame(self, frame: np.ndarray, timestamp: float) -> Dict[str, Any]:
        if self.detector is None:
            return {"available": False}
        boxes = self.detector.detect(frame)
        assignment = self._assign_sides(boxes)
        return {
            "available": True,
            "timestamp": round(float(timestamp), 2),
            "left": self._box_dict(assignment["left"]),
            "right": self._box_dict(assignment["right"]),
        }

    @staticmethod
    def _box_dict(box) -> Optional[Dict[str, float]]:
        if box is None:
            return None
        return {
            "x1": int(box[0]),
            "y1": int(box[1]),
            "x2": int(box[2]),
            "y2": int(box[3]),
            "confidence": round(float(box[4]), 2),
            "center_x": round((box[0] + box[2]) / 2, 1),
        }


def net_x_from_quad(quad: np.ndarray, frame_width: int) -> float:
    """
    Abscisse image approximative de la ligne de filet : milieu des milieux des
    petits côtés du quad table (ordre tl,tr,br,bl). Repli : centre de l'image.
    """
    try:
        q = np.asarray(quad, dtype=np.float32).reshape(4, 2)
        left_mid = (q[0] + q[3]) / 2.0
        right_mid = (q[1] + q[2]) / 2.0
        return float((left_mid[0] + right_mid[0]) / 2.0)
    except Exception:
        return frame_width / 2.0


def analyze_players(
    video_path: str,
    table_quad: Optional[np.ndarray] = None,
    detect_every: int = 4,
    max_frames: int = 2500,
) -> Dict[str, Any]:
    """
    Analyse les joueurs sur toute la vidéo (1 frame sur `detect_every`).
    Retourne {"available", "frames": [...], "summary"} — dégrade proprement.
    """
    tracker = PlayersTracker()
    if tracker.detector is None:
        return {"available": False, "reason": "Modèle yolov8n.onnx absent (voir backend/models/README.md)"}

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"available": False, "reason": "Vidéo illisible"}
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    if table_quad is not None:
        tracker.net_x = net_x_from_quad(table_quad, width)

    frames: List[Dict[str, Any]] = []
    idx = 0
    left_count = right_count = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret or idx > max_frames * detect_every:
                break
            if idx % detect_every == 0:
                res = tracker.process_frame(frame, idx / fps)
                if res.get("left"):
                    left_count += 1
                if res.get("right"):
                    right_count += 1
                frames.append(res)
            idx += 1
    finally:
        cap.release()

    total = len(frames) or 1
    return {
        "available": True,
        "frames": frames,
        "summary": {
            "frames_analyzed": len(frames),
            "left_detection_ratio": round(left_count / total, 2),
            "right_detection_ratio": round(right_count / total, 2),
            "net_x_px": round(tracker.net_x, 1),
        },
    }
