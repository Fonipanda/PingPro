"""
PingPro MVP Backend
FastAPI server for table tennis video analysis.
No external DB or LLM required: everything runs in-memory and TTNet heuristics
provide the analysis. Video compilations are generated when FFmpeg is available.
"""

import asyncio
import logging
import os
import json
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import cv2
import numpy as np
from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

from ttnet_analysis import analyze_video_with_ttn
from pose_analysis import analyze_video_pose
from pose_reference import compare_with_reference, suggest_improvements
from table_detector import TableDetector
from match_analysis import build_match_analysis, extract_video_fallback_scale
from players_tracker import analyze_players
from video_overlay import (
    get_ffmpeg_path,
    build_auto_edit,
    build_best_rallies_compilation,
    generate_placement_overlay,
    generate_pose_overlay,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# Configuration -----------------------------------------------------------------
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

COMPILATIONS_DIR = ROOT_DIR / "compilations"
COMPILATIONS_DIR.mkdir(exist_ok=True)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]

# In-memory stores (use external DB by wiring here if needed)
analysis_status: Dict[str, "AnalysisStatus"] = {}
analysis_results: Dict[str, "AnalysisResult"] = {}

# Logging -----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Pydantic models ---------------------------------------------------------------
class AnalysisRequest(BaseModel):
    player_side: str = "droite"
    skill_level: str = "intermediaire"
    focus_areas: List[str] = ["technique_coups", "positionnement", "timing"]
    # Calibrage manuel de la table : 4 coins [[x, y], ...] en coordonnées
    # normalisées (0-1) de la frame. Optionnel — l'auto-détection reste le défaut.
    table_quad: Optional[List[List[float]]] = None


class AnalysisStatus(BaseModel):
    analysis_id: str
    status: str  # queued | processing | completed | failed
    progress: float
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    current_step: Optional[str] = None


class VideoInfo(BaseModel):
    duration_seconds: float
    frame_count: int
    fps: float
    resolution: str


class TechnicalAnalysis(BaseModel):
    stroke_analysis: Dict[str, Any]
    positioning_analysis: Dict[str, Any]
    timing_analysis: Dict[str, Any]
    movement_analysis: Dict[str, Any]
    ttnet_analysis: Optional[Dict[str, Any]] = None
    pose_analysis: Optional[Dict[str, Any]] = None
    match_analysis: Optional[Dict[str, Any]] = None


class PerformanceMetrics(BaseModel):
    technical_consistency: float
    positioning_score: float
    timing_accuracy: float
    overall_score: float
    improvement_areas: List[str]
    posture_score: Optional[float] = None
    kinetic_chain_quality: Optional[float] = None
    ball_tracking_quality: Optional[str] = None
    rally_analysis: Optional[Dict[str, Any]] = None
    event_detection: Optional[Dict[str, Any]] = None


class AnalysisResult(BaseModel):
    analysis_id: str
    video_info: VideoInfo
    technical_analysis: TechnicalAnalysis
    performance_metrics: PerformanceMetrics
    recommendations: List[str]
    highlights_timestamps: List[float]
    confidence_score: float
    video_compilations: Optional[Dict[str, Optional[str]]] = None
    lexicon_analysis: Optional[Dict[str, Any]] = None
    table_tennis_scoring: Optional[Dict[str, Any]] = None
    pose_reference_comparison: Optional[Dict[str, Any]] = None
    pose_report: Optional[str] = None
    overlay_frames: Optional[List[str]] = None
    match_analysis: Optional[Dict[str, Any]] = None
    players_analysis: Optional[Dict[str, Any]] = None
    training_plan: Optional[Dict[str, Any]] = None


# FastAPI app -------------------------------------------------------------------
app = FastAPI(
    title="PingPro - Analyse IA Tennis de Table",
    description="MVP d'analyse vidéo de tennis de table par IA",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers -----------------------------------------------------------------------
def _has_ffmpeg() -> bool:
    return get_ffmpeg_path() is not None


def _get_video_info(video_path: str) -> VideoInfo:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError("Cannot open video file")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / fps if fps > 0 else 0.0
    cap.release()

    return VideoInfo(
        duration_seconds=duration,
        frame_count=frame_count,
        fps=fps,
        resolution=f"{width}x{height}",
    )


def _build_fallback_analysis(ttnet_results: Dict[str, Any], params: AnalysisRequest) -> Dict[str, Any]:
    stats = ttnet_results.get("match_statistics", {})
    insights = ttnet_results.get("technical_insights", {})
    events = stats.get("event_summary", {})
    ball_detection_rate = stats.get("ball_detection_rate", 0)

    technique_quality = "8" if ball_detection_rate > 0.7 else "6" if ball_detection_rate > 0.4 else "4"

    return {
        "stroke_analysis": {
            "identified_strokes": ["service", "coup droit", "revers"],
            "technique_quality": technique_quality,
            "strengths": ["Analyse basée sur la détection automatique de la balle"],
            "weaknesses": [
                "Analyse nécessite une vidéo de meilleure qualité"
                if ball_detection_rate < 0.5
                else "Technique à affiner avec un coach"
            ],
            "stroke_consistency": f"Détection: {ball_detection_rate:.1%}",
            "power_vs_control": "Équilibré selon l'analyse automatique",
        },
        "positioning_analysis": {
            "court_position": "Position analysée par segmentation automatique",
            "movement_quality": "Mouvement suivi par vision artificielle",
            "balance_score": "7",
            "recovery_speed": "Analysé automatiquement",
            "tactical_positioning": insights.get("game_flow_assessment", "Analyse disponible"),
        },
        "timing_analysis": {
            "preparation_quality": "Analysé par détection d'événements",
            "impact_timing": f"{events.get('ball_bounce', 0)} impacts détectés",
            "rhythm_consistency": f"Basé sur {events.get('serve', 0)} services",
            "reaction_time": "Calculé automatiquement",
        },
        "errors_identified": insights.get("technical_recommendations", ["Analyse complète effectuée"])[:3],
        "improvement_priorities": [
            "Améliorer la régularité selon l'analyse automatique",
            "Optimiser le positionnement détecté par IA",
            "Travailler selon les recommandations techniques",
        ],
    }


def _build_performance_metrics(
    ttnet_results: Dict[str, Any],
    analysis_data: Dict[str, Any],
    pose_results: Optional[Dict[str, Any]] = None,
    pose_comparison: Optional[Dict[str, Any]] = None,
) -> PerformanceMetrics:
    stats = ttnet_results.get("match_statistics", {})
    insights = ttnet_results.get("technical_insights", {})
    skill = insights.get("skill_assessment", {})

    ball_detection_rate = stats.get("ball_detection_rate", 0)
    technical_consistency = skill.get("technical_consistency", 70)
    tactical_awareness = skill.get("tactical_awareness", 65)
    shot_variety = skill.get("shot_variety", 60)

    # Pose-based metrics
    posture_score = None
    kinetic_chain_quality = None
    if pose_results and "error" not in pose_results and pose_results.get("contact_angles"):
        angles = pose_results.get("contact_angles", {})
        elbow = angles.get("elbow", 120)
        knee = angles.get("knee", 130)
        posture_score = 100 - abs(elbow - 110) * 0.5 - abs(knee - 140) * 0.3
        posture_score = round(max(0, min(100, posture_score)), 1)

        kinetic = pose_results.get("kinetic_chain", {})
        kinetic_chain_quality = kinetic.get("quality_score")

    # Overall score includes pose if available
    pose_weight = 0.15 if posture_score is not None else 0.0
    overall = (
        technical_consistency * (0.4 - pose_weight / 2)
        + tactical_awareness * (0.3 - pose_weight / 2)
        + shot_variety * 0.2
        + ball_detection_rate * 100 * 0.1
    )
    if pose_weight > 0:
        overall += (posture_score or 70) * pose_weight / 2
        overall += (kinetic_chain_quality or 70) * pose_weight / 2

    improvement_areas = []
    if technical_consistency < 70:
        improvement_areas.append("Régularité technique")
    if tactical_awareness < 65:
        improvement_areas.append("Lecture du jeu")
    if shot_variety < 60:
        improvement_areas.append("Variété des coups")
    if ball_detection_rate < 0.5:
        improvement_areas.append("Qualité de la vidéo")
    if pose_comparison and pose_comparison.get("similarity_score", 100) < 60:
        improvement_areas.append("Technique de frappe par rapport au modèle")
    if posture_score is not None and posture_score < 60:
        improvement_areas.append("Posture au contact")
    if not improvement_areas:
        improvement_areas.append("Perfectionnement des coups de finition")

    events = stats.get("event_summary", {})
    trajectory = stats.get("ball_trajectory_analysis", {})

    return PerformanceMetrics(
        technical_consistency=round(technical_consistency, 1),
        positioning_score=round(tactical_awareness, 1),
        timing_accuracy=round(shot_variety, 1),
        overall_score=round(min(100, max(0, overall)), 1),
        improvement_areas=improvement_areas[:4],
        posture_score=posture_score,
        kinetic_chain_quality=kinetic_chain_quality,
        ball_tracking_quality=insights.get("ball_tracking_quality", "Good"),
        rally_analysis={
            "average_rally_length": events.get("ball_bounce", 0)
            / max(1, events.get("serve", 1)),
            "total_bounces": events.get("ball_bounce", 0),
            "total_serves": events.get("serve", 0),
            "max_ball_speed": round(trajectory.get("max_speed_pixels_per_frame", 0), 1),
        },
        event_detection=events,
    )


def _create_video_segment(input_path: str, output_path: str, start: float, duration: float) -> bool:
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        return False
    try:
        subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-i",
                input_path,
                "-ss",
                str(start),
                "-t",
                str(duration),
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-b:v",
                "1M",
                "-b:a",
                "128k",
                output_path,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=300,
        )
        return os.path.exists(output_path)
    except Exception as e:
        logger.error(f"Failed to create video segment: {e}")
        return False


# Correspondance temps original -> temps compilation auto-edit, par analyse
_AUTO_EDIT_SEGMENTS: Dict[str, List[Dict[str, float]]] = {}


def _compile_auto_edit(
    video_path: str, out_dir: Path, rallies: List[Dict[str, Any]], analysis_id: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Montage auto : concatène les échanges réellement détectés (sans temps morts).

    Utilise un trim+concat ré-encodé (précis) et mémorise la correspondance
    temporelle pour les overlays (placement, pose). Si le montage complet
    échoue, retombe sur une compilation des meilleurs échanges.
    """
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path or not rallies:
        return None, None
    output_path, segments = build_auto_edit(video_path, rallies, out_dir, ffmpeg_path)
    if output_path and segments:
        _AUTO_EDIT_SEGMENTS[analysis_id] = segments
        return output_path, output_path
    # Fallback : meilleurs échanges (même segments, pas de correspondance overlay)
    fallback = build_best_rallies_compilation(video_path, rallies, out_dir, ffmpeg_path)
    return fallback, fallback


def _compile_videos(
    video_path: str,
    analysis_id: str,
    detected_rallies: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Optional[str]]]:
    if not _has_ffmpeg():
        logger.info("FFmpeg not available, skipping video compilations")
        return None

    try:
        info = _get_video_info(video_path)
        duration = info.duration_seconds
        if duration <= 0:
            return None

        out_dir = COMPILATIONS_DIR / analysis_id
        out_dir.mkdir(parents=True, exist_ok=True)

        compilations: Dict[str, Optional[str]] = {}

        # Montage auto prioritaire : échanges réellement détectés par le tracker
        auto_edit, best_rallies = _compile_auto_edit(
            video_path, out_dir, detected_rallies, analysis_id
        )
        if auto_edit:
            compilations["auto_edit"] = auto_edit
        if best_rallies:
            compilations["best_rallies"] = best_rallies

        # Segments génériques si la détection d'échange a échoué
        if not auto_edit and not best_rallies:
            segments = [
                ("match_compilation", 0, min(60, duration)),
                ("strengths", min(30, duration), min(60, duration)),
                ("weaknesses", min(60, duration), min(60, duration - min(60, duration))),
                ("best_rallies", max(0, duration - 60), min(60, duration)),
            ]

            for name, start, seg_duration in segments:
                if seg_duration <= 0:
                    continue
                output_path = str(out_dir / f"{name}.mp4")
                if _create_video_segment(video_path, output_path, start, seg_duration):
                    compilations[name] = output_path

        return compilations or None
    except Exception as e:
        logger.error(f"Video compilation failed: {e}")
        return None


def _apply_table_tennis_scoring(
    ttnet_results: Dict[str, Any],
    match_analysis: Optional[Dict[str, Any]] = None,
    player_side: str = "droite",
) -> Dict[str, Any]:
    """
    Score reconstruit à partir des échanges détectés.
    - Si les gagnants d'échange sont attribués (rebond final détecté par camp),
      la progression est réelle point par point (toujours marquée "estimation"
      car la détection reste imparfaite).
    - Sinon, repli : total de points = nombre d'échanges détectés, réparti par
      taux de détection (estimation grossière, clairement badgée).
    """
    stats = ttnet_results.get("match_statistics", {})
    events = stats.get("event_summary", {})
    total_bounces = events.get("ball_bounce", 15)
    serves = events.get("serve", 6)
    detection_rate = stats.get("ball_detection_rate", 0.65)

    rally_summary = (match_analysis or {}).get("rally_summary") or {}
    detected_rallies = int(rally_summary.get("total_rallies", 0))
    scoring_events = (match_analysis or {}).get("scoring_events") or []
    user_side = "droite" if player_side == "droite" else "gauche"

    progression = []
    p1 = p2 = 0
    attributed = 0
    if scoring_events:
        for i, ev in enumerate(scoring_events):
            if ev.get("winner_side") == user_side:
                p1 += 1
                attributed += 1
            elif ev.get("winner_side"):
                p2 += 1
                attributed += 1
            progression.append({"point": i + 1, "player1": p1, "player2": p2})
    else:
        if detected_rallies > 0:
            total_points = min(25, max(1, detected_rallies))
        else:
            total_points = min(25, max(11, total_bounces // 2))
        p1 = int(round(total_points * detection_rate))
        p2 = total_points - p1
        for i in range(1, total_points + 1):
            ratio = i / float(total_points)
            progression.append(
                {
                    "point": i,
                    "player1": int(round(p1 * ratio)),
                    "player2": int(round(p2 * ratio)),
                }
            )

    return {
        "estimated": True,
        "user_side": user_side,
        "attribution_quality": "par_échange" if scoring_events else "grossière",
        "points_attributed": attributed,
        "points_total_detected": len(scoring_events) if scoring_events else 0,
        "final_score": {
            "player1": p1,
            "player2": p2,
            "winner": "player1" if p1 > p2 else "player2",
        },
        "sets": {
            "player1_sets": 1 if p1 > p2 else 0,
            "player2_sets": 1 if p2 > p1 else 0,
            "total_sets": 1,
            "match_format": "Best of 3",
        },
        "score_progression": progression,
        "rules_applied": {
            "winning_score": 11,
            "minimum_lead": 2,
            "deuce_rule": "Continue until 2-point lead",
            "match_format": "First to 2 sets (best of 3)",
        },
        "match_statistics": {
            "total_points": len(progression),
            "detected_rallies": detected_rallies,
            "longest_rally": rally_summary.get("average_strokes")
            and int(round(float(rally_summary.get("average_strokes"))))
            or max(3, total_bounces // max(1, serves)),
            "aces_served": max(1, serves // 3),
            "unforced_errors": max(2, events.get("net_hit", 2)),
        },
    }


def _infer_stroke_type(focus_areas: List[str]) -> str:
    """Déduit le type de coup à comparer avec le modèle de référence."""
    focus = ",".join(focus_areas).lower()
    if "revers" in focus or "backhand" in focus:
        return "backhand"
    if "service" in focus or "serve" in focus:
        return "serve"
    return "forehand_topspin"


def _generate_pose_report(
    pose_results: Dict[str, Any],
    pose_comparison: Dict[str, Any],
    performance_metrics: PerformanceMetrics,
    match_analysis: Optional[Dict[str, Any]] = None,
) -> str:
    """Génère un rapport textuel sur la pose. Utilise un LLM si configuré, sinon fallback."""
    static_report = _build_static_pose_report(pose_results, pose_comparison, performance_metrics, match_analysis)

    llm_report = _generate_llm_report(pose_results, pose_comparison, performance_metrics, match_analysis)
    if llm_report:
        return llm_report
    return static_report


def _generate_llm_report(
    pose_results: Dict[str, Any],
    pose_comparison: Dict[str, Any],
    performance_metrics: PerformanceMetrics,
    match_analysis: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Rapport Coach IA via OpenAI. Retourne None si la clé/le package sont absents."""
    if not OPENAI_API_KEY:
        return None
    try:
        import openai
    except ImportError:
        return None

    def _call() -> Optional[str]:
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            prompt = (
                "Tu es un coach de tennis de table. Rédige en français un rapport technique "
                "structuré (markdown) à partir des données d'analyse suivantes.\n\n"
                "## Métriques de performance\n"
                f"{performance_metrics.model_dump_json(indent=2)}\n\n"
            )
            if "error" not in pose_results:
                prompt += (
                    "## Analyse de pose\n"
                    f"Angles au contact : {pose_results.get('contact_angles', {})}\n"
                    f"Chaîne cinétique : {pose_results.get('kinetic_chain', {})}\n"
                    f"Phases du geste : {pose_results.get('phases', {})}\n\n"
                    "## Comparaison au modèle de référence\n"
                    f"{pose_comparison}\n\n"
                )
            if match_analysis:
                ma = dict(match_analysis)
                # Alléger le prompt : retirer les listes volumineuses
                ma.pop("bounces", None)
                ma["rallies"] = ma.get("rally_summary", {})
                prompt += "## Analyse de match\n" + str(ma) + "\n\n"
            prompt += (
                "Consignes : identifie 2-3 forces et 2-3 axes d'amélioration concrets, "
                "cite les chiffres pertinents (angles, vitesses, longueurs d'échanges), "
                "reste encourageant et factuel. Ne dépasse pas 400 mots."
            )
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Tu es un coach expert de tennis de table."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=900,
                temperature=0.6,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Rapport LLM impossible, fallback statique: {e}")
            return None

    return _call()


def _build_static_pose_report(
    pose_results: Dict[str, Any],
    pose_comparison: Dict[str, Any],
    performance_metrics: PerformanceMetrics,
    match_analysis: Optional[Dict[str, Any]] = None,
) -> str:
    """Rapport statique (fallback sans LLM)."""
    angles = pose_results.get("contact_angles", {}) if "error" not in pose_results else {}
    kinetic = pose_results.get("kinetic_chain", {}) if "error" not in pose_results else {}
    phases = pose_results.get("phases", {}) if "error" not in pose_results else {}

    # Fallback report
    lines = [
        "## Rapport technique - Analyse de la pose",
        "",
        f"**Score de posture au contact** : {performance_metrics.posture_score or 'N/A'}/100",
        f"**Qualité de la chaîne cinétique** : {performance_metrics.kinetic_chain_quality or 'N/A'}/100",
        f"**Similarité avec le modèle de référence** : {pose_comparison.get('similarity_score', 'N/A')}/100",
        "",
        "### Angles articulaires au contact",
    ]
    for joint, value in angles.items():
        lines.append(f"- **{joint}** : {value:.1f}°")

    lines.extend(
        [
            "",
            "### Chaîne cinétique",
            f"- Ordre séquentiel idéal (bassin → épaules → avant-bras) : {'oui' if kinetic.get('sequential_order_ok') else 'non'}",
        ]
    )
    for segment, data in kinetic.items():
        if isinstance(data, dict):
            lines.append(f"- **{segment}** : vitesse max {data.get('max_speed', 'N/A')} au temps {data.get('timestamp', 'N/A')}s")

    lines.extend(
        [
            "",
            "### Phases du geste",
            f"- Début de l'armé : {phases.get('backswing', {}).get('start_timestamp', 'N/A')}s",
            f"- Contact estimé : {phases.get('contact', {}).get('timestamp', 'N/A')}s",
            f"- Fin de l'accompagnement : {phases.get('follow_through', {}).get('end_timestamp', 'N/A')}s",
        ]
    )

    if match_analysis and match_analysis.get("available"):
        rally_summary = match_analysis.get("rally_summary", {})
        speeds = match_analysis.get("ball_speed", {})
        placement = match_analysis.get("placement", {})
        lines.extend(
            [
                "",
                "### Analyse de match",
                f"- Échanges détectés : {rally_summary.get('total_rallies', 0)} "
                f"(moyenne {rally_summary.get('average_strokes', 0)} coups)",
            ]
        )
        if speeds.get("max_speed_ms") is not None:
            lines.append(
                f"- Vitesse max de balle : {speeds.get('max_speed_ms')} m/s "
                f"(moyenne {speeds.get('average_speed_ms')} m/s)"
            )
        if placement.get("available"):
            lines.append(f"- Zones d'impact principales : {placement.get('zones', {})}")

    lines.extend(["", "### Recommandations"])
    for suggestion in suggest_improvements(pose_results, pose_comparison):
        lines.append(f"- {suggestion}")

    return "\n".join(lines)


class PlanRequest(BaseModel):
    goal: str = "progression_generale"
    priority: str = "technique_coups"
    weekly_frequency: int = 3
    session_duration_min: int = 60
    difficulty: str = "intermediaire"
    equipment: List[str] = ["table", "raquette", "balles"]
    injuries: Optional[str] = None


def _generate_static_training_plan(
    params: PlanRequest,
    match_analysis: Optional[Dict[str, Any]] = None,
    pose_results: Optional[Dict[str, Any]] = None,
    performance_metrics: Optional[PerformanceMetrics] = None,
) -> Dict[str, Any]:
    """Plan d'entraînement structuré sans LLM, basé sur les données d'analyse."""
    rally_summary = (match_analysis or {}).get("rally_summary", {})
    improvement_areas = (performance_metrics.improvement_areas if performance_metrics else []) or []

    focus_blocks = {
        "technique_coups": "Régularité coup droit / revers (topspin 15 min, poussette 10 min)",
        "service_remise": "Services variés + remises courtes (20 min)",
        "deplacement": "Jeu de jambes : déplacements latéraux et récupération (15 min)",
        "physique": "Gainage et explosivité (15 min)",
    }
    priority_block = focus_blocks.get(params.priority, focus_blocks["technique_coups"])
    if rally_summary.get("average_strokes", 0) and rally_summary["average_strokes"] < 5:
        priority_block += " — beaucoup d'échanges courts : travailler la remise et le contrôle"

    sessions = []
    for i in range(max(1, min(7, params.weekly_frequency))):
        sessions.append(
            {
                "session": i + 1,
                "duree_min": params.session_duration_min,
                "echauffement": "10 min : footwork + balles régulières",
                "bloc_prioritaire": priority_block,
                "bloc_secondaire": improvement_areas[0] if improvement_areas else "Points libres en match",
                "retour_calme": "5 min : services coupés + étirements",
            }
        )

    return {
        "source": "statique",
        "goal": params.goal,
        "difficulty": params.difficulty,
        "weekly_frequency": params.weekly_frequency,
        "improvement_areas_targeted": improvement_areas[:3],
        "sessions": sessions,
        "precautions": params.injuries or None,
    }


def _generate_llm_training_plan(
    params: PlanRequest,
    match_analysis: Optional[Dict[str, Any]] = None,
    pose_results: Optional[Dict[str, Any]] = None,
    performance_metrics: Optional[PerformanceMetrics] = None,
) -> Optional[Dict[str, Any]]:
    """Plan d'entraînement via OpenAI. Retourne None si clé/package absents ou erreur."""
    if not OPENAI_API_KEY:
        return None
    try:
        import openai
    except ImportError:
        return None

    def _call() -> Optional[Dict[str, Any]]:
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            context = (
                f"Profil : objectif={params.goal}, priorité={params.priority}, "
                f"fréquence={params.weekly_frequency}/semaine, durée séance={params.session_duration_min} min, "
                f"niveau={params.difficulty}, matériel={params.equipment}, "
                f"blessures={params.injuries or 'aucune'}.\n"
            )
            if match_analysis:
                ma = dict(match_analysis)
                ma.pop("bounces", None)
                ma["rallies"] = ma.get("rally_summary", {})
                context += f"Données d'analyse de match : {ma}\n"
            if performance_metrics:
                context += (
                    f"Métriques : {performance_metrics.model_dump_json(exclude_none=True)}\n"
                )
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Tu es un entraîneur de tennis de table. Réponds UNIQUEMENT en JSON valide : "
                            '{"source":"llm","summary":str,"weekly_focus":[str],"sessions":[{"session":int,'
                            '"duree_min":int,"echauffement":str,"bloc_prioritaire":str,'
                            '"bloc_secondaire":str,"retour_calme":str}],"conseils":[str]}'
                        ),
                    },
                    {"role": "user", "content": context + "Génère le plan d'entraînement hebdomadaire."},
                ],
                response_format={"type": "json_object"},
                max_tokens=1200,
                temperature=0.5,
            )
            import json
            plan = json.loads(response.choices[0].message.content)
            plan.setdefault("goal", params.goal)
            return plan
        except Exception as e:
            logger.warning(f"Plan LLM impossible, fallback statique: {e}")
            return None

    return _call()


def _generate_training_plan(
    params: PlanRequest,
    match_analysis: Optional[Dict[str, Any]] = None,
    pose_results: Optional[Dict[str, Any]] = None,
    performance_metrics: Optional[PerformanceMetrics] = None,
) -> Dict[str, Any]:
    llm_plan = _generate_llm_training_plan(params, match_analysis, pose_results, performance_metrics)
    if llm_plan:
        return llm_plan
    return _generate_static_training_plan(params, match_analysis, pose_results, performance_metrics)


def _generate_detailed_analysis_texts(
    performance_metrics: PerformanceMetrics,
    match_analysis: Optional[Dict[str, Any]],
    pose_results: Optional[Dict[str, Any]],
) -> Dict[str, List[str]]:
    """
    Produit des forces / faiblesses / recommandations DÉTAILLÉES et argumentées
    (constat chiffré + cause probable + piste de travail). LLM si configuré,
    sinon enrichissement statique à partir des données réelles.
    """
    llm = _generate_llm_analysis_texts(performance_metrics, match_analysis, pose_results)
    if llm:
        return llm
    return _generate_static_analysis_texts(performance_metrics, match_analysis, pose_results)


def _generate_static_analysis_texts(
    performance_metrics: PerformanceMetrics,
    match_analysis: Optional[Dict[str, Any]],
    pose_results: Optional[Dict[str, Any]],
) -> Dict[str, List[str]]:
    rally_summary = (match_analysis or {}).get("rally_summary") or {}
    speeds = (match_analysis or {}).get("ball_speed") or {}
    placement = (match_analysis or {}).get("placement") or {}
    avg_strokes = float(rally_summary.get("average_strokes", 0) or 0)
    total_rallies = int(rally_summary.get("total_rallies", 0) or 0)
    max_speed = speeds.get("max_speed_ms")
    avg_speed = speeds.get("average_speed_ms")
    tech = round(float(performance_metrics.technical_consistency or 0), 1)
    pos = round(float(performance_metrics.positioning_score or 0), 1)
    timing = round(float(performance_metrics.timing_accuracy or 0), 1)
    overall = round(float(performance_metrics.overall_score or 0), 1)

    strengths: List[str] = []
    if total_rallies > 0:
        strengths.append(
            f"Vous avez maintenu {total_rallies} échanges détectés avec une longueur moyenne de "
            f"{avg_strokes:.1f} coups. Cette régularité dans la durée du match montre une capacité "
            f"à construire les points plutôt qu'à chercher le coup gagnant immédiat — un socle "
            f"solide pour développer un jeu offensif par la suite."
        )
    if max_speed:
        strengths.append(
            f"Votre balle a atteint {max_speed} m/s en pointe (moyenne {avg_speed} m/s). "
            f"Cette différence entre pointe et moyenne indique que vous variez l'intensité des "
            f"frappes : exploitez ce potentiel en accélérant sur les balles hautes et mi-hautes, "
            f"où le rapport risque/rendement est le meilleur."
        )
    strengths.append(
        f"La consistance technique mesurée est de {tech}/100 pour un score global de {overall}/100. "
        f"Le différentiel entre ces deux indicateurs suggère que votre régularité gestuelle porte "
        f"vos résultats : continuer à travailler la qualité d'exécution (préparation, transfert du "
        f"poids) devrait débloquer le score global."
    )

    weaknesses: List[str] = []
    if placement.get("available"):
        zones = placement.get("zones", {})
        main_zone = max(zones.items(), key=lambda kv: kv[1]) if zones else None
        if main_zone:
            weaknesses.append(
                f"Vos impacts se concentrent sur la zone « {main_zone[0]} » ({main_zone[1]} impacts sur "
                f"{placement.get('total_balls_on_table', main_zone[1])}). Cette prévisibilité permet à "
                f"l'adversaire de se placer avant même votre frappe : travailler le changement de "
                f"rythme et la variation de longueur (courte/longe) rendra votre jeu beaucoup plus "
                f"difficile à lire."
            )
    if max_speed and avg_speed and max_speed > 0:
        ratio = avg_speed / max_speed
        if ratio < 0.55:
            weaknesses.append(
                f"La vitesse moyenne ({avg_speed} m/s) représente seulement {ratio:.0%} de votre pointe "
                f"({max_speed} m/s) : votre intensité de jeu est très inégale. Cela traduit souvent un "
                f"placement tardif ou une préparation trop longue entre les coups — un travail de "
                f"jambes et de récupération positionnelle (déplacements latéraux, retour au centre) "
                f"égaliserait votre niveau d'exécution d'un échange à l'autre."
            )
    if avg_strokes and avg_strokes < 5:
        weaknesses.append(
            f"Vos échanges durent en moyenne {avg_strokes:.1f} coups : la majorité des points se "
            f"joue dans les 3 premières frappes. Cela peut venir d'une prise de risque excessive "
            f"en début d'échange ou d'une remise trop friable. Renforcer la qualité de la remise "
            f"(poussette courte gênante plutôt que longue attaquerable) allongerait les échanges "
            f"et vous donnerait plus d'occasions d'attaquer en position favorable."
        )
    weaknesses.append(
        f"Axes mesurés les plus faibles : précision/variété {timing}/100 et positionnement "
        f"{pos}/100. Ce sont vos deux leviers de progression les plus directs : des exercices "
        f"ciblés (cibles posées sur la table pour la précision, jeux à thème limités au "
        f"placement) transformeront rapidement ces scores en points gagnés en match."
    )

    recommendations: List[str] = [
        "Séance à thème : 20 minutes de jeu en diagonale coup droit avec changement d'orientation "
        "imposé après 3 échanges, pour casser la prévisibilité du placement identifiée plus haut.",
        "Travail de remise : votre adversaire sert, vous devez renvoyer court (zone du filet) dans "
        "7 balles sur 10 ; cela allonge les échanges et réduit les attaques adverses en 3e balle.",
        "Exercice de vitesse moyenne : filmer à nouveau une séance après un travail de jambes et "
        "comparer la vitesse moyenne de balle — l'objectif est de rapprocher la moyenne de la pointe.",
        "Contrôle sous pression : jouer des points avec obligation de 5 coups minimum avant "
        "attaque, afin d'automatiser la construction du point observée dans les échanges longs.",
    ]
    return {"strengths": strengths, "weaknesses": weaknesses, "recommendations": recommendations}


def _generate_llm_analysis_texts(
    performance_metrics: PerformanceMetrics,
    match_analysis: Optional[Dict[str, Any]],
    pose_results: Optional[Dict[str, Any]],
) -> Optional[Dict[str, List[str]]]:
    """Forces/faiblesses/recommandations détaillées via OpenAI. None si clé absente ou erreur."""
    if not OPENAI_API_KEY:
        return None
    try:
        import openai
    except ImportError:
        return None

    def _call() -> Optional[Dict[str, List[str]]]:
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            context = f"Métriques de performance : {performance_metrics.model_dump_json(exclude_none=True)}\n"
            if match_analysis:
                ma = dict(match_analysis)
                ma.pop("bounces", None)
                ma["rallies"] = ma.get("rally_summary", {})
                context += f"Analyse de match : {ma}\n"
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Tu es un coach expert de tennis de table. Réponds UNIQUEMENT en JSON valide : "
                            '{"strengths":[str],"weaknesses":[str],"recommendations":[str]}. '
                            "Chaque élément doit être un paragraphe argumenté de 3 à 5 phrases : "
                            "un constat appuyé sur un chiffre fourni, la cause probable, puis une piste "
                            "de travail concrète. 3 éléments minimum par liste. Français."
                        ),
                    },
                    {"role": "user", "content": context},
                ],
                response_format={"type": "json_object"},
                max_tokens=1400,
                temperature=0.6,
            )
            import json

            data = json.loads(response.choices[0].message.content)
            result = {}
            for key in ("strengths", "weaknesses", "recommendations"):
                values = data.get(key, [])
                result[key] = [str(v) for v in values if v][:6]
            if not result["strengths"] or not result["weaknesses"]:
                return None
            return result
        except Exception as e:
            logger.warning(f"Analyse LLM détaillée impossible, fallback statique : {e}")
            return None

    return _call()


async def _process_video_analysis(analysis_id: str, video_path: str, params: AnalysisRequest):
    """Background task: run TTNet + Pose analysis and build the result."""
    try:
        analysis_status[analysis_id].status = "processing"
        analysis_status[analysis_id].progress = 5.0
        analysis_status[analysis_id].current_step = "Analyse TTNet en cours..."

        # 1. TTNet analysis
        ttnet_results = await asyncio.get_event_loop().run_in_executor(
            None, analyze_video_with_ttn, video_path
        )

        analysis_status[analysis_id].progress = 30.0
        analysis_status[analysis_id].current_step = "Traitement vidéo et détection des échanges..."

        # 1bis. Analyse de match (table + homographie + placement/vitesses/échanges)
        # Calibrage manuel optionnel : quad fourni en coordonnées normalisées (0-1)
        manual_quad = None
        if params.table_quad and len(params.table_quad) == 4:
            try:
                import cv2 as _cv2

                _cap = _cv2.VideoCapture(video_path)
                _w = int(_cap.get(_cv2.CAP_PROP_FRAME_WIDTH))
                _h = int(_cap.get(_cv2.CAP_PROP_FRAME_HEIGHT))
                _cap.release()
                manual_quad = np.array(
                    [
                        [float(p[0]) * _w, float(p[1]) * _h]
                        for p in params.table_quad
                    ],
                    dtype=np.float32,
                )
            except Exception as e:
                logger.warning(f"Quad de calibrage ignoré : {e}")
                manual_quad = None

        try:
            match_analysis = await asyncio.get_event_loop().run_in_executor(
                None,
                build_match_analysis,
                ttnet_results,
                video_path,
                None,
                None,
                params.player_side,
                manual_quad,
            )
        except Exception as e:
            logger.warning(f"Match analysis failed (non-blocking): {e}")
            match_analysis = None

        # 1ter. Suivi des joueurs (gauche/droite) — non bloquant
        players_results: Dict[str, Any] = {"available": False}
        try:
            players_results = await asyncio.get_event_loop().run_in_executor(
                None,
                analyze_players,
                video_path,
                (match_analysis or {}).get("table_quad_pixel"),
                4,
            )
        except Exception as e:
            logger.warning(f"Players tracking failed (non-blocking): {e}")
        # Allègement : ne garder qu'un échantillon de frames pour le résultat JSON
        if players_results.get("available"):
            sampled = (players_results.get("frames") or [])[::10]
            players_results["frames"] = sampled
            players_results["summary"]["frames_returned"] = len(sampled)

        # 2. (supprimé) VideoProcessor simulé : le pipeline sert désormais
        # exclusivement les données réelles (TTNet + match_analysis + pose).
        analysis_status[analysis_id].progress = 50.0
        analysis_status[analysis_id].current_step = "Analyse de la pose et biomécanique..."

        # 3. Pose analysis with MediaPipe
        # Non bloquant : une erreur pose ne doit pas annuler toute l'analyse
        # On aligne le contact pose sur les rebonds détectés quand c'est possible.
        pose_bounces = (match_analysis or {}).get("bounces") if match_analysis else None
        try:
            pose_results = await asyncio.get_event_loop().run_in_executor(
                None,
                analyze_video_pose,
                video_path,
                analysis_id,
                params.player_side,
                str(COMPILATIONS_DIR),
                5,
                pose_bounces,
            )
        except Exception as e:
            logger.warning(f"Pose analysis failed (non-blocking): {e}")
            pose_results = {"error": str(e)}

        analysis_status[analysis_id].progress = 70.0
        analysis_status[analysis_id].current_step = "Génération des insights..."

        # 4. Build fallback or LLM analysis
        analysis_data = _build_fallback_analysis(ttnet_results, params)

        # 5. Pose reference comparison
        pose_frames = pose_results.get("frames", []) if "error" not in pose_results else []
        stroke_type = pose_results.get("stroke_type") or _infer_stroke_type(params.focus_areas)
        pose_comparison = compare_with_reference(pose_frames, stroke_type)

        # 6. Performance metrics
        performance_metrics = _build_performance_metrics(
            ttnet_results, analysis_data, pose_results, pose_comparison
        )

        # 7. Recommendations (détaillées : LLM si configuré, sinon enrichissement statique)
        detailed_texts = await asyncio.get_event_loop().run_in_executor(
            None,
            _generate_detailed_analysis_texts,
            performance_metrics,
            match_analysis,
            pose_results if "error" not in pose_results else None,
        )
        recommendations = detailed_texts["recommendations"]
        # Alimente aussi les onglets Points Forts / Points Faibles avec des
        # paragraphes argumentés basés sur les données réelles
        analysis_data["stroke_analysis"]["strengths"] = detailed_texts["strengths"]
        analysis_data["stroke_analysis"]["weaknesses"] = detailed_texts["weaknesses"]

        # 8. Video compilations (optional) — montage auto basé sur les échanges détectés
        analysis_status[analysis_id].progress = 85.0
        analysis_status[analysis_id].current_step = "Compilation des vidéos (si FFmpeg disponible)..."
        detected_rallies = (match_analysis or {}).get("rallies") or []
        video_compilations = _compile_videos(
            video_path, analysis_id, detected_rallies=detected_rallies
        )

        # 8bis. Overlays : placement des coups + squelette de pose sur le montage auto
        if video_compilations and video_compilations.get("auto_edit"):
            analysis_status[analysis_id].current_step = "Génération des overlays vidéo (placement, pose)..."
            try:
                ffmpeg_path = get_ffmpeg_path()
                source = video_compilations["auto_edit"]
                out_dir = COMPILATIONS_DIR / analysis_id
                segments = _AUTO_EDIT_SEGMENTS.get(analysis_id, [])

                bounces = (match_analysis or {}).get("bounces") or []
                if bounces and ffmpeg_path:
                    td = TableDetector()
                    tinfo = td.detect_table_homography(video_path)
                    if tinfo and tinfo.get("H_inv") is not None:
                        placement_path = generate_placement_overlay(
                            source,
                            str(out_dir / "placement_overlay.mp4"),
                            bounces,
                            segments,
                            tinfo["H_inv"],
                            ffmpeg_path,
                        )
                        if placement_path:
                            video_compilations["placement_overlay"] = placement_path

                pose_frames_overlay = (
                    pose_results.get("frames") or []
                    if isinstance(pose_results, dict) and "error" not in pose_results
                    else []
                )
                if pose_frames_overlay and ffmpeg_path:
                    pose_path = generate_pose_overlay(
                        source,
                        str(out_dir / "pose_overlay.mp4"),
                        pose_frames_overlay,
                        segments,
                        ffmpeg_path,
                    )
                    if pose_path:
                        video_compilations["pose_overlay"] = pose_path
            except Exception as e:
                logger.warning(f"Overlay generation failed (non-blocking): {e}")

        # 9. Video info
        video_info = _get_video_info(video_path)

        # 10. Highlights
        duration = video_info.duration_seconds
        highlights = [10.0, 30.0, 60.0]
        if duration > 0:
            highlights = [min(duration, h) for h in highlights]

        # 11. Pose report (LLM or fallback)
        pose_report = await asyncio.get_event_loop().run_in_executor(
            None,
            _generate_pose_report,
            pose_results,
            pose_comparison,
            performance_metrics,
            match_analysis,
        )

        # 11bis. Plan d'entraînement personnalisé (LLM ou fallback statique)
        plan_request = PlanRequest(
            goal="progression_generale",
            priority=(
                params.focus_areas[0]
                if params.focus_areas
                and params.focus_areas[0]
                in ("technique_coups", "service_remise", "deplacement", "physique")
                else "technique_coups"
            ),
            difficulty=params.skill_level,
        )
        training_plan = await asyncio.get_event_loop().run_in_executor(
            None,
            _generate_training_plan,
            plan_request,
            match_analysis or {},
            pose_results,
            performance_metrics,
        )

        # 12. Build final result
        technical_analysis = TechnicalAnalysis(
            stroke_analysis=analysis_data.get("stroke_analysis", {}),
            positioning_analysis=analysis_data.get("positioning_analysis", {}),
            timing_analysis=analysis_data.get("timing_analysis", {}),
            movement_analysis={
                "average_speed": ttnet_results.get("match_statistics", {})
                .get("ball_trajectory_analysis", {})
                .get("average_speed_pixels_per_frame", 0),
                "max_speed": ttnet_results.get("match_statistics", {})
                .get("ball_trajectory_analysis", {})
                .get("max_speed_pixels_per_frame", 0),
            },
            ttnet_analysis=ttnet_results.get("match_statistics", {}),
            pose_analysis=pose_results if "error" not in pose_results else None,
            match_analysis=match_analysis,
        )

        result = AnalysisResult(
            analysis_id=analysis_id,
            video_info=video_info,
            technical_analysis=technical_analysis,
            performance_metrics=performance_metrics,
            recommendations=recommendations,
            highlights_timestamps=highlights,
            confidence_score=ttnet_results.get("match_statistics", {}).get("ball_detection_rate", 0),
            video_compilations=video_compilations,
            lexicon_analysis=None,
            table_tennis_scoring=_apply_table_tennis_scoring(
                ttnet_results, match_analysis, params.player_side
            ),
            pose_reference_comparison=pose_comparison,
            pose_report=pose_report,
            overlay_frames=pose_results.get("overlay_frames") if "error" not in pose_results else None,
            match_analysis=match_analysis,
            players_analysis=players_results if players_results.get("available") else None,
            training_plan=training_plan,
        )

        analysis_results[analysis_id] = result
        analysis_status[analysis_id].status = "completed"
        analysis_status[analysis_id].progress = 100.0
        analysis_status[analysis_id].completed_at = datetime.now(timezone.utc)
        analysis_status[analysis_id].current_step = "Analyse terminée"

        logger.info(f"Analysis {analysis_id} completed successfully")

    except Exception as e:
        logger.exception(f"Analysis {analysis_id} failed: {e}")
        analysis_status[analysis_id].status = "failed"
        analysis_status[analysis_id].progress = 0.0
        analysis_status[analysis_id].error_message = str(e)
        analysis_status[analysis_id].current_step = f"Erreur: {e}"

    finally:
        # Clean up uploaded original video
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
        except Exception:
            pass


# API Routes --------------------------------------------------------------------
@app.post("/api/analyze")
async def upload_and_analyze_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    player_side: str = Form("droite"),
    skill_level: str = Form("intermediaire"),
    focus_areas: str = Form("technique_coups,positionnement,timing"),
    table_quad: str = Form(""),
):
    if not video.filename or not video.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        raise HTTPException(
            status_code=400,
            detail="Format de fichier non supporté. Utilisez MP4, AVI, MOV ou MKV.",
        )

    analysis_id = str(uuid.uuid4())
    file_extension = Path(video.filename).suffix
    file_path = UPLOAD_DIR / f"{analysis_id}{file_extension}"

    # Copie par chunks pour ne pas charger toute la vidéo en mémoire
    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await video.read(1024 * 1024):
            await f.write(chunk)

    # Calibrage manuel optionnel : JSON "[[x,y],[x,y],[x,y],[x,y]]" normalisé (0-1)
    parsed_quad = None
    if table_quad:
        try:
            _quad = json.loads(table_quad)
            if (
                isinstance(_quad, list)
                and len(_quad) == 4
                and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in _quad)
            ):
                parsed_quad = [[float(p[0]), float(p[1])] for p in _quad]
        except Exception:
            parsed_quad = None

    params = AnalysisRequest(
        player_side=player_side,
        skill_level=skill_level,
        focus_areas=[a.strip() for a in focus_areas.split(",")],
        table_quad=parsed_quad,
    )

    analysis_status[analysis_id] = AnalysisStatus(
        analysis_id=analysis_id,
        status="queued",
        progress=0.0,
        created_at=datetime.now(timezone.utc),
        current_step="En attente...",
    )

    background_tasks.add_task(_process_video_analysis, analysis_id, str(file_path), params)

    return {
        "analysis_id": analysis_id,
        "status": "queued",
        "message": "Vidéo téléchargée avec succès. Analyse en cours...",
        "estimated_time": "1-2 minutes",
    }


@app.get("/api/analysis/{analysis_id}/status")
async def get_analysis_status(analysis_id: str):
    if analysis_id not in analysis_status:
        raise HTTPException(status_code=404, detail="ID d'analyse introuvable")
    return analysis_status[analysis_id]


@app.get("/api/analysis/{analysis_id}/results")
async def get_analysis_results(analysis_id: str):
    if analysis_id not in analysis_status:
        raise HTTPException(status_code=404, detail="ID d'analyse introuvable")

    status = analysis_status[analysis_id]
    if status.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Analyse non terminée. Statut actuel : {status.status}",
        )

    if analysis_id not in analysis_results:
        raise HTTPException(status_code=500, detail="Résultats d'analyse introuvables")

    return analysis_results[analysis_id]


@app.get("/api/analysis/{analysis_id}/video/{video_type}")
async def get_compilation_video(analysis_id: str, video_type: str):
    if analysis_id not in analysis_status:
        raise HTTPException(status_code=404, detail="ID d'analyse introuvable")

    if analysis_status[analysis_id].status != "completed":
        raise HTTPException(status_code=400, detail="Analyse non terminée")

    if analysis_id not in analysis_results:
        raise HTTPException(status_code=500, detail="Résultats d'analyse introuvables")

    result = analysis_results[analysis_id]
    if not result.video_compilations or video_type not in result.video_compilations:
        raise HTTPException(status_code=404, detail="Vidéo de compilation introuvable")

    video_path = result.video_compilations[video_type]
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Fichier vidéo introuvable")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{video_type}_{analysis_id}.mp4",
    )


@app.get("/api/analysis/{analysis_id}/pose/frame/{frame_index}")
async def get_pose_overlay_frame(analysis_id: str, frame_index: int):
    """Serve un frame overlay de pose en JPEG."""
    if analysis_id not in analysis_status:
        raise HTTPException(status_code=404, detail="ID d'analyse introuvable")

    if analysis_status[analysis_id].status != "completed":
        raise HTTPException(status_code=400, detail="Analyse non terminée")

    if analysis_id not in analysis_results:
        raise HTTPException(status_code=500, detail="Résultats d'analyse introuvables")

    result = analysis_results[analysis_id]
    overlay_frames = result.overlay_frames or []
    if frame_index < 0 or frame_index >= len(overlay_frames):
        raise HTTPException(status_code=404, detail="Frame introuvable")

    frame_path = overlay_frames[frame_index]
    if not frame_path or not os.path.exists(frame_path):
        raise HTTPException(status_code=404, detail="Fichier image introuvable")

    return FileResponse(
        frame_path,
        media_type="image/jpeg",
        filename=f"pose_{analysis_id}_{frame_index}.jpg",
    )


@app.get("/api/")
async def root():
    return {"message": "PingPro API - Analyse IA Tennis de Table"}


@app.post("/api/plan")
async def generate_training_plan(request: PlanRequest):
    """Plan d'entraînement personnalisé (LLM si configuré, sinon statique)."""
    latest_match_analysis = None
    latest_metrics = None
    if analysis_results:
        latest = max(analysis_results.values(), key=lambda r: r.video_info.duration_seconds)
        latest_match_analysis = latest.match_analysis
        latest_metrics = latest.performance_metrics
    plan = await asyncio.get_event_loop().run_in_executor(
        None,
        _generate_training_plan,
        request,
        latest_match_analysis,
        {},
        latest_metrics,
    )
    return plan
