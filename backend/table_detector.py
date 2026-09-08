"""
Détection de la table de tennis de table et calcul d'homographie.

Le plan de la table (image) est projeté vers un repère réel en mètres :
- axe X : longueur de la table, x ∈ [-1.37, 1.37] (le filet est à x = 0)
- axe Y : largeur de la table, y ∈ [-0.7625, 0.7625]

Si la table n'est pas détectable, toutes les fonctions retournent None et
l'analyse de match se dégrade proprement (vitesses en pixels/frame).
"""

import logging
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Dimensions officielles ITTF (mètres)
TABLE_LENGTH = 2.74
TABLE_WIDTH = 1.525
HALF_LENGTH = TABLE_LENGTH / 2.0
HALF_WIDTH = TABLE_WIDTH / 2.0

# Repère cible : coins de la table (longueur en X, largeur en Y)
TARGET_CORNERS = np.array(
    [
        [-HALF_LENGTH, -HALF_WIDTH],
        [HALF_LENGTH, -HALF_WIDTH],
        [HALF_LENGTH, HALF_WIDTH],
        [-HALF_LENGTH, HALF_WIDTH],
    ],
    dtype=np.float32,
)


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Ordonne 4 points : haut-gauche, haut-droite, bas-droite, bas-gauche (image)."""
    pts = np.array(pts, dtype=np.float32).reshape(4, 2)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(d)]
    bl = pts[np.argmax(d)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


class TableDetector:
    """Détecte le quadrilatère de la table et construit l'homographie image -> table."""

    def __init__(self):
        self._cached_homography: Optional[np.ndarray] = None
        self._cached_quad: Optional[np.ndarray] = None

    def _table_mask(self, frame: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        masks = []
        # Bleu (table courante) : hue ~ 95-125
        masks.append(cv2.inRange(hsv, np.array([95, 60, 40]), np.array([125, 255, 255])))
        # Vert (anciennes tables) : hue ~ 35-85
        masks.append(cv2.inRange(hsv, np.array([35, 60, 40]), np.array([85, 255, 255])))
        mask = cv2.bitwise_or(*masks)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        return mask

    def detect_quad(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Détecte les 4 coins de la table dans une image (ou None)."""
        mask = self._table_mask(frame)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        largest = max(contours, key=cv2.contourArea)
        area_ratio = cv2.contourArea(largest) / (frame.shape[0] * frame.shape[1])
        if area_ratio < 0.02:
            return None

        # Polygone approximé ; s'il n'a pas 4 sommets, on retombe sur le rectangle englobant
        peri = cv2.arcLength(largest, True)
        approx = cv2.approxPolyDP(largest, 0.02 * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            quad = approx.reshape(4, 2).astype(np.float32)
        else:
            quad = cv2.boxPoints(cv2.minAreaRect(largest)).astype(np.float32)
        return _order_corners(quad)

    def detect_table_homography(
        self, video_path: str, num_samples: int = 8
    ) -> Optional[Dict[str, np.ndarray]]:
        """
        Échantillonne quelques frames réparties dans la vidéo, vote sur les
        quads détectés (médiane par coin) et construit l'homographie.
        """
        if self._cached_homography is not None:
            return {"quad": self._cached_quad, "H": self._cached_homography}

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        quads: List[np.ndarray] = []
        try:
            for i in range(num_samples):
                idx = int(total * (i + 0.5) / num_samples)
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret:
                    continue
                quad = self.detect_quad(frame)
                if quad is not None:
                    quads.append(quad)
        finally:
            cap.release()

        if len(quads) < max(2, num_samples // 4):
            logger.info("Table non détectée : stats de match en coordonnées pixels.")
            return None

        # Filtrer les quads aberrants (différence médiane trop grande)
        quads_arr = np.stack(quads)  # (n, 4, 2)
        median = np.median(quads_arr, axis=0)
        dists = np.linalg.norm(quads_arr - median, axis=2).mean(axis=1)
        threshold = np.percentile(dists, 75)
        good = quads_arr[dists <= threshold] if len(quads) > 2 else quads_arr
        if len(good) == 0:
            good = quads_arr
        quad = _order_corners(np.median(good, axis=0))

        H, _ = cv2.findHomography(quad.astype(np.float32), TARGET_CORNERS)
        if H is None or not np.isfinite(H).all() or abs(float(H[2, 2])) < 1e-9:
            logger.info("Homographie de table invalide : stats de match en coordonnées pixels.")
            return None

        H_inv, _ = cv2.findHomography(TARGET_CORNERS, quad.astype(np.float32))
        if H_inv is None or not np.isfinite(H_inv).all():
            H_inv = None

        self._cached_homography = H
        self._cached_quad = quad
        return {"quad": quad, "H": H, "H_inv": H_inv}

    @staticmethod
    def image_points_to_table(
        H: np.ndarray, points: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """Projette des points image vers le repère table (x longueur, y largeur).

        Retourne des floats Python (sérialisables en JSON par pydantic).
        """
        if not points:
            return []
        pts = np.array(points, dtype=np.float32).reshape(-1, 1, 2)
        projected = cv2.perspectiveTransform(pts, H)
        if projected is None:
            return []
        return [(float(p[0]), float(p[1])) for p in projected.reshape(-1, 2)]

    @staticmethod
    def point_in_table(quad: np.ndarray, point: Tuple[float, float]) -> bool:
        return cv2.pointPolygonTest(quad.astype(np.float32), (float(point[0]), float(point[1])), False) >= 0

    @staticmethod
    def meters_per_pixel(quad: np.ndarray, frame_shape: Tuple[int, int]) -> Optional[float]:
        """Échelle approximative (m/pixel) au niveau de la table, via l'aire du quad."""
        area_px = cv2.contourArea(quad.astype(np.float32))
        if area_px <= 0:
            return None
        # Aire projetée de la table vue en perspective ≈ aire réelle / facteur de
        # foreshortening ; on prend le côté le plus long du quad (la longueur 2,74 m
        # est toujours le plus grand côté réel de la table).
        e1 = np.linalg.norm(quad[1] - quad[0])
        e2 = np.linalg.norm(quad[2] - quad[1])
        longest_px = max(e1, e2)
        return TABLE_LENGTH / longest_px if longest_px > 0 else None
