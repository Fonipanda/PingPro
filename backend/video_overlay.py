"""
Overlays vidéo pour PingPro : placement des coups et squelette de pose incrustés
dans la compilation auto-edit.

Timeline : la compilation auto-edit est construite par découpe/ré-assemblage des
échanges détectés. Les fonctions `build_segments` / `map_time_to_output`
maintiennent la correspondance temps original -> temps compilation, ce qui
permet de placer précisément les rebonds et les poses analysées sur la vidéo
finale.
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Palette BGR par type de coup estimé — dérivée exactement de la palette
# hexadécimale du frontend (App.js colorMap) pour une légende cohérente :
# topspin_coup_droit #f59e0b | topspin_revers #3b82f6 | coup_droit #eab308
# revers #22c55e | inconnu #e5e7eb
STROKE_COLORS_BGR: Dict[str, Tuple[int, int, int]] = {
    "topspin_coup_droit": (11, 158, 245),   # orange  #f59e0b
    "topspin_revers": (246, 130, 59),       # bleu    #3b82f6
    "coup_droit": (8, 179, 234),            # jaune   #eab308
    "revers": (94, 197, 34),                # vert    #22c55e
    "inconnu": (235, 231, 229),             # blanc   #e5e7eb
}

# Connexions du squelette MediaPipe Pose (indices de landmarks)
POSE_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (24, 26), (26, 28),
    (27, 29), (29, 31), (31, 27), (28, 30), (30, 32), (32, 28),
    (9, 10), (0, 11), (0, 12),
]


def get_ffmpeg_path() -> Optional[str]:
    """Chemin ffmpeg : PATH système, sinon binaire du paquet imageio-ffmpeg."""
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def build_segments(
    rallies: List[Dict[str, Any]],
    margin_before: float = 0.5,
    margin_after: float = 1.0,
    max_rallies: int = 40,
    min_duration: float = 1.0,
) -> List[Dict[str, float]]:
    """Découpe des échanges -> segments avec offset de sortie cumulé."""
    segments: List[Dict[str, float]] = []
    out_cursor = 0.0
    prev_end = -1.0
    for rally in rallies[:max_rallies]:
        raw_start = float(rally["start_time"]) - margin_before
        raw_end = float(rally["end_time"]) + margin_after
        # pas de chevauchement avec le segment précédent
        start = max(0.0, raw_start, prev_end + 0.05)
        end = max(start + min_duration, raw_end)
        duration = end - start
        if duration <= 0:
            continue
        segments.append(
            {
                "orig_start": start,
                "orig_end": end,
                "out_start": out_cursor,
                "out_dur": duration,
            }
        )
        out_cursor += duration
        prev_end = end
    return segments


def map_time_to_output(t: float, segments: List[Dict[str, float]]) -> Optional[float]:
    """Temps vidéo original -> temps dans la compilation (None si hors segments)."""
    for s in segments:
        if s["orig_start"] - 0.01 <= t <= s["orig_end"] + 0.01:
            return s["out_start"] + (t - s["orig_start"])
    return None


def build_auto_edit(
    video_path: str,
    rallies: List[Dict[str, Any]],
    out_dir: Path,
    ffmpeg_path: str,
) -> Tuple[Optional[str], List[Dict[str, float]]]:
    """
    Montage auto précis : trim + concat ré-encodés (h264, lisible dans le
    navigateur). Retourne (chemin ou None, segments correspondants).
    """
    segments = build_segments(rallies)
    if not segments:
        return None, []

    filters = []
    labels = []
    for i, s in enumerate(segments):
        filters.append(
            f"[0:v]trim=start={s['orig_start']:.3f}:end={s['orig_end']:.3f},"
            f"setpts=PTS-STARTPTS[v{i}]"
        )
        labels.append(f"[v{i}]")
    filter_complex = (
        ";".join(filters) + f";{''.join(labels)}concat=n={len(segments)}:v=1:a=0[out]"
    )

    output_path = out_dir / "auto_edit.mp4"
    try:
        subprocess.run(
            [
                ffmpeg_path, "-y",
                "-i", str(video_path),
                "-filter_complex", filter_complex,
                "-map", "[out]",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-an",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=900,
        )
        if output_path.exists():
            return str(output_path), segments
    except Exception as e:
        logger.error(f"Auto-edit build failed: {e}")
    return None, []


def build_best_rallies_compilation(
    video_path: str,
    rallies: List[Dict[str, Any]],
    out_dir: Path,
    ffmpeg_path: str,
    top_n: int = 3,
) -> Optional[str]:
    """Fallback : concatène les N échanges les plus longs (ou les plus rapides)."""
    if not rallies:
        return None
    sorted_rallies = sorted(
        rallies,
        key=lambda r: (r.get("stroke_count", 0), r.get("duration", 0)),
        reverse=True,
    )[:top_n]
    segments = build_segments(sorted_rallies, margin_before=0.3, margin_after=0.8)
    if not segments:
        return None
    output_path = out_dir / "best_rallies.mp4"
    filters = []
    labels = []
    for i, s in enumerate(segments):
        filters.append(
            f"[0:v]trim=start={s['orig_start']:.3f}:end={s['orig_end']:.3f},"
            f"setpts=PTS-STARTPTS[v{i}]"
        )
        labels.append(f"[v{i}]")
    filter_complex = (
        ";".join(filters) + f";{''.join(labels)}concat=n={len(segments)}:v=1:a=0[out]"
    )
    try:
        subprocess.run(
            [
                ffmpeg_path, "-y",
                "-i", str(video_path),
                "-filter_complex", filter_complex,
                "-map", "[out]",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-an",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=900,
        )
        return str(output_path) if output_path.exists() else None
    except Exception as e:
        logger.error(f"Best-rallies compilation failed: {e}")
        return None


def _reproject_point(table_x: float, table_y: float, H_inv: np.ndarray) -> Optional[Tuple[int, int]]:
    try:
        pt = cv2.perspectiveTransform(
            np.array([[[float(table_x), float(table_y)]]], dtype=np.float32), H_inv
        )
        return int(round(float(pt[0, 0, 0]))), int(round(float(pt[0, 0, 1])))
    except Exception:
        return None


def generate_placement_overlay(
    source_path: str,
    out_path: str,
    bounces: List[Dict[str, Any]],
    segments: List[Dict[str, float]],
    H_inv: np.ndarray,
    ffmpeg_path: str,
) -> Optional[str]:
    """Incruste chaque rebond détecté (cercle coloré + légende) sur la vidéo."""
    cap = cv2.VideoCapture(source_path)
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    events = []
    for b in bounces:
        t = float(b.get("timestamp", 0.0))
        t_out = map_time_to_output(t, segments) if segments else t
        if t_out is None:
            continue
        pt = _reproject_point(b.get("table_x", 0.0), b.get("table_y", 0.0), H_inv)
        if pt is None:
            continue
        events.append((t_out, pt[0], pt[1], b.get("stroke_side", "inconnu"), b.get("speed_ms")))

    if not events:
        cap.release()
        return None

    tmp_path = out_path + ".tmp.mp4"
    writer = cv2.VideoWriter(tmp_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        t = frame_idx / fps
        for t_bounce, x, y, side, speed in events:
            age = t - t_bounce
            if 0 <= age <= 0.9:
                color = STROKE_COLORS_BGR.get(side, STROKE_COLORS_BGR["inconnu"])
                cv2.circle(frame, (x, y), 8, color, -1)
                cv2.circle(frame, (x, y), 8 + int(12 * age), color, 2)
                label = side.replace("_", " ")
                if speed:
                    label += f" {speed} m/s"
                cv2.putText(
                    frame, label, (min(x + 12, width - 160), max(20, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA,
                )
        writer.write(frame)
        frame_idx += 1
    cap.release()
    writer.release()

    try:
        subprocess.run(
            [
                ffmpeg_path, "-y", "-i", tmp_path,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-an", out_path,
            ],
            capture_output=True, text=True, check=True, timeout=900,
        )
    except Exception as e:
        logger.error(f"Placement overlay encode failed: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return out_path if os.path.exists(out_path) else None


def generate_pose_overlay(
    source_path: str,
    out_path: str,
    pose_frames: List[Dict[str, Any]],
    segments: List[Dict[str, float]],
    ffmpeg_path: str,
) -> Optional[str]:
    """Incruste le squelette du joueur (landmarks image) sur la vidéo compilée."""
    cap = cv2.VideoCapture(source_path)
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    mapped: List[Tuple[float, List[Dict[str, float]]]] = []
    for f in pose_frames:
        t_out = (
            map_time_to_output(float(f.get("timestamp", 0.0)), segments)
            if segments
            else float(f.get("timestamp", 0.0))
        )
        poses = f.get("poses") or []
        if t_out is None or not poses:
            continue
        mapped.append((t_out, poses[0]))
    mapped.sort(key=lambda m: m[0])
    if not mapped:
        cap.release()
        return None

    tmp_path = out_path + ".tmp.mp4"
    writer = cv2.VideoWriter(tmp_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    frame_idx = 0
    cursor = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        t = frame_idx / fps
        # avancer le curseur vers la pose analysée la plus proche (fenêtre 0.25 s)
        while cursor + 1 < len(mapped) and mapped[cursor + 1][0] <= t:
            cursor += 1
        best = cursor
        if cursor + 1 < len(mapped) and abs(mapped[cursor + 1][0] - t) < abs(mapped[cursor][0] - t):
            best = cursor + 1
        if abs(mapped[best][0] - t) <= 0.25:
            landmarks = mapped[best][1]
            pts = []
            for lm in landmarks:
                pts.append((int(lm["x"] * width), int(lm["y"] * height)))
            for a, b in POSE_CONNECTIONS:
                if a < len(pts) and b < len(pts):
                    cv2.line(frame, pts[a], pts[b], (80, 220, 80), 2, cv2.LINE_AA)
            for p in pts:
                cv2.circle(frame, p, 3, (255, 255, 255), -1)
        writer.write(frame)
        frame_idx += 1
    cap.release()
    writer.release()

    try:
        subprocess.run(
            [
                ffmpeg_path, "-y", "-i", tmp_path,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-an", out_path,
            ],
            capture_output=True, text=True, check=True, timeout=900,
        )
    except Exception as e:
        logger.error(f"Pose overlay encode failed: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    return out_path if os.path.exists(out_path) else None
