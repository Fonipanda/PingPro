"""
Détection et suivi de balle par modèle ONNX pour PingPro.

Remplace (avec repli propre) l'heuristique couleur/forme de ttnet_analysis.

- Détecteur : YOLO nano fine-tuné "table tennis ball", exporté ONNX.
  Le fichier attendu est backend/models/ball_yolo.onnx (voir backend/models/README.md
  et tools/export_ball_model.py pour la génération).
- Exécution : onnxruntime (CPU par défaut, DirectML si disponible sur iGPU AMD).
- Suivi : prédiction à vitesse constante + association au plus proche voisin.

Si le modèle ou onnxruntime est absent, `get_onnx_ball_detector()` retourne None
et le pipeline continue avec l'heuristique existante (aucune régression).
"""

import logging
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "ball_yolo.onnx"


def _create_session(model_path: Path):
    """Crée une session onnxruntime avec le meilleur provider disponible."""
    import onnxruntime as ort

    available = ort.get_available_providers()
    preferred = [p for p in ("DmlExecutionProvider", "CPUExecutionProvider") if p in available]
    if not preferred:
        preferred = available
    logger.info(f"Ball ONNX model providers: {preferred}")
    return ort.InferenceSession(str(model_path), providers=preferred)


class OnnxBallDetector:
    """Détecteur de balle YOLO exporté en ONNX (compatible YOLOv8/11)."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: float = 0.30,
        input_size: int = 640,
    ):
        path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        if not path.exists():
            raise FileNotFoundError(f"Modèle balle introuvable: {path}")
        self.session = _create_session(path)
        input_info = self.session.get_inputs()[0]
        self.input_name = input_info.name
        # YOLO exports ont une entrée dynamique ou fixe; on lit la taille annoncée
        shape = input_info.shape  # ex: [1, 3, 640, 640] ou [1, 3, 'height', 'width']
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

    def _nms(self, boxes: np.ndarray, scores: np.ndarray, iou_thr: float = 0.45) -> List[int]:
        if len(boxes) == 0:
            return []
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
            iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
            order = order[1:][iou <= iou_thr]
        return keep

    def detect(self, frame: np.ndarray) -> List[Tuple[int, int, float, float]]:
        """Retourne [(x, y, confidence, radius)] en coordonnées de l'image d'origine."""
        padded, scale, pad_x, pad_y = self._letterbox(frame)
        blob = cv2.dnn.blobFromImage(padded, 1.0 / 255.0, swapRB=True)
        outputs = self.session.run(None, {self.input_name: blob})
        pred = outputs[0]
        # YOLOv8/11: (1, 4+nc, N) -> transposer en (N, 4+nc)
        if pred.ndim == 3:
            pred = pred[0]
        if pred.shape[0] < pred.shape[1]:
            pred = pred.T
        num_classes = pred.shape[1] - 4
        boxes_cxcywh = pred[:, :4]
        class_scores = pred[:, 4:]
        class_ids = np.argmax(class_scores, axis=1)
        scores = class_scores[np.arange(len(class_scores)), class_ids]

        mask = scores >= self.conf_threshold
        boxes_cxcywh, scores, class_ids = boxes_cxcywh[mask], scores[mask], class_ids[mask]
        if len(scores) == 0:
            return []

        # cxcywh -> xyxy (repère letterbox)
        xy = boxes_cxcywh[:, :2]
        wh = boxes_cxcywh[:, 2:]
        boxes_xyxy = np.concatenate([xy - wh / 2, xy + wh / 2], axis=1)
        keep = self._nms(boxes_xyxy, scores)

        results: List[Tuple[int, int, float, float]] = []
        ih, iw = frame.shape[:2]
        for i in keep:
            x1, y1, x2, y2 = boxes_xyxy[i]
            # dé-letterbox puis retour aux coordonnées d'origine
            x1 = (x1 - pad_x) / scale
            y1 = (y1 - pad_y) / scale
            x2 = (x2 - pad_x) / scale
            y2 = (y2 - pad_y) / scale
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(iw, x2), min(ih, y2)
            cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            radius = max((x2 - x1), (y2 - y1)) / 2.0
            # Une balle est petite ; filtre les grosses boîtes (joueurs, table)
            if radius > 40:
                continue
            results.append((int(cx), int(cy), float(scores[i]), float(radius)))
        results.sort(key=lambda c: c[2], reverse=True)
        return results

    def close(self):
        pass


class BallTracker:
    """Suivi temporel simple : prédiction à vitesse constante + gating."""

    def __init__(self, history: int = 30, gate_px: float = 80.0):
        self.history: deque = deque(maxlen=history)  # (t, x, y, conf, radius)
        self.gate_px = gate_px

    def predict(self) -> Optional[Tuple[float, float]]:
        if len(self.history) < 2:
            return None
        (_, x1, y1, _, _), (_, x2, y2, _, _) = list(self.history)[-2:]
        return (2 * x2 - x1, 2 * y2 - y1)

    def update(
        self,
        candidates: List[Tuple[int, int, float, float]],
        timestamp: Optional[float] = None,
    ) -> Optional[Tuple[int, int, float]]:
        """
        Associe la meilleure candidate au suivi courant et met à jour l'historique.
        Accepte des candidats (x, y, conf) ou (x, y, conf, radius) ; retourne (x, y, conf).
        """
        if not candidates:
            return None
        # Normalisation : tous les candidats en (x, y, conf, radius)
        norm = [
            (c[0], c[1], float(c[2]), float(c[3]) if len(c) > 3 else 0.0)
            for c in candidates
        ]
        candidates = norm

        pred = self.predict()
        if pred is None:
            best = max(candidates, key=lambda c: c[2])
        else:
            best = min(
                candidates,
                key=lambda c: (c[0] - pred[0]) ** 2 + (c[1] - pred[1]) ** 2,
            )
            dist = ((best[0] - pred[0]) ** 2 + (best[1] - pred[1]) ** 2) ** 0.5
            if dist > self.gate_px:
                # Rien de cohérent avec la trajectoire : on garde la candidate la plus
                # confiante mais sans mise à jour de l'historique de vitesse.
                best = max(candidates, key=lambda c: c[2])
                return (int(best[0]), int(best[1]), float(best[2]))
        self.history.append((timestamp or time.time(), best[0], best[1], best[2], best[3]))
        return (int(best[0]), int(best[1]), float(best[2]))


_detector_singleton: Optional[OnnxBallDetector] = None
_detector_attempted = False


def get_onnx_ball_detector() -> Optional[OnnxBallDetector]:
    """Retourne le détecteur ONNX partagé, ou None si indisponible (une seule tentative)."""
    global _detector_singleton, _detector_attempted
    if _detector_singleton is not None:
        return _detector_singleton
    if _detector_attempted:
        return None
    _detector_attempted = True
    if not DEFAULT_MODEL_PATH.exists():
        logger.info(
            "Aucun modèle balle ONNX (%s) : repli sur l'heuristique TTNet. "
            "Voir backend/models/README.md pour activer le modèle.",
            DEFAULT_MODEL_PATH,
        )
        return None
    try:
        _detector_singleton = OnnxBallDetector()
        logger.info("Détecteur de balle ONNX chargé : %s", DEFAULT_MODEL_PATH)
        return _detector_singleton
    except ImportError:
        logger.info("onnxruntime non installé : repli sur l'heuristique TTNet.")
        return None
    except Exception as e:
        logger.warning(f"Chargement du modèle balle impossible ({e}) : repli heuristique.")
        return None
