"""
Analyse de match façon SportArc : placement de la balle, vitesse réelle,
schémas de frappe, phases et moments clés.

Entrées : frame_analyses produites par ttnet_analysis (positions balle horodatées
en temps vidéo) + détection de table optionnelle (homographie).
Sans table détectée, les vitesses restent en pixels/frame et le placement est
exprimé en coordonnées normalisées image.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from table_detector import (
    HALF_LENGTH,
    HALF_WIDTH,
    TABLE_LENGTH,
    TABLE_WIDTH,
    TableDetector,
)

logger = logging.getLogger(__name__)

# Un échange est cassé après ce silence de détection balle (s)
RALLY_GAP_S = 1.2
# Durée minimale pour qu'une séquence compte comme échange (s)
RALLY_MIN_DURATION_S = 0.8


def _extract_ball_points(frame_analyses: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    """Points balle horodatés en temps vidéo : [{t, x, y, conf}]."""
    points = []
    for fa in frame_analyses:
        pos = fa.get("ball_position")
        if not pos:
            continue
        t = fa.get("video_timestamp", fa.get("timestamp", 0.0))
        points.append({"t": float(t), "x": float(pos[0]), "y": float(pos[1]), "conf": float(pos[2])})
    return points


def segment_rallies(
    ball_points: List[Dict[str, float]],
    table_coords: Optional[List[Tuple[float, float]]] = None,
    min_confidence_ratio: float = 0.25,
) -> List[Dict[str, Any]]:
    """
    Segmentation des échanges à partir des silences de détection balle.
    Si table_coords est fourni, compte les traversées du filet (x=0) dans le
    repère table ; sinon retombe sur le changement de signe de dx image.
    """
    rallies: List[Dict[str, Any]] = []
    current: List[Dict[str, float]] = []

    def close_current():
        if len(current) < 2:
            return
        start, end = current[0]["t"], current[-1]["t"]
        duration = end - start
        if duration < RALLY_MIN_DURATION_S:
            return

        confidences = [p["conf"] for p in current]
        confidence_ratio = sum(1 for c in confidences if c and c > 0.3) / len(confidences)
        if confidence_ratio < min_confidence_ratio:
            return

        # Traversées du filet
        crossings = 0
        if table_coords and len(table_coords) == len(ball_points):
            idx0 = ball_points.index(current[0])
            for i in range(idx0 + 2, idx0 + len(current)):
                x1 = table_coords[i - 1][0]
                x2 = table_coords[i][0]
                if x1 == 0 or x2 == 0:
                    continue
                if x1 * x2 < 0 and abs(x2 - x1) > 0.05:
                    crossings += 1
        else:
            for i in range(2, len(current)):
                dx1 = current[i - 1]["x"] - current[i - 2]["x"]
                dx2 = current[i]["x"] - current[i - 1]["x"]
                if dx1 * dx2 < 0 and abs(dx1) + abs(dx2) > 0:
                    crossings += 1

        rallies.append(
            {
                "start_time": round(start, 2),
                "end_time": round(end, 2),
                "duration": round(duration, 2),
                "stroke_count": max(2, crossings + 1),
                "detections": len(current),
                "confidence_ratio": round(confidence_ratio, 2),
            }
        )

    for pt in ball_points:
        if current and (pt["t"] - current[-1]["t"]) > RALLY_GAP_S:
            close_current()
            current = []
        current.append(pt)
    close_current()
    return rallies


def _table_positions(
    ball_points: List[Dict[str, float]], table_info: Optional[Dict[str, Any]]
) -> Tuple[List[Tuple[float, float]], List[bool]]:
    """Convertit les points image en coordonnées table (m) + validité (dans le quad)."""
    if not table_info:
        return [], []
    H = table_info["H"]
    quad = table_info["quad"]
    pts = [(p["x"], p["y"]) for p in ball_points]
    coords = TableDetector.image_points_to_table(H, pts)
    inside = [TableDetector.point_in_table(quad, p) for p in pts]
    return [tuple(c) for c in coords], inside


def _placement_analysis(
    table_coords: List[Tuple[float, float]], inside_flags: List[bool]
) -> Dict[str, Any]:
    """Répartition des rebonds par zone : 2 moitiés x 3 zones en longueur."""
    on_table = [c for c, ok in zip(table_coords, inside_flags) if ok]
    if not on_table:
        return {"available": False, "reason": "Table non détectée ou balle jamais sur la table"}

    # Zone longueur : côté joueur (x<0), milieu, côté adversaire (x>0)
    # Zone largeur : revers (y<0), centre, coup droit (y>0) — convention image
    grid = np.zeros((2, 3, 3), dtype=int)  # [moitié][longueur][largeur]
    for x, y in on_table:
        half = 0 if x < 0 else 1
        ln = 0 if abs(x) < HALF_LENGTH / 3 else (1 if abs(x) < 2 * HALF_LENGTH / 3 else 2)
        wd = 0 if y < -HALF_WIDTH / 3 else (1 if y < HALF_WIDTH / 3 else 2)
        grid[half][ln][wd] += 1

    zones = {}
    labels_ln = ["fond", "milieu", "pres_filet"]
    labels_wd = ["revers", "centre", "coup_droit"]
    labels_half = ["moitie_1", "moitie_2"]
    for h in range(2):
        for l in range(3):
            for w in range(3):
                if grid[h][l][w] > 0:
                    zones[f"{labels_half[h]}.{labels_ln[l]}.{labels_wd[w]}"] = int(grid[h][l][w])

    return {
        "available": True,
        "total_balls_on_table": len(on_table),
        "zones": zones,
        "heatmap_grid": grid.tolist(),
        "table_dimensions_m": {"length": TABLE_LENGTH, "width": TABLE_WIDTH},
    }


def _speed_analysis(
    ball_points: List[Dict[str, float]],
    table_coords: List[Tuple[float, float]],
    table_info: Optional[Dict[str, Any]],
    fallback_scale_m_per_px: Optional[float],
) -> Dict[str, Any]:
    """Vitesses en m/s via homographie, sinon pixels/frame (+ échelle approx)."""
    speeds_px = []
    for i in range(1, len(ball_points)):
        p0, p1 = ball_points[i - 1], ball_points[i]
        dt = p1["t"] - p0["t"]
        if dt <= 0:
            continue
        dist = ((p1["x"] - p0["x"]) ** 2 + (p1["y"] - p0["y"]) ** 2) ** 0.5
        speeds_px.append(dist / dt)

    speeds_ms = []
    if table_info and len(table_coords) == len(ball_points) and len(table_coords) > 1:
        for i in range(1, len(table_coords)):
            if not (table_coords[i - 1] and table_coords[i]):
                continue
            dt = ball_points[i]["t"] - ball_points[i - 1]["t"]
            if dt <= 0:
                continue
            (x0, y0), (x1, y1) = table_coords[i - 1], table_coords[i]
            # Vitesses hors table = sauts d'homographie (points hors quad) : filtrées
            if abs(x1 - x0) > TABLE_LENGTH or abs(y1 - y0) > TABLE_WIDTH * 2:
                continue
            speeds_ms.append(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 / dt)

    result: Dict[str, Any] = {
        "average_speed_pixels_per_frame": round(float(np.mean(speeds_px)), 1) if speeds_px else 0.0,
        "max_speed_pixels_per_frame": round(float(np.max(speeds_px)), 1) if speeds_px else 0.0,
        "unit": "m/s" if speeds_ms else "pixels/s",
    }
    if speeds_ms:
        result["average_speed_ms"] = round(float(np.mean(speeds_ms)), 1)
        result["max_speed_ms"] = round(float(np.max(speeds_ms)), 1)
    elif fallback_scale_m_per_px:
        result["average_speed_ms_estimated"] = round(
            float(np.mean(speeds_px)) * fallback_scale_m_per_px, 1
        ) if speeds_px else 0.0
    return result


def _classify_stroke_side(speed_ms: float, table_y: float, speed_median_ms: float, left_handed: bool) -> str:
    """
    Estimation honnête du type de coup pour un rebond :
    - topspin vs coup poussé : vitesse locale vs vitesse médiane des rebonds
    - coup droit / revers : côté de la table (largeur), hypothèse joueur droitier
      inversée si joueur gaucher. L'orientation caméra est arbitraire : à préciser
      via player_side si connue.
    """
    kind = "topspin" if speed_ms > speed_median_ms else "coup"
    fh = table_y > 0
    if left_handed:
        fh = not fh
    side = "coup_droit" if fh else "revers"
    # Clés canoniques partagées avec le frontend (colorMap) et les overlays :
    # topspin_coup_droit | topspin_revers | coup_droit | revers
    return f"topspin_{side}" if kind == "topspin" else side


def _smooth_series(values: List[float], window: int = 3) -> List[float]:
    """Lissage par médiane glissante ; conserve les extrémités."""
    if len(values) < window:
        return values
    half = window // 2
    smoothed = []
    for i in range(len(values)):
        lo = max(0, i - half)
        hi = min(len(values), i + half + 1)
        smoothed.append(float(np.median(values[lo:hi])))
    return smoothed


def detect_bounces(
    ball_points: List[Dict[str, float]],
    table_coords: List[Tuple[float, float]],
    inside_flags: List[bool],
    left_handed: bool = False,
) -> List[Dict[str, Any]]:
    """Rebonds : changement de signe de la vitesse verticale de la balle sur la table."""
    n = len(ball_points)
    if n < 4 or not table_coords:
        return []

    # Lissage de la trajectoire verticale table pour réduire le bruit
    ys = _smooth_series([c[1] for c in table_coords], window=3)
    xs = [c[0] for c in table_coords]

    candidates = []
    for i in range(2, n - 2):
        if not (inside_flags and inside_flags[i] and inside_flags[i - 1] and inside_flags[i + 1]):
            continue
        y_prev, y_curr, y_next = ys[i - 1], ys[i], ys[i + 1]
        vy1, vy2 = y_curr - y_prev, y_next - y_curr
        # Rebond : descente puis remontée nette
        if not (vy1 < -0.005 and vy2 > 0.005 and (vy2 - vy1) > 0.01):
            continue

        # vitesse locale (m/s)
        dt1 = ball_points[i]["t"] - ball_points[i - 1]["t"]
        dt2 = ball_points[i + 1]["t"] - ball_points[i]["t"]
        speed = 0.0
        if dt1 > 0 and dt2 > 0:
            d1 = ((xs[i] - xs[i - 1]) ** 2 + (ys[i] - ys[i - 1]) ** 2) ** 0.5
            d2 = ((xs[i + 1] - xs[i]) ** 2 + (ys[i + 1] - ys[i]) ** 2) ** 0.5
            speed = (d1 + d2) / (dt1 + dt2)
        # filtrage des faux rebonds (balle quasi à l'arrêt ou hors plage réaliste)
        if speed < 0.3 or speed > 25.0:
            continue
        # le rebond doit être dans les limites de la table
        if abs(xs[i]) > HALF_LENGTH or abs(ys[i]) > HALF_WIDTH:
            continue

        candidates.append(
            {
                "timestamp": round(ball_points[i]["t"], 2),
                "table_x": round(xs[i], 2),
                "table_y": round(ys[i], 2),
                "confidence": min(1.0, (vy2 - vy1) / 0.2),
                "speed_ms": round(speed, 1),
            }
        )

    if candidates:
        median_speed = float(np.median([c["speed_ms"] for c in candidates]))
        for c in candidates:
            c["stroke_side"] = _classify_stroke_side(
                c["speed_ms"], c["table_y"], median_speed, left_handed
            )
            # Camp du rebond : table_x < 0 = moitié image-gauche (convention homographie)
            c["side"] = "gauche" if c["table_x"] < 0 else "droite"
    return candidates


def attribute_rallies(
    rallies: List[Dict[str, Any]], bounces: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Estime le gagnant de chaque échange : le dernier rebond détecté a atterri
    côté X, le camp adverse marque (l'échange s'arrête quand le retour échoue).
    winner_side = None si aucun rebond fiable dans l'échange.
    """
    events = []
    for rally in rallies:
        rb = [
            b for b in bounces
            if rally["start_time"] - 0.2 <= b["timestamp"] <= rally["end_time"] + 0.5
        ]
        winner_side = None
        last_side = None
        if rb:
            last = max(rb, key=lambda b: b["timestamp"])
            last_side = last["side"]
            winner_side = "droite" if last_side == "gauche" else "gauche"
        events.append(
            {
                "start_time": rally["start_time"],
                "end_time": rally["end_time"],
                "last_bounce_side": last_side,
                "winner_side": winner_side,
                "confident": winner_side is not None,
                "stroke_count": rally.get("stroke_count", 0),
            }
        )
    return events


def build_match_analysis(
    ttnet_results: Dict[str, Any],
    video_path: str,
    table_info: Optional[Dict[str, Any]] = None,
    fallback_scale_m_per_px: Optional[float] = None,
    player_side: Optional[str] = None,
    manual_quad: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Construit le bloc "Analyse de match" à partir des frame_analyses TTNet.
    Détecte la table à la demande si table_info n'est pas fourni ; un quad de
    calibrage manuel (4 coins image) prime sur l'auto-détection.
    """
    frame_analyses = ttnet_results.get("frame_analyses", [])
    ball_points = _extract_ball_points(frame_analyses)

    # Taux de détection balle (pour l'indicateur de qualité frontend)
    total_frames = len(frame_analyses)
    detected_frames = sum(1 for f in frame_analyses if f.get("ball_position"))
    ball_detection_rate = round(detected_frames / max(1, total_frames) * 100, 1)

    if table_info is None:
        try:
            detector = TableDetector()
            table_info = detector.detect_table_homography(video_path, manual_quad=manual_quad)
        except Exception as e:
            logger.warning(f"Détection de table échouée (non bloquant): {e}")
            table_info = None

    table_coords, inside_flags = _table_positions(ball_points, table_info)

    rallies = segment_rallies(ball_points, table_coords)
    placement = _placement_analysis(table_coords, inside_flags)
    speeds = _speed_analysis(ball_points, table_coords, table_info, fallback_scale_m_per_px)
    bounces = (
        detect_bounces(ball_points, table_coords, inside_flags, left_handed=(player_side == "gauche"))
        if table_info
        else []
    )

    longest = max(rallies, key=lambda r: r["stroke_count"], default=None)
    length_buckets = {
        "courts_1_3_coups": len([r for r in rallies if r["stroke_count"] <= 3]),
        "moyens_4_7_coups": len([r for r in rallies if 4 <= r["stroke_count"] <= 7]),
        "longs_8_plus": len([r for r in rallies if r["stroke_count"] > 7]),
    }

    scoring_events = attribute_rallies(rallies, bounces) if (rallies and bounces) else []
    confident_points = sum(1 for e in scoring_events if e.get("confident"))
    scoring_summary = {
        "total_points": len(scoring_events),
        "confident_points": confident_points,
        "estimated_points": len(scoring_events) - confident_points,
    }

    # Stats par camp : rebonds sur chaque moitié + vitesse moyenne par camp
    player_stats: Dict[str, Any] = {}
    if bounces:
        for side in ("gauche", "droite"):
            side_bounces = [b for b in bounces if b.get("side") == side]
            side_speeds = [b["speed_ms"] for b in side_bounces if b.get("speed_ms")]
            player_stats[side] = {
                "bounces": len(side_bounces),
                "avg_speed_ms": round(float(np.mean(side_speeds)), 1) if side_speeds else None,
            }

    return {
        "available": bool(rallies),
        "table_detected": table_info is not None,
        "table_source": (table_info or {}).get("source", "auto" if table_info else None),
        "table_quad_pixel": (
            [[float(x), float(y)] for x, y in table_info["quad"]] if table_info else None
        ),
        "total_ball_detections": len(ball_points),
        "ball_detection_rate": ball_detection_rate,
        "rallies": rallies,
        "rally_summary": {
            "total_rallies": len(rallies),
            "average_strokes": round(
                float(np.mean([r["stroke_count"] for r in rallies])), 1
            )
            if rallies
            else 0.0,
            **length_buckets,
        },
        "placement": placement,
        "ball_speed": speeds,
        "bounces": bounces[:100],
        "scoring_events": scoring_events,
        "scoring_summary": scoring_summary,
        "player_stats": player_stats,
        "key_moments": {
            "longest_rally": longest,
            "fastest_frame_speed_ms": speeds.get("max_speed_ms"),
        },
    }


def extract_video_fallback_scale(video_path: str) -> Optional[float]:
    """Échelle approximative m/px via la table (repli quand l'homographie est absente)."""
    try:
        detector = TableDetector()
        cap = cv2.VideoCapture(video_path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        if total <= 0:
            return None
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total / 2))
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return None
        quad = detector.detect_quad(frame)
        if quad is None:
            return None
        h, w = frame.shape[:2]
        return TableDetector.meters_per_pixel(quad, (h, w))
    except Exception:
        return None
