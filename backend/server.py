"""
PingPro MVP Backend
FastAPI server for table tennis video analysis.
No external DB or LLM required: everything runs in-memory and TTNet heuristics
provide the analysis. Video compilations are generated when FFmpeg is available.
"""

import asyncio
import logging
import os
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
from video_processor import VideoProcessor
from pose_analysis import analyze_video_pose
from pose_reference import compare_with_reference, suggest_improvements
from table_detector import TableDetector
from match_analysis import build_match_analysis, extract_video_fallback_scale

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
    return shutil.which("ffmpeg") is not None


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
    if not _has_ffmpeg():
        return False
    try:
        subprocess.run(
            [
                "ffmpeg",
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


def _compile_auto_edit(video_path: str, out_dir: Path, rallies: List[Dict[str, Any]]) -> Optional[str]:
    """Montage auto : concatène les échanges réellement détectés (sans temps morts)."""
    if not rallies:
        return None
    segments_file = out_dir / "auto_edit_segments.txt"
    with open(segments_file, "w", encoding="utf-8") as f:
        for rally in rallies[:40]:  # garde-fou : 40 échanges max
            start = max(0.0, float(rally["start_time"]) - 0.5)
            end = float(rally["end_time"]) + 1.0
            f.write(f"file '{Path(video_path).as_posix()}'\n")
            f.write(f"inpoint {start}\n")
            f.write(f"outpoint {end}\n")

    output_path = out_dir / "auto_edit.mp4"
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(segments_file),
                "-c", "copy",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=300,
        )
        return str(output_path) if output_path.exists() else None
    except Exception as e:
        logger.error(f"Auto-edit compilation failed: {e}")
        return None


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
        if detected_rallies:
            auto_edit = _compile_auto_edit(video_path, out_dir, detected_rallies)
            if auto_edit:
                compilations["auto_edit"] = auto_edit

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


def _apply_table_tennis_scoring(ttnet_results: Dict[str, Any]) -> Dict[str, Any]:
    stats = ttnet_results.get("match_statistics", {})
    events = stats.get("event_summary", {})
    total_bounces = events.get("ball_bounce", 15)
    serves = events.get("serve", 6)
    detection_rate = stats.get("ball_detection_rate", 0.65)

    total_points = min(25, max(11, total_bounces // 2))
    player1 = int(total_points * detection_rate)
    player2 = total_points - player1

    # Apply table-tennis 11-point rule
    if player1 >= 11 and player1 - player2 >= 2:
        pass
    elif player2 >= 11 and player2 - player1 >= 2:
        pass
    elif detection_rate > 0.6:
        player1, player2 = 11, max(0, min(9, player2))
    else:
        player1, player2 = max(0, min(9, player1)), 11

    progression = []
    for i in range(1, 20):
        ratio = i / 19.0
        progression.append(
            {
                "point": i,
                "player1": int(player1 * ratio),
                "player2": int(player2 * ratio),
            }
        )

    return {
        "final_score": {
            "player1": player1,
            "player2": player2,
            "winner": "player1" if player1 > player2 else "player2",
        },
        "sets": {
            "player1_sets": 1 if player1 > player2 else 0,
            "player2_sets": 1 if player2 > player1 else 0,
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
            "longest_rally": max(3, total_bounces // max(1, serves)),
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
        try:
            match_analysis = await asyncio.get_event_loop().run_in_executor(
                None, build_match_analysis, ttnet_results, video_path
            )
        except Exception as e:
            logger.warning(f"Match analysis failed (non-blocking): {e}")
            match_analysis = None

        # 2. Video processor (rallies + technical analysis)
        # Non bloquant : les compilations servies sont générées séparément
        try:
            video_processor = VideoProcessor()
            video_processing_results = await video_processor.process_video_complete(
                video_path, generate_compilations=False
            )
        except Exception as e:
            logger.warning(f"Video processor failed (non-blocking): {e}")
            video_processing_results = {}

        analysis_status[analysis_id].progress = 50.0
        analysis_status[analysis_id].current_step = "Analyse de la pose et biomécanique..."

        # 3. Pose analysis with MediaPipe
        # Non bloquant : une erreur pose ne doit pas annuler toute l'analyse
        try:
            pose_results = await asyncio.get_event_loop().run_in_executor(
                None,
                analyze_video_pose,
                video_path,
                analysis_id,
                params.player_side,
                str(COMPILATIONS_DIR),
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
        stroke_type = _infer_stroke_type(params.focus_areas)
        pose_comparison = compare_with_reference(pose_frames, stroke_type)

        # 6. Performance metrics
        performance_metrics = _build_performance_metrics(
            ttnet_results, analysis_data, pose_results, pose_comparison
        )

        # 7. Recommendations (from TTNet + pose suggestions)
        recommendations = ttnet_results.get("technical_insights", {}).get(
            "technical_recommendations", []
        )
        if "error" not in pose_results:
            recommendations.extend(suggest_improvements(pose_results, pose_comparison))
        if not recommendations:
            recommendations = [
                "Continuer l'entraînement régulier",
                "Filmer de vraies sessions pour une analyse plus précise",
                "Travailler la régularité technique",
            ]
        recommendations = list(dict.fromkeys(recommendations))[:6]

        # 8. Video compilations (optional) — montage auto basé sur les échanges détectés
        analysis_status[analysis_id].progress = 85.0
        analysis_status[analysis_id].current_step = "Compilation des vidéos (si FFmpeg disponible)..."
        detected_rallies = (match_analysis or {}).get("rallies") or []
        video_compilations = _compile_videos(
            video_path, analysis_id, detected_rallies=detected_rallies
        )

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
            lexicon_analysis=video_processing_results.get("technical_analysis", {}),
            table_tennis_scoring=_apply_table_tennis_scoring(ttnet_results),
            pose_reference_comparison=pose_comparison,
            pose_report=pose_report,
            overlay_frames=pose_results.get("overlay_frames") if "error" not in pose_results else None,
            match_analysis=match_analysis,
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

    params = AnalysisRequest(
        player_side=player_side,
        skill_level=skill_level,
        focus_areas=[a.strip() for a in focus_areas.split(",")],
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
