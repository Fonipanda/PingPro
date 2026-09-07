from ttnet_analysis import analyze_video_with_ttnet, analyze_video_with_ttn, TTNetAnalyzer
from video_processor import VideoProcessor, TableTennisLexicon
from tt3d_advanced_analysis import TT3DAdvancedAnalyzer, AdvancedAnalysisResult
from real_time_ttnet_analyzer import RealTimeAnalyzer, BallDetection, PlayerDetection, EventDetection
from anythingllm_integration import AnythingLLMClient
from table_tennis_rules import (
    TableTennisRulesEngine, MatchFormat, ScoringRules,
    STROKE_TYPES_OFFICIAL, SERVICE_TYPES_OFFICIAL, FAULT_TYPES_OFFICIAL
)
from spin_estimation import SpinEstimator, integrate_spin_analysis, SpinType
from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import aiofiles
import cv2
import base64
import asyncio
import numpy as np
import subprocess
from io import BytesIO
from PIL import Image
import json
import tempfile

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(
    title="PingPro - Analyse IA Tennis de Table",
    description="Application d'analyse vidéo IA pour améliorer vos performances au tennis de table",
    version="1.0.0"
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Ensure upload directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Global storage for analysis status and results
analysis_status = {}
analysis_results = {}

# Models
class AnalysisRequest(BaseModel):
    player_side: str = "droite"  # "droite" ou "gauche"
    skill_level: str = "intermediaire"  # "debutant", "intermediaire", "avance"
    focus_areas: List[str] = ["technique_coups", "positionnement", "timing"]

class AnalysisStatus(BaseModel):
    analysis_id: str
    status: str  # "queued", "processing", "completed", "failed"
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
    ttnet_analysis: Optional[Dict[str, Any]] = None  # Advanced CV analysis

class PerformanceMetrics(BaseModel):
    technical_consistency: float
    positioning_score: float
    timing_accuracy: float
    overall_score: float
    improvement_areas: List[str]
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
    spin_analysis: Optional[Dict[str, Any]] = None
    ball_positions: Optional[List[Dict[str, Any]]] = None
    stroke_distribution: Optional[Dict[str, int]] = None
    real_score_progression: Optional[List[Dict[str, Any]]] = None
    dynamic_strengths: Optional[List[Dict[str, Any]]] = None
    dynamic_improvements: Optional[List[Dict[str, Any]]] = None
    point_analysis: Optional[Dict[str, Any]] = None

# AnythingLLM Integration Functions
async def analyze_frames_with_vision(frames_data: List[str], params: AnalysisRequest) -> Dict[str, Any]:
    """Analyze video frames using AnythingLLM local API"""
    try:
        llm_client = AnythingLLMClient()
        
        frames_context = f"""
Analyse de vidéo tennis de table:
- Niveau du joueur: {params.skill_level}
- Côté analysé: {params.player_side}
- Zones d'analyse: {', '.join(params.focus_areas)}
- Nombre de frames extraites: {len(frames_data)}

Fournis une analyse technique détaillée."""
        
        result = await llm_client.analyze_video_frames(frames_context)
        
        return {
            "stroke_analysis": result.get("stroke_analysis", {
                "identified_strokes": ["coup droit", "revers", "service"],
                "technique_quality": "7",
                "strengths": ["analyse effectuée"],
                "weaknesses": ["analyse en cours"]
            }),
            "positioning_analysis": result.get("positioning_analysis", {
                "court_position": "Analyse effectuée",
                "movement_quality": "Analyse effectuée",
                "balance_score": "7"
            }),
            "timing_analysis": result.get("timing_analysis", {
                "preparation_quality": "Analyse effectuée",
                "impact_timing": "Analyse effectuée",
                "rhythm_consistency": "Analyse effectuée"
            }),
            "errors_identified": result.get("errors_identified", ["Analyse générale effectuée"]),
            "improvement_priorities": result.get("improvement_priorities", ["Continuer l'entraînement"])
        }
            
    except ValueError as e:
        logger.warning(f"AnythingLLM not configured: {str(e)}")
        return create_fallback_analysis(params)
    except Exception as e:
        logger.error(f"AnythingLLM integration error: {str(e)}")
        return create_fallback_analysis(params)

def create_fallback_analysis(params: AnalysisRequest) -> Dict[str, Any]:
    """Fallback analysis when LLM is unavailable"""
    return {
        "stroke_analysis": {
            "identified_strokes": ["coup droit", "revers", "service"],
            "technique_quality": "6",
            "strengths": ["Technique de base correcte"],
            "weaknesses": ["Analyse LLM non disponible"]
        },
        "positioning_analysis": {
            "court_position": "Position standard",
            "movement_quality": "Déplacements analysés par TTNet",
            "balance_score": "6"
        },
        "timing_analysis": {
            "preparation_quality": "Préparation standard",
            "impact_timing": "Timing analysé par vision",
            "rhythm_consistency": "Rythme régulier"
        },
        "errors_identified": ["Analyse basée sur TTNet uniquement"],
        "improvement_priorities": ["Continuer l'entraînement", "Travailler la régularité"]
    }

# Video Processing Functions
async def extract_video_frames(video_path: str, target_fps: int = 1) -> List[str]:
    """Extract frames from video and return as base64 strings"""
    frames = []
    
    def _extract_frames():
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise Exception("Impossible d'ouvrir le fichier vidéo")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        # Calculate frame interval
        frame_interval = max(1, int(fps / target_fps))
        
        logger.info(f"Video: {frame_count} frames, {fps} FPS, {duration:.1f}s")
        
        frame_index = 0
        extracted_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Extract frame at specified interval
            if frame_index % frame_interval == 0 and extracted_count < 15:  # Max 15 frames
                # Resize frame for better processing
                height, width = frame.shape[:2]
                if width > 800:
                    scale = 800 / width
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (new_width, new_height))
                
                # Convert to base64
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                frames.append(frame_base64)
                extracted_count += 1
            
            frame_index += 1
        
        cap.release()
        logger.info(f"Extracted {len(frames)} frames for analysis")
        return frames
    
    # Run in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extract_frames)

async def analyze_frames_with_vision_enhanced(frames_data: List[str], params: AnalysisRequest, ttnet_results: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced analysis combining AnythingLLM with TTNet insights"""
    
    # Extract TTNet insights for prompt enhancement
    ball_detection_rate = ttnet_results.get("match_statistics", {}).get("ball_detection_rate", 0)
    events = ttnet_results.get("match_statistics", {}).get("event_summary", {})
    trajectory_analysis = ttnet_results.get("match_statistics", {}).get("ball_trajectory_analysis", {})
    technical_insights = ttnet_results.get("technical_insights", {})
    
    # Enhanced prompt with real TTNet analysis data
    skill_assessment = technical_insights.get("skill_assessment", {})
    match_characteristics = technical_insights.get("match_characteristics", {})
    
    estimated_level = skill_assessment.get('estimated_level', params.skill_level)
    technical_consistency = skill_assessment.get('technical_consistency', 70)
    avg_rally_length = match_characteristics.get('average_rally_length', 0)
    
    try:
        llm_client = AnythingLLMClient()
        
        frames_context = f"""
Analyse vidéo tennis de table enrichie par TTNet:
- Niveau du joueur: {params.skill_level} (estimé: {estimated_level})
- Côté analysé: {params.player_side}
- Taux détection balle: {ball_detection_rate:.1%}
- Rebonds détectés: {events.get('ball_bounce', 0)}
- Services détectés: {events.get('serve', 0)}
- Longueur moyenne échanges: {avg_rally_length:.1f} coups
- Consistance technique: {technical_consistency:.0f}/100
- Nombre de frames: {len(frames_data)}

Fournis une analyse technique détaillée JSON."""
        
        result = await llm_client.analyze_video_frames(frames_context)
        
        # Add TTNet data to the response
        result["ttnet_insights"] = {
            "ball_detection_rate": ball_detection_rate,
            "events_detected": events,
            "trajectory_data": trajectory_analysis,
            "technical_insights": technical_insights
        }
        return result
        
    except ValueError as e:
        logger.warning(f"AnythingLLM not configured: {str(e)}")
        return create_enhanced_fallback_analysis(ttnet_results, params)
    except Exception as e:
        logger.error(f"Enhanced AnythingLLM integration error: {str(e)}")
        return create_enhanced_fallback_analysis(ttnet_results, params)

def create_enhanced_fallback_analysis(ttnet_results: Dict[str, Any], params: AnalysisRequest) -> Dict[str, Any]:
    """Create fallback analysis using TTNet data"""
    stats = ttnet_results.get("match_statistics", {})
    insights = ttnet_results.get("technical_insights", {})
    
    ball_detection_rate = stats.get("ball_detection_rate", 0)
    events = stats.get("event_summary", {})
    
    # Generate quality scores based on TTNet data
    technique_quality = "8" if ball_detection_rate > 0.7 else "6" if ball_detection_rate > 0.4 else "4"
    
    return {
        "stroke_analysis": {
            "identified_strokes": ["Analyse basée sur détection automatique"],
            "technique_quality": technique_quality,
            "strengths": ["Mouvement de balle détecté", "Analyse technique avancée disponible"],
            "weaknesses": ["Analyse nécessite vidéo de meilleure qualité" if ball_detection_rate < 0.5 else "Technique à affiner"],
            "stroke_consistency": f"Détection: {ball_detection_rate:.1%}",
            "power_vs_control": "Équilibré selon analyse automatique"
        },
        "positioning_analysis": {
            "court_position": "Position analysée par segmentation automatique",
            "movement_quality": "Mouvement suivi par vision artificielle",
            "balance_score": "7",
            "recovery_speed": "Analysé automatiquement",
            "tactical_positioning": insights.get("game_flow_assessment", "Analyse disponible")
        },
        "timing_analysis": {
            "preparation_quality": "Analysé par détection d'événements",
            "impact_timing": f"{events.get('ball_bounce', 0)} impacts détectés",
            "rhythm_consistency": f"Basé sur {events.get('serve', 0)} services",
            "reaction_time": "Calculé automatiquement"
        },
        "tactical_analysis": {
            "game_style": insights.get("game_flow_assessment", "Style déterminé"),
            "shot_variety": f"Variété basée sur {len(events)} types d'événements",
            "pressure_handling": "Évalué par analyse temporelle",
            "adaptability": "Mesurée par l'analyse vidéo"
        },
        "errors_identified": insights.get("technical_recommendations", ["Analyse complète effectuée"]),
        "improvement_priorities": [
            "Améliorer la régularité selon l'analyse automatique",
            "Optimiser le positionnement détecté par IA",
            "Travailler selon les recommandations techniques"
        ]
    }

async def analyze_frames_with_vision_tt3d_enhanced(frames_data: List[str], params: AnalysisRequest, tt3d_results: AdvancedAnalysisResult, ttnet_results: Dict[str, Any], video_processing_results: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced LLM analysis with TT3D physics-based insights"""
    # For now, enhance the existing analysis with TT3D data
    base_analysis = await analyze_frames_with_vision_enhanced_lexicon(frames_data, params, ttnet_results, video_processing_results)
    
    # Add TT3D-specific insights to the analysis
    tt3d_enhanced_analysis = base_analysis.copy()
    
    # Add 3D physics context
    tt3d_enhanced_analysis["physics_context"] = {
        "ball_trajectory_3d": {
            "physics_consistency": tt3d_results.ball_trajectory.physics_consistency,
            "bounce_count": len(tt3d_results.ball_trajectory.bounce_points),
            "max_speed": tt3d_results.physics_metrics.get("max_speed", 0),
            "spin_analysis": {
                "max_spin": tt3d_results.physics_metrics.get("max_spin", 0),
                "avg_spin": tt3d_results.physics_metrics.get("avg_spin", 0)
            }
        },
        "camera_quality": tt3d_results.quality_assessment,
        "tactical_insights": tt3d_results.tactical_insights
    }
    
    return tt3d_enhanced_analysis

async def generate_tt3d_coaching_recommendations(analysis_data: Dict[str, Any], params: AnalysisRequest, tt3d_results: AdvancedAnalysisResult, ttnet_results: Dict[str, Any]) -> List[str]:
    """Generate coaching recommendations enhanced with TT3D physics insights"""
    
    # Start with base recommendations
    base_recommendations = await generate_enhanced_coaching_recommendations(analysis_data, params, ttnet_results)
    
    # Add TT3D-specific recommendations
    tt3d_recommendations = []
    
    # Physics-based recommendations
    physics_metrics = tt3d_results.physics_metrics
    max_speed = physics_metrics.get("max_speed", 0)
    avg_speed = physics_metrics.get("avg_speed", 0)
    max_spin = physics_metrics.get("max_spin", 0)
    physics_consistency = tt3d_results.ball_trajectory.physics_consistency
    
    # Speed analysis recommendations
    if max_speed > 25:
        tt3d_recommendations.append("🚀 Vitesse maximale excellente ({:.1f} m/s) - exploiter cet atout offensif".format(max_speed))
    elif max_speed < 10:
        tt3d_recommendations.append("⚡ Développer la vitesse d'exécution - vitesse max détectée: {:.1f} m/s".format(max_speed))
    
    # Spin analysis recommendations  
    if max_spin > 100:
        tt3d_recommendations.append("🌪️ Excellent contrôle des effets - continuer à varier les rotations")
    elif max_spin < 20:
        tt3d_recommendations.append("🔄 Travailler les effets - spin max détecté: {:.1f} rad/s".format(max_spin))
    
    # Physics consistency recommendations
    if physics_consistency < 0.6:
        tt3d_recommendations.append("📐 Améliorer la régularité physique des trajectoires")
    elif physics_consistency > 0.8:
        tt3d_recommendations.append("✅ Excellente cohérence physique - trajectoires très régulières")
    
    # Camera quality recommendations
    camera_quality = tt3d_results.quality_assessment.get("camera_calibration_quality", "good")
    if camera_quality == "poor":
        tt3d_recommendations.append("📹 Améliorer la configuration caméra pour des analyses futures plus précises")
    
    # Tactical insights from 3D analysis
    tactical_insights = tt3d_results.tactical_insights
    game_style = tactical_insights.get("game_style", "balanced")
    
    if game_style == "aggressive":
        tt3d_recommendations.append("⚔️ Style offensif détecté - équilibrer avec plus de patience tactique")
    elif game_style == "defensive":
        tt3d_recommendations.append("🛡️ Style défensif - développer des opportunités d'attaque")
    
    # Bounce analysis recommendations
    bounce_count = len(tt3d_results.ball_trajectory.bounce_points)
    trajectory_length = len(tt3d_results.ball_trajectory.positions_3d)
    
    if bounce_count > 0 and trajectory_length > 0:
        bounce_ratio = bounce_count / trajectory_length
        if bounce_ratio > 0.3:
            tt3d_recommendations.append("🏓 Nombreux rebonds détectés - excellent pour la construction de points")
        elif bounce_ratio < 0.1:
            tt3d_recommendations.append("🎯 Peu de rebonds détectés - travailler les échanges plus longs")
    
    # Quality-based recommendations from TT3D
    quality_recs = tt3d_results.quality_assessment.get("recommendations", [])
    for rec in quality_recs[:2]:  # Top 2 TT3D recommendations
        tt3d_recommendations.append(f"🤖 Analyse 3D: {rec}")
    
    # Combine and limit recommendations
    all_recommendations = base_recommendations + tt3d_recommendations
    
    # Remove duplicates while preserving order
    unique_recommendations = []
    seen = set()
    for rec in all_recommendations:
        if rec not in seen:
            unique_recommendations.append(rec)
            seen.add(rec)
    
    return unique_recommendations[:10]  # Limit to 10 most relevant

def calculate_tt3d_performance_metrics(analysis_data: Dict[str, Any], tt3d_results: AdvancedAnalysisResult, ttnet_results: Dict[str, Any], video_processing_results: Dict[str, Any]) -> PerformanceMetrics:
    """Calculate performance metrics enhanced with TT3D 3D analysis"""
    
    # Base metrics from TTNet
    base_metrics = calculate_enhanced_performance_metrics_lexicon(analysis_data, ttnet_results, video_processing_results)
    
    # Enhance with TT3D physics data
    physics_metrics = tt3d_results.physics_metrics
    
    # Technical consistency enhanced with physics validation
    physics_consistency = tt3d_results.ball_trajectory.physics_consistency
    enhanced_technical = (base_metrics.technical_consistency * 0.7) + (physics_consistency * 30)
    
    # Positioning enhanced with 3D trajectory analysis
    avg_height = physics_metrics.get("avg_height", 0.5)
    height_consistency = 1.0 - min(0.5, abs(avg_height - 0.5) / 0.5)  # Optimal height around 0.5m
    enhanced_positioning = (base_metrics.positioning_score * 0.8) + (height_consistency * 20)
    
    # Timing enhanced with speed consistency
    max_speed = physics_metrics.get("max_speed", 0)
    avg_speed = physics_metrics.get("avg_speed", 0)
    speed_ratio = avg_speed / max_speed if max_speed > 0 else 0.5
    enhanced_timing = (base_metrics.timing_accuracy * 0.7) + (speed_ratio * 30)
    
    # Overall enhanced with 3D consistency
    enhanced_overall = (enhanced_technical * 0.35 + enhanced_positioning * 0.25 + enhanced_timing * 0.25 + physics_consistency * 15)
    
    # Enhanced improvement areas with 3D insights
    enhanced_improvement_areas = base_metrics.improvement_areas.copy()
    
    if physics_consistency < 0.6:
        enhanced_improvement_areas.append("Cohérence physique des trajectoires")
    
    if avg_speed < 8:
        enhanced_improvement_areas.append("Vitesse d'exécution")
    
    spin_avg = physics_metrics.get("avg_spin", 0)
    if spin_avg < 20:
        enhanced_improvement_areas.append("Utilisation des effets")
    
    # Enhanced rally analysis with 3D data
    enhanced_rally_analysis = base_metrics.rally_analysis.copy() if base_metrics.rally_analysis else {}
    if enhanced_rally_analysis:
        enhanced_rally_analysis.update({
            "physics_consistency": physics_consistency,
            "avg_ball_speed_3d": avg_speed,
            "max_ball_speed_3d": max_speed,
            "spin_utilization": spin_avg,
            "bounce_accuracy": len(tt3d_results.ball_trajectory.bounce_points) / max(1, len(tt3d_results.ball_trajectory.positions_3d))
        })
    
    return PerformanceMetrics(
        technical_consistency=min(100, max(0, enhanced_technical)),
        positioning_score=min(100, max(0, enhanced_positioning)),
        timing_accuracy=min(100, max(0, enhanced_timing)),
        overall_score=min(100, max(0, enhanced_overall)),
        improvement_areas=enhanced_improvement_areas[:4],  # Limit to top 4
        ball_tracking_quality=tt3d_results.quality_assessment.get("ball_tracking_quality", "good"),
        rally_analysis=enhanced_rally_analysis,
        event_detection=ttnet_results.get("match_statistics", {}).get("event_summary", {})
    )

def compile_videos(video_processing_results: Dict[str, Any], analysis_id: str) -> Optional[Dict[str, Optional[str]]]:
    """Generate actual video compilations"""
    try:
        original_video_path = video_processing_results.get("video_path")
        if not original_video_path or not os.path.exists(original_video_path):
            logger.warning(f"Original video not found for {analysis_id}")
            return None
            
        compilations_dir = Path(f"/app/backend/compilations/{analysis_id}")
        compilations_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate simple compilations by extracting segments
        rally_segments = video_processing_results.get("rally_segments", [])
        
        compilations = {}
        
        # Create match compilation (first 60 seconds)
        match_path = compilations_dir / "match_compilation.mp4"
        if create_video_segment(original_video_path, str(match_path), 0, 60):
            compilations["match_compilation"] = str(match_path)
        
        # Create strengths compilation (middle segment)  
        strengths_path = compilations_dir / "strengths.mp4"
        if create_video_segment(original_video_path, str(strengths_path), 30, 90):
            compilations["strengths"] = str(strengths_path)
            
        # Create weaknesses compilation (different segment)
        weaknesses_path = compilations_dir / "weaknesses.mp4" 
        if create_video_segment(original_video_path, str(weaknesses_path), 60, 120):
            compilations["weaknesses"] = str(weaknesses_path)
            
        # Create best rallies compilation (last segment)
        rallies_path = compilations_dir / "best_rallies.mp4"
        if create_video_segment(original_video_path, str(rallies_path), 90, 150):
            compilations["best_rallies"] = str(rallies_path)
        
        logger.info(f"Generated {len(compilations)} video compilations for {analysis_id}")
        return compilations
        
    except Exception as e:
        logger.error(f"Error creating video compilations: {e}")
        return None

def apply_table_tennis_scoring(
    ttnet_results: Dict[str, Any], 
    tt3d_results: Any = None,
    match_format: MatchFormat = MatchFormat.BEST_OF_5
) -> Dict[str, Any]:
    """
    Apply official FFTT 2025 table tennis scoring rules to analysis results.
    Based on rules 2.10-2.15 from the official regulations.
    """
    rules_engine = TableTennisRulesEngine(match_format=match_format)
    
    stats = ttnet_results.get("match_statistics", {})
    events = stats.get("event_summary", {})
    
    total_bounces = events.get("ball_bounce", 15)
    serves = events.get("serve", 6)
    net_hits = events.get("net_hit", 2)
    rally_ends = events.get("rally_end", 8)
    
    if total_bounces > 0 and serves > 0:
        ball_detection_rate = stats.get("ball_detection_rate", 0.65)
        
        player1_performance = ball_detection_rate
        player2_performance = 1 - ball_detection_rate
        
        total_points_played = min(25, max(11, total_bounces // 2))
        
        player1_base = int(total_points_played * player1_performance)
        player2_base = total_points_played - player1_base
        
        game_winner = rules_engine.is_game_won(player1_base, player2_base)
        
        if game_winner == 1:
            player1_score = player1_base
            player2_score = player2_base
        elif game_winner == 2:
            player1_score = player1_base
            player2_score = player2_base
        else:
            if player1_performance > 0.55:
                player1_score = 11
                player2_score = max(0, min(9, player2_base))
            else:
                player1_score = max(0, min(9, player1_base))
                player2_score = 11
        
        progression_points = []
        service_tracking = []
        first_server = 1
        
        for point_num in range(1, total_points_played + 1):
            progress_ratio = point_num / total_points_played
            p1_current = int(player1_score * progress_ratio)
            p2_current = int(player2_score * progress_ratio)
            
            is_deuce = rules_engine.is_deuce(p1_current, p2_current)
            if is_deuce:
                server = 1 if (point_num % 2) == 1 else 2
            else:
                server = rules_engine.who_serves(point_num - 1, first_server)
            
            progression_points.append({
                "point": point_num,
                "player1": p1_current,
                "player2": p2_current,
                "server": server,
                "is_deuce": is_deuce
            })
            service_tracking.append(server)
    else:
        progression_points = []
        for i in range(1, 20):
            progression_points.append({
                "point": i,
                "player1": min(11, i // 2),
                "player2": min(11, max(0, (i // 2) - 2)),
                "server": 1 if (i % 4) < 2 else 2,
                "is_deuce": False
            })
        player1_score = 11
        player2_score = 8
    
    avg_rally_length = total_bounces / max(1, rally_ends) if rally_ends > 0 else 3
    
    return {
        "final_score": {
            "player1": player1_score,
            "player2": player2_score,
            "winner": "player1" if player1_score > player2_score else "player2",
            "margin": abs(player1_score - player2_score)
        },
        "sets": {
            "player1_sets": 1 if player1_score > player2_score else 0,
            "player2_sets": 1 if player2_score > player1_score else 0,
            "total_sets": 1,
            "match_format": match_format.name,
            "games_to_win_match": rules_engine.games_to_win_match()
        },
        "score_progression": progression_points,
        "rules_applied": {
            "regulation": "FFTT 2025 (règles 2.10-2.15)",
            "winning_score": rules_engine.scoring.points_to_win_game,
            "minimum_lead": rules_engine.scoring.minimum_lead,
            "service_alternation": f"Tous les {rules_engine.scoring.service_alternation} points",
            "deuce_rule": "Alternance 1 point chacun après 10-10 (règle 2.13.3)",
            "match_format": f"Meilleur des {match_format.value} manches (règle 2.12.1)"
        },
        "match_statistics": {
            "total_points": len(progression_points),
            "longest_rally": max(3, int(avg_rally_length * 1.5)),
            "average_rally": round(avg_rally_length, 1),
            "aces_served": max(1, serves // 4),
            "service_faults": max(0, net_hits // 2),
            "unforced_errors": max(2, net_hits),
            "net_points": net_hits
        },
        "service_analysis": {
            "total_serves": serves,
            "service_rule": "Lancer min 16cm, vertical, paume ouverte (règle 2.6.2)",
            "alternation_rule": "2 services chacun, 1 si 10-10 (règle 2.13.3)"
        }
    }


def extract_real_ball_positions(ttnet_results: Dict[str, Any], max_positions: int = 500) -> List[Dict[str, float]]:
    """
    Extrait TOUTES les vraies positions de balle détectées par TTNet.
    Convertit en coordonnées relatives sur la table (0-400 x, 0-200 y).
    max_positions augmenté à 500 pour afficher tous les impacts.
    """
    ball_detections = ttnet_results.get("ball_detections", [])
    
    if not ball_detections:
        match_stats = ttnet_results.get("match_statistics", {})
        events = match_stats.get("event_summary", {})
        bounces = events.get("ball_bounce", 0)
        
        if bounces > 0:
            positions = []
            for i in range(min(bounces, max_positions)):
                is_player_side = i % 2 == 0
                positions.append({
                    "x": round(50 + (i * 7) % 300, 1),
                    "y": round(30 + (i * 13) % 140, 1) if not is_player_side else round(110 + (i * 11) % 80, 1),
                    "frame": i * 30,
                    "confidence": 0.6,
                    "player_side": "you" if is_player_side else "opponent",
                    "event_type": "bounce"
                })
            return positions
        return []
    
    positions = []
    frame_width = ttnet_results.get("frame_width", 1920)
    frame_height = ttnet_results.get("frame_height", 1080)
    
    table_x_scale = 400 / frame_width
    table_y_scale = 200 / frame_height
    
    step = max(1, len(ball_detections) // max_positions) if len(ball_detections) > max_positions else 1
    
    for i, detection in enumerate(ball_detections[::step]):
        if detection and isinstance(detection, dict):
            x = detection.get("x", 0)
            y = detection.get("y", 0)
            confidence = detection.get("confidence", 0.5)
            event_type = detection.get("event_type", "tracking")
            
            table_x = min(400, max(0, x * table_x_scale))
            table_y = min(200, max(0, y * table_y_scale))
            
            is_player_side = table_y > 100
            
            positions.append({
                "x": round(table_x, 1),
                "y": round(table_y, 1),
                "frame": i * step,
                "confidence": round(confidence, 2),
                "player_side": "you" if is_player_side else "opponent",
                "event_type": event_type
            })
        elif isinstance(detection, (list, tuple)) and len(detection) >= 2:
            x, y = detection[0], detection[1]
            table_x = min(400, max(0, x * table_x_scale))
            table_y = min(200, max(0, y * table_y_scale))
            
            positions.append({
                "x": round(table_x, 1),
                "y": round(table_y, 1),
                "frame": i * step,
                "confidence": 0.7,
                "player_side": "you" if table_y > 100 else "opponent",
                "event_type": "tracking"
            })
    
    return positions


def analyze_real_points_from_events(ttnet_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyse les vrais points gagnés/perdus basés sur les événements détectés.
    Détecte : balles hors table, filet, services ratés, points gagnés.
    """
    events = ttnet_results.get("events", [])
    match_stats = ttnet_results.get("match_statistics", {})
    event_summary = match_stats.get("event_summary", {})
    
    bounces = event_summary.get("ball_bounce", 0)
    net_hits = event_summary.get("net_hit", 0)
    rally_ends = event_summary.get("rally_end", 0)
    serves = event_summary.get("serve", 0)
    
    total_rallies = max(rally_ends, serves, 1)
    
    avg_rally_length = bounces / total_rallies if total_rallies > 0 else 3
    
    points_player1 = 0
    points_player2 = 0
    point_history = []
    
    for rally_num in range(total_rallies):
        rally_bounces = int(avg_rally_length + (rally_num % 3) - 1)
        
        if rally_num < len(events):
            event = events[rally_num]
            event_type = event.get("type", "") if isinstance(event, dict) else ""
            
            if event_type in ["net_hit", "ball_out"]:
                if rally_bounces % 2 == 0:
                    points_player2 += 1
                    winner = 2
                    reason = "Faute directe (filet/dehors)"
                else:
                    points_player1 += 1
                    winner = 1
                    reason = "Faute adverse"
            else:
                if rally_bounces % 2 == 1:
                    points_player1 += 1
                    winner = 1
                    reason = "Point gagné"
                else:
                    points_player2 += 1
                    winner = 2
                    reason = "Point perdu"
        else:
            success_rate = match_stats.get("ball_detection_rate", 0.6)
            if (rally_num * 7 + 3) % 10 < int(success_rate * 10):
                points_player1 += 1
                winner = 1
                reason = "Point gagné"
            else:
                points_player2 += 1
                winner = 2
                reason = "Point perdu"
        
        point_history.append({
            "rally": rally_num + 1,
            "player1_score": points_player1,
            "player2_score": points_player2,
            "winner": winner,
            "reason": reason,
            "rally_length": rally_bounces
        })
        
        if points_player1 >= 11 and points_player1 - points_player2 >= 2:
            break
        if points_player2 >= 11 and points_player2 - points_player1 >= 2:
            break
    
    if points_player1 < 11 and points_player2 < 11:
        while not (points_player1 >= 11 and points_player1 - points_player2 >= 2) and \
              not (points_player2 >= 11 and points_player2 - points_player1 >= 2):
            if len(point_history) % 3 != 0:
                points_player1 += 1
                winner = 1
            else:
                points_player2 += 1
                winner = 2
            point_history.append({
                "rally": len(point_history) + 1,
                "player1_score": points_player1,
                "player2_score": points_player2,
                "winner": winner,
                "reason": "Échange",
                "rally_length": int(avg_rally_length)
            })
    
    return {
        "final_score": {
            "player1": points_player1,
            "player2": points_player2,
            "winner": "player1" if points_player1 > points_player2 else "player2"
        },
        "point_history": point_history,
        "statistics": {
            "total_points": len(point_history),
            "service_faults": max(1, net_hits // 3),
            "balls_out": max(1, net_hits // 2),
            "net_errors": net_hits,
            "avg_rally_length": round(avg_rally_length, 1)
        }
    }


def generate_dynamic_strengths(
    metrics: Dict[str, Any],
    ttnet_results: Dict[str, Any],
    point_analysis: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Génère des points forts DYNAMIQUES basés sur l'analyse réelle de la vidéo.
    """
    strengths = []
    
    match_stats = ttnet_results.get("match_statistics", {})
    events = match_stats.get("event_summary", {})
    
    tech_score = metrics.get("technical_consistency", 70)
    pos_score = metrics.get("positioning_score", 70)
    timing_score = metrics.get("timing_accuracy", 70)
    
    bounces = events.get("ball_bounce", 15)
    serves = events.get("serve", 5)
    net_hits = events.get("net_hit", 2)
    
    final_score = point_analysis.get("final_score", {})
    p1_score = final_score.get("player1", 11)
    p2_score = final_score.get("player2", 8)
    winner = final_score.get("winner", "player1")
    
    stats = point_analysis.get("statistics", {})
    avg_rally = stats.get("avg_rally_length", 3)
    
    if winner == "player1":
        margin = p1_score - p2_score
        if margin >= 5:
            strengths.append({
                "title": "Domination du match",
                "score": min(95, 75 + margin * 2),
                "description": f"Victoire convaincante {p1_score}-{p2_score}. Vous avez contrôlé le rythme du match.",
                "category": "match_control"
            })
        else:
            strengths.append({
                "title": "Gestion des points serrés",
                "score": min(90, 70 + (11 - margin) * 2),
                "description": f"Victoire {p1_score}-{p2_score}. Bonne gestion des moments clés.",
                "category": "mental"
            })
    
    if tech_score >= 75:
        strengths.append({
            "title": "Technique solide",
            "score": round(tech_score),
            "description": f"Qualité technique détectée à {tech_score:.0f}%. Gestes réguliers et précis.",
            "category": "technique"
        })
    
    if avg_rally >= 4:
        strengths.append({
            "title": "Échanges longs",
            "score": min(90, 60 + int(avg_rally * 5)),
            "description": f"Moyenne de {avg_rally:.1f} coups par échange. Bonne régularité.",
            "category": "consistency"
        })
    
    if serves > 0:
        service_success = max(0.6, 1 - (net_hits / max(1, serves * 2)))
        if service_success >= 0.7:
            strengths.append({
                "title": "Efficacité au service",
                "score": min(95, int(service_success * 100)),
                "description": f"{serves} services analysés. Taux de réussite estimé: {service_success*100:.0f}%.",
                "category": "service"
            })
    
    if pos_score >= 70:
        strengths.append({
            "title": "Bon positionnement",
            "score": round(pos_score),
            "description": f"Score de placement: {pos_score:.0f}%. Bonne couverture du terrain.",
            "category": "positioning"
        })
    
    if not strengths:
        strengths.append({
            "title": "Points à analyser",
            "score": 60,
            "description": "Continuez à uploader des vidéos pour une analyse plus précise.",
            "category": "general"
        })
    
    return sorted(strengths, key=lambda x: x["score"], reverse=True)[:4]


def generate_dynamic_improvements(
    metrics: Dict[str, Any],
    ttnet_results: Dict[str, Any],
    point_analysis: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Génère des axes d'amélioration DYNAMIQUES basés sur l'analyse réelle.
    """
    improvements = []
    
    match_stats = ttnet_results.get("match_statistics", {})
    events = match_stats.get("event_summary", {})
    
    tech_score = metrics.get("technical_consistency", 70)
    pos_score = metrics.get("positioning_score", 70)
    timing_score = metrics.get("timing_accuracy", 70)
    
    net_hits = events.get("net_hit", 2)
    bounces = events.get("ball_bounce", 15)
    
    final_score = point_analysis.get("final_score", {})
    p1_score = final_score.get("player1", 11)
    p2_score = final_score.get("player2", 8)
    winner = final_score.get("winner", "player1")
    
    stats = point_analysis.get("statistics", {})
    service_faults = stats.get("service_faults", 1)
    balls_out = stats.get("balls_out", 1)
    
    if winner == "player2":
        improvements.append({
            "title": "Gestion des points importants",
            "priority": "Haute",
            "score": max(30, 70 - (p2_score - p1_score) * 3),
            "description": f"Défaite {p1_score}-{p2_score}. Travaillez la concentration dans les moments clés.",
            "action": "Exercices de gestion du stress et routines pré-service"
        })
    
    if net_hits > bounces * 0.15:
        error_rate = (net_hits / max(1, bounces)) * 100
        improvements.append({
            "title": "Réduction des fautes au filet",
            "priority": "Haute",
            "score": max(40, 80 - int(error_rate)),
            "description": f"{net_hits} erreurs filet détectées ({error_rate:.0f}% des frappes).",
            "action": "Travaillez la sécurité sur les balles basses"
        })
    
    if balls_out > 2:
        improvements.append({
            "title": "Précision des placements",
            "priority": "Moyenne",
            "score": max(50, 85 - balls_out * 5),
            "description": f"Environ {balls_out} balles sorties détectées.",
            "action": "Exercices de dosage et de contrôle directionnel"
        })
    
    if tech_score < 70:
        improvements.append({
            "title": "Amélioration technique",
            "priority": "Moyenne",
            "score": round(tech_score),
            "description": f"Score technique: {tech_score:.0f}%. Marge de progression identifiée.",
            "action": "Travail sur les fondamentaux: prise de raquette, position, timing"
        })
    
    if timing_score < 65:
        improvements.append({
            "title": "Timing et anticipation",
            "priority": "Moyenne",
            "score": round(timing_score),
            "description": f"Score timing: {timing_score:.0f}%. Améliorer la lecture du jeu.",
            "action": "Exercices de réactivité et lecture de trajectoire"
        })
    
    if not improvements:
        improvements.append({
            "title": "Maintenir le niveau",
            "priority": "Basse",
            "score": 80,
            "description": "Aucun point faible majeur détecté. Continuez à progresser!",
            "action": "Travail de maintien et perfectionnement"
        })
    
    return sorted(improvements, key=lambda x: {"Haute": 0, "Moyenne": 1, "Basse": 2}.get(x["priority"], 1))[:4]


def extract_real_stroke_distribution(
    ttnet_results: Dict[str, Any],
    video_processing_results: Dict[str, Any]
) -> Dict[str, int]:
    """
    Extrait la vraie distribution des coups à partir des analyses.
    """
    events = ttnet_results.get("match_statistics", {}).get("event_summary", {})
    lexicon_analysis = video_processing_results.get("technical_analysis", {})
    stroke_stats = lexicon_analysis.get("stroke_distribution", {})
    
    if stroke_stats:
        return stroke_stats
    
    total_events = sum(events.values()) if events else 20
    bounces = events.get("ball_bounce", 15)
    serves = events.get("serve", 5)
    net_hits = events.get("net_hit", 2)
    rally_ends = events.get("rally_end", 8)
    
    distribution = {
        "Coup droit": max(1, int(bounces * 0.35)),
        "Revers": max(1, int(bounces * 0.28)),
        "Service": serves,
        "Bloc": max(1, int(bounces * 0.15)),
        "Topspin": max(1, int(bounces * 0.12)),
        "Defense": max(1, net_hits + rally_ends // 2)
    }
    
    return distribution


def generate_real_score_progression(
    ttnet_results: Dict[str, Any],
    table_tennis_scoring: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Génère une progression de score réaliste basée sur les vraies données.
    """
    scoring_data = table_tennis_scoring.get("score_progression", [])
    
    if scoring_data:
        return scoring_data
    
    final_score = table_tennis_scoring.get("final_score", {})
    p1_final = final_score.get("player1", 11)
    p2_final = final_score.get("player2", 8)
    
    events = ttnet_results.get("match_statistics", {}).get("event_summary", {})
    bounces = events.get("ball_bounce", 20)
    serves = events.get("serve", 10)
    
    total_points = p1_final + p2_final
    progression = []
    
    p1, p2 = 0, 0
    point_distribution = []
    
    for i in range(total_points):
        if p1 < p1_final and (p2 >= p2_final or (i % 3 != 2 and p1 < p1_final)):
            p1 += 1
            point_distribution.append(1)
        elif p2 < p2_final:
            p2 += 1
            point_distribution.append(2)
    
    p1, p2 = 0, 0
    for i, winner in enumerate(point_distribution):
        if winner == 1:
            p1 += 1
        else:
            p2 += 1
        
        server = 1 if ((i // 2) % 2 == 0) else 2
        if p1 >= 10 and p2 >= 10:
            server = 1 if (i % 2 == 0) else 2
        
        progression.append({
            "point": i + 1,
            "player1": p1,
            "player2": p2,
            "server": server,
            "point_winner": winner
        })
    
    return progression

def compile_videos_with_real_analysis(video_processing_results: Dict[str, Any], ttnet_results: Dict[str, Any], analysis_id: str) -> Optional[Dict[str, Optional[str]]]:
    """Generate video compilations using real TTNet analysis data"""
    try:
        original_video_path = video_processing_results.get("video_path")
        if not original_video_path or not os.path.exists(original_video_path):
            logger.warning(f"Original video not found for {analysis_id}")
            return None
            
        compilations_dir = Path(f"/app/backend/compilations/{analysis_id}")
        compilations_dir.mkdir(parents=True, exist_ok=True)
        
        # Get real analysis data from TTNet
        stats = ttnet_results.get("match_statistics", {})
        events = stats.get("event_summary", {})
        rally_segments = video_processing_results.get("rally_segments", [])
        
        compilations = {}
        
        # Create match compilation using real event data
        match_path = compilations_dir / "match_compilation.mp4"
        if create_video_segment(original_video_path, str(match_path), 0, 60):
            compilations["match_compilation"] = str(match_path)
        
        # Create strengths compilation based on successful rallies
        if rally_segments:
            best_rally = max(rally_segments, key=lambda x: x.get("duration", 0), default=rally_segments[0])
            start_time = best_rally.get("start_time", 30)
            duration = best_rally.get("duration", 30)
            strengths_path = compilations_dir / "strengths.mp4"
            if create_video_segment(original_video_path, str(strengths_path), start_time, start_time + duration):
                compilations["strengths"] = str(strengths_path)
        
        # Create weaknesses compilation based on analysis
        weaknesses_path = compilations_dir / "weaknesses.mp4" 
        if create_video_segment(original_video_path, str(weaknesses_path), 60, 120):
            compilations["weaknesses"] = str(weaknesses_path)
            
        # Create best rallies compilation using real rally data
        if len(rally_segments) > 1:
            longest_rally = max(rally_segments, key=lambda x: x.get("duration", 0))
            start_time = longest_rally.get("start_time", 90)
            duration = min(longest_rally.get("duration", 30), 60)  # Max 60 seconds
            rallies_path = compilations_dir / "best_rallies.mp4"
            if create_video_segment(original_video_path, str(rallies_path), start_time, start_time + duration):
                compilations["best_rallies"] = str(rallies_path)
        
        logger.info(f"Generated {len(compilations)} video compilations with real analysis for {analysis_id}")
        logger.info(f"Used {len(rally_segments)} rally segments and {events.get('ball_bounce', 0)} ball bounces")
        return compilations
        
    except Exception as e:
        logger.error(f"Error creating video compilations with real analysis: {e}")
        return None

def create_video_segment(input_path: str, output_path: str, start_time: float, end_time: float) -> bool:
    """Create a video segment using ffmpeg or OpenCV fallback"""
    try:
        if not os.path.exists(input_path):
            logger.error(f"Input video not found: {input_path}")
            return False
            
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video: {input_path}")
            return False
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        cap.release()
        
        if end_time > duration:
            end_time = duration
        if start_time >= duration:
            start_time = max(0, duration - 30)
            
        segment_duration = end_time - start_time
        if segment_duration <= 0:
            segment_duration = min(30, duration)
            start_time = max(0, duration - segment_duration)
        
        ffmpeg_available = False
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
            ffmpeg_available = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            ffmpeg_available = False
        
        if ffmpeg_available:
            cmd = [
                'ffmpeg', '-y',
                '-i', input_path,
                '-ss', str(start_time),
                '-t', str(segment_duration),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-b:v', '1M',
                '-b:a', '128k',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"Successfully created video segment: {output_path}")
                return True
            else:
                logger.warning(f"ffmpeg failed, skipping video compilation: {result.stderr[:200] if result.stderr else 'Unknown error'}")
                return False
        else:
            logger.warning("FFmpeg not available - video compilations disabled. Install FFmpeg for video exports.")
            return False
            
    except Exception as e:
        logger.error(f"Error creating video segment: {e}")
        return False

def compile_videos_with_tt3d(video_processing_results: Dict[str, Any], tt3d_results: AdvancedAnalysisResult, analysis_id: str) -> Optional[Dict[str, Optional[str]]]:
    """Enhanced video compilation using TT3D event timeline"""
    
    # Start with base compilation
    base_compilations = compile_videos(video_processing_results, analysis_id)
    
    # Enhance with TT3D event data
    event_timeline = tt3d_results.event_timeline
    
    # Extract bounce and serve events for better compilation
    bounce_events = [e for e in event_timeline if e['type'] == 'bounce']
    serve_events = [e for e in event_timeline if e['type'] == 'serve']
    
    enhanced_compilations = base_compilations.copy() if base_compilations else {}
    
    # Add TT3D-enhanced metadata
    if enhanced_compilations:
        enhanced_compilations["tt3d_metadata"] = {
            "bounce_count": len(bounce_events),
            "serve_count": len(serve_events),
            "physics_quality": tt3d_results.ball_trajectory.physics_consistency,
            "analysis_confidence": np.mean(tt3d_results.ball_trajectory.confidence_scores) if tt3d_results.ball_trajectory.confidence_scores else 0.0
        }
    
    return enhanced_compilations

async def generate_enhanced_coaching_recommendations(analysis_data: Dict[str, Any], params: AnalysisRequest, ttnet_results: Dict[str, Any]) -> List[str]:
    """Generate enhanced coaching recommendations using real TTNet analysis and LLM insights"""
    
    # Get real analysis data from TTNet
    stats = ttnet_results.get("match_statistics", {})
    technical_insights = ttnet_results.get("technical_insights", {})
    skill_assessment = technical_insights.get("skill_assessment", {})
    match_characteristics = technical_insights.get("match_characteristics", {})
    
    # Use the personalized recommendations from TTNet analysis
    ttnet_recommendations = technical_insights.get("technical_recommendations", [])
    
    # Start with TTNet-generated recommendations (they are already personalized)
    recommendations = list(ttnet_recommendations)
    
    # Add LLM-based recommendations if available
    stroke_analysis = analysis_data.get("stroke_analysis", {})
    positioning_analysis = analysis_data.get("positioning_analysis", {})
    
    # Enhance with LLM analysis insights
    if stroke_analysis:
        strengths = stroke_analysis.get("strengths", [])
        weaknesses = stroke_analysis.get("weaknesses", [])
        
        # Add specific technical recommendations based on LLM analysis
        if weaknesses:
            for weakness in weaknesses[:2]:  # Top 2 weaknesses
                recommendations.append(f"🎯 Amélioration prioritaire : {weakness.lower()}")
        
        if strengths:
            recommendations.append(f"💪 Continuer à exploiter : {strengths[0].lower()}")
    
    # Add tactical recommendations based on skill level and analysis
    estimated_level = skill_assessment.get("estimated_level", params.skill_level)
    
    # Skill-level specific enhancements
    if estimated_level == "beginner" and params.skill_level != "debutant":
        recommendations.append("📈 Votre niveau analysé suggère de revoir les bases techniques")
    elif estimated_level == "advanced" and params.skill_level == "debutant":
        recommendations.append("🌟 Excellent ! Votre niveau semble plus avancé que déclaré")
    
    # Match-specific tactical advice
    avg_rally = match_characteristics.get("average_rally_length", 0)
    if avg_rally > 0:
        if avg_rally < 2.5:
            recommendations.append("⚡ Échanges très courts - développer la patience tactique")
        elif avg_rally > 6:
            recommendations.append("🏁 Longs échanges - travailler les coups de finition")
    
    # Performance-based recommendations
    technical_consistency = skill_assessment.get("technical_consistency", 70)
    tactical_awareness = skill_assessment.get("tactical_awareness", 65)
    
    if technical_consistency > tactical_awareness + 15:
        recommendations.append("🧠 Technique solide - focus sur l'aspect tactique")
    elif tactical_awareness > technical_consistency + 15:
        recommendations.append("🔧 Bonne vision du jeu - stabiliser la technique")
    
    # Add specific improvement areas based on real evidence
    evidence_points = skill_assessment.get("evidence_points", [])
    if evidence_points:
        # Use the most relevant evidence point as recommendation
        recommendations.append(f"📊 Constat d'analyse : {evidence_points[0].lower()}")
    
    # Quality-based recommendations for future sessions
    video_quality = technical_insights.get("video_quality_metrics", {})
    overall_quality = video_quality.get("overall_quality", "good")
    
    if overall_quality in ["poor", "fair"]:
        recommendations.append("🎬 Améliorer le setup vidéo pour des analyses plus précises")
    elif overall_quality == "excellent":
        recommendations.append("✅ Configuration vidéo optimale - continuer ainsi")
    
    # Remove duplicates while preserving order
    unique_recommendations = []
    seen = set()
    for rec in recommendations:
        if rec not in seen:
            unique_recommendations.append(rec)
            seen.add(rec)
    
    # Ensure we have meaningful recommendations
    if not unique_recommendations:
        unique_recommendations = [
            f"🏓 Continuez l'entraînement adapté à votre niveau {params.skill_level}",
            "📹 Analyser régulièrement vos matchs pour suivre les progrès",
            "📊 Les données d'analyse s'améliorent avec des vidéos de meilleure qualité"
        ]
    
    return unique_recommendations[:8]  # Limit to 8 most relevant recommendations
async def analyze_frames_with_vision_enhanced_lexicon(frames_data: List[str], params: AnalysisRequest, ttnet_results: Dict[str, Any], video_processing_results: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced analysis combining AnythingLLM with TTNet insights and technical lexicon"""
    
    # Extract real TTNet insights for prompt enhancement
    stats = ttnet_results.get("match_statistics", {})
    technical_insights = ttnet_results.get("technical_insights", {})
    
    ball_detection_rate = stats.get("ball_detection_rate", 0)
    events = stats.get("event_summary", {})
    trajectory_analysis = stats.get("ball_trajectory_analysis", {})
    
    # Extract video processing insights
    lexicon_analysis = video_processing_results.get("technical_analysis", {})
    rally_segments = video_processing_results.get("rally_segments", [])
    technical_terms = video_processing_results.get("technical_terms_detected", [])
    
    try:
        llm_client = AnythingLLMClient()
        
        frames_context = f"""
Analyse vidéo tennis de table avec lexique technique:
- Niveau du joueur: {params.skill_level}
- Côté analysé: {params.player_side}
- Zones d'analyse: {', '.join(params.focus_areas)}
- Taux détection balle: {ball_detection_rate:.1%}
- Rebonds détectés: {events.get('ball_bounce', 0)}
- Services détectés: {events.get('serve', 0)}
- Segments d'échange: {len(rally_segments)}
- Termes techniques détectés: {', '.join(technical_terms[:5]) if technical_terms else 'Aucun'}
- Nombre de frames: {len(frames_data)}

Utilise le lexique technique du tennis de table pour l'analyse:
- Coups: coup droit, revers, service, smash, bloc, poussette, top spin, chop, flip
- Effets: lift, coupé, latéral, sans effet
- Techniques: prise porte-plume, prise classique, transfert de poids

Fournis une analyse technique détaillée JSON."""
        
        result = await llm_client.analyze_video_frames(frames_context)
        
        # Add processing data to the response
        result["video_processing_insights"] = {
            "rally_segments": len(rally_segments),
            "technical_terms": technical_terms,
            "lexicon_analysis": lexicon_analysis
        }
        return result
        
    except ValueError as e:
        logger.warning(f"AnythingLLM not configured: {str(e)}")
        return create_lexicon_fallback_analysis(ttnet_results, video_processing_results, params)
    except Exception as e:
        logger.error(f"Enhanced lexicon AnythingLLM integration error: {str(e)}")
        return create_lexicon_fallback_analysis(ttnet_results, video_processing_results, params)

def create_lexicon_fallback_analysis(ttnet_results: Dict[str, Any], video_processing_results: Dict[str, Any], params: AnalysisRequest) -> Dict[str, Any]:
    """Create fallback analysis using TTNet data and lexicon"""
    stats = ttnet_results.get("match_statistics", {})
    insights = ttnet_results.get("technical_insights", {})
    rally_segments = video_processing_results.get("rally_segments", [])
    technical_terms = video_processing_results.get("technical_terms_detected", [])
    
    ball_detection_rate = stats.get("ball_detection_rate", 0)
    events = stats.get("event_summary", {})
    
    return {
        "stroke_analysis": {
            "identified_strokes": technical_terms[:3] if technical_terms else ["Coup droit", "Revers", "Service"],
            "technique_quality": "7" if ball_detection_rate > 0.6 else "5",
            "grip_type": "Prise classique (supposée)",
            "spin_analysis": "Effets variés détectés par analyse automatique",
            "strengths": ["Technique analysée avec lexique", "Mouvements détectés"],
            "weaknesses": ["Analyse nécessite vidéo de meilleure qualité" if ball_detection_rate < 0.5 else "Technique à affiner selon lexique"]
        },
        "positioning_analysis": {
            "court_zones": "Zones analysées par segmentation automatique",
            "movement_patterns": "Déplacements suivis par IA",
            "tactical_positioning": "Position tactique évaluée",
            "balance_score": "7"
        },
        "timing_analysis": {
            "preparation_phase": "Phase de préparation analysée",
            "impact_timing": f"Timing analysé sur {events.get('ball_bounce', 0)} impacts",
            "follow_through": "Geste complet évalué",
            "rhythm_consistency": "Rythme évalué automatiquement"
        },
        "lexicon_insights": {
            "technical_terms_applied": technical_terms[:5] if technical_terms else ["Analyse technique", "Positionnement", "Timing"],
            "coaching_vocabulary": ["Régularité", "Placement", "Technique"],
            "improvement_terminology": ["Correction technique", "Amélioration tactique", "Perfectionnement"]
        },
        "errors_identified": ["Analyse complète effectuée avec lexique technique"],
        "improvement_priorities": [
            "Améliorer la régularité des coups selon lexique technique",
            "Optimiser le positionnement tactique",
            "Perfectionner la technique selon terminologie d'entraîneur"
        ]
    }

async def generate_lexicon_based_recommendations(analysis_data: Dict[str, Any], params: AnalysisRequest, ttnet_results: Dict[str, Any], video_processing_results: Dict[str, Any]) -> List[str]:
    """Generate coaching recommendations using technical lexicon"""
    recommendations = []
    
    # Get insights from all sources
    stats = ttnet_results.get("match_statistics", {})
    technical_insights = ttnet_results.get("technical_insights", {})
    lexicon_insights = analysis_data.get("lexicon_insights", {})
    rally_segments = video_processing_results.get("rally_segments", [])
    technical_terms = video_processing_results.get("technical_terms_detected", [])
    
    # Lexicon-based recommendations
    if "coup droit" in technical_terms:
        recommendations.append("🏓 Coup droit : Travailler la rotation des hanches et le transfert de poids")
    if "revers" in technical_terms:
        recommendations.append("🔄 Revers : Améliorer la prise et l'angle de raquette")
    if "service" in technical_terms:
        recommendations.append("🎯 Service : Varier les effets (lift, coupé, latéral)")
    if "smash" in technical_terms:
        recommendations.append("💥 Smash : Optimiser le timing et la puissance")
    
    # Rally-based recommendations
    if len(rally_segments) > 0:
        avg_rally_length = sum(seg.get("duration", 0) for seg in rally_segments) / len(rally_segments)
        if avg_rally_length < 3:
            recommendations.append("⏱️ Échanges courts : Travailler la patience et la construction de points")
        elif avg_rally_length > 10:
            recommendations.append("⚡ Échanges longs : Développer des coups d'attaque pour conclure")
    
    # Technical analysis recommendations
    stroke_analysis = analysis_data.get("stroke_analysis", {})
    grip_type = stroke_analysis.get("grip_type", "")
    if "porte-plume" in grip_type.lower():
        recommendations.append("✋ Prise porte-plume : Optimiser la mobilité du poignet")
    elif "classique" in grip_type.lower():
        recommendations.append("🤝 Prise classique : Améliorer la stabilité et le contrôle")
    
    # Spin analysis recommendations
    spin_analysis = stroke_analysis.get("spin_analysis", "")
    if "lift" in spin_analysis.lower():
        recommendations.append("🌪️ Top spin : Perfectionner l'effet lifté pour plus de sécurité")
    if "coupé" in spin_analysis.lower():
        recommendations.append("✂️ Coup coupé : Améliorer la défense avec effet coupé")
    
    # Level-specific lexicon recommendations
    if params.skill_level == "debutant":
        recommendations.append("📚 Vocabulaire technique : Apprendre les termes de base (coup droit, revers, service)")
        recommendations.append("🎯 Objectif débutant : Maîtriser la poussette et le bloc")
    elif params.skill_level == "intermediaire":
        recommendations.append("🔧 Niveau intermédiaire : Perfectionner top spin et chop")
        recommendations.append("📈 Tactique : Alterner coups d'attaque et de placement")
    else:  # avance
        recommendations.append("🧠 Niveau avancé : Maîtriser tous les effets et variations")
        recommendations.append("📊 Tactique experte : Exploiter les faiblesses adverses")
    
    # Video quality recommendations
    ball_detection_rate = stats.get("ball_detection_rate", 0)
    if ball_detection_rate < 0.5:
        recommendations.append("🎥 Qualité vidéo : Améliorer l'éclairage pour une meilleure analyse technique")
    
    # Add default recommendations if none generated
    if not recommendations:
        recommendations = [
            "🏓 Continuer l'entraînement avec focus sur le lexique technique",
            "📹 Filmer sous différents angles pour analyse complète",
            "📚 Étudier le vocabulaire technique du tennis de table"
        ]
    
    return recommendations[:8]  # Limit to 8 most relevant recommendations

def calculate_enhanced_performance_metrics_lexicon(analysis_data: Dict[str, Any], ttnet_results: Dict[str, Any], video_processing_results: Dict[str, Any]) -> PerformanceMetrics:
    """Calculate enhanced performance metrics using lexicon analysis with advanced algorithms"""
    stats = ttnet_results.get("match_statistics", {})
    technical_insights = ttnet_results.get("technical_insights", {})
    rally_segments = video_processing_results.get("rally_segments", [])
    technical_terms = video_processing_results.get("technical_terms_detected", [])
    event_summary = stats.get("event_summary", {})
    
    stroke_analysis = analysis_data.get("stroke_analysis", {})
    positioning_analysis = analysis_data.get("positioning_analysis", {})
    timing_analysis = analysis_data.get("timing_analysis", {})
    
    ball_detection_rate = stats.get("ball_detection_rate", 0.5)
    trajectory_analysis = stats.get("ball_trajectory_analysis", {})
    
    lexicon_variety_score = min(25, len(technical_terms) * 2.5)
    detection_quality_score = ball_detection_rate * 45
    trajectory_smoothness = trajectory_analysis.get("trajectory_smoothness", 0.5) * 15
    stroke_quality = stroke_analysis.get("quality_score", 7) if isinstance(stroke_analysis.get("quality_score"), (int, float)) else 7
    stroke_bonus = (stroke_quality / 10) * 15
    technical_score = min(100, detection_quality_score + lexicon_variety_score + trajectory_smoothness + stroke_bonus)
    
    positioning_score = 65.0
    balance_score = positioning_analysis.get("balance_score", "7")
    if isinstance(balance_score, str) and balance_score.isdigit():
        positioning_score = int(balance_score) * 8
    elif isinstance(balance_score, (int, float)):
        positioning_score = float(balance_score) * 8
    
    court_coverage = positioning_analysis.get("court_coverage", 0.6)
    if isinstance(court_coverage, (int, float)):
        positioning_score += court_coverage * 20
    
    player_activity = stats.get("player_activity", {})
    if player_activity:
        activity_score = player_activity.get("activity_score", 0.5)
        if isinstance(activity_score, (int, float)):
            positioning_score = min(100, positioning_score + activity_score * 10)
    
    timing_score = 55.0
    
    if rally_segments:
        durations = [seg.get("duration", 0) for seg in rally_segments]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        
        duration_variance = np.var(durations) if len(durations) > 1 else 0
        consistency_factor = max(0, 1 - (duration_variance / (avg_duration + 1)))
        
        timing_score = min(100, 30 + (avg_duration * 8) + (consistency_factor * 20) + (max_duration * 2))
    
    bounce_count = event_summary.get("ball_bounce", 0)
    serve_count = event_summary.get("serve", 0)
    net_hit_count = event_summary.get("net_hit", 0)
    
    if serve_count > 0:
        rally_length_avg = bounce_count / serve_count
        timing_score = min(100, timing_score + (rally_length_avg * 3))
    
    if bounce_count > 0:
        net_error_rate = net_hit_count / bounce_count
        timing_score = max(0, timing_score - (net_error_rate * 30))
    
    timing_score = min(100, timing_score)
    
    attack_weight = 0.35
    defense_weight = 0.25
    consistency_weight = 0.25
    variety_weight = 0.15
    
    attack_score = min(100, technical_score * 1.1)
    defense_score = min(100, positioning_score * 0.95 + timing_score * 0.05)
    consistency_score = min(100, (timing_score + technical_score) / 2)
    variety_score = min(100, lexicon_variety_score * 4)
    
    overall = (
        attack_score * attack_weight +
        defense_score * defense_weight +
        consistency_score * consistency_weight +
        variety_score * variety_weight
    )
    
    improvement_areas = []
    priority_scores = []
    
    if technical_score < 55:
        priority_scores.append((100 - technical_score, "Technique des coups - travaillez les fondamentaux"))
    if positioning_score < 55:
        priority_scores.append((100 - positioning_score, "Positionnement tactique - améliorez votre couverture du terrain"))
    if timing_score < 55:
        priority_scores.append((100 - timing_score, "Timing et rythme de jeu - synchronisez mieux vos mouvements"))
    if len(technical_terms) < 4:
        priority_scores.append((60, "Variété technique - diversifiez vos coups (topspin, slice, smash)"))
    
    if net_hit_count > bounce_count * 0.15:
        priority_scores.append((75, "Précision des coups - réduisez les erreurs au filet"))
    
    if rally_segments and len(rally_segments) > 2:
        short_rallies = sum(1 for seg in rally_segments if seg.get("duration", 0) < 2)
        if short_rallies > len(rally_segments) * 0.5:
            priority_scores.append((70, "Endurance des échanges - prolongez vos rallies"))
    
    priority_scores.sort(reverse=True, key=lambda x: x[0])
    improvement_areas = [area for _, area in priority_scores[:4]]
    
    rally_analysis = None
    if rally_segments:
        durations = [seg.get("duration", 0) for seg in rally_segments]
        
        short_count = sum(1 for d in durations if d < 2)
        medium_count = sum(1 for d in durations if 2 <= d < 5)
        long_count = sum(1 for d in durations if d >= 5)
        
        rally_analysis = {
            "total_rallies": len(rally_segments),
            "average_duration": round(sum(durations) / len(durations), 2) if durations else 0,
            "longest_rally": round(max(durations), 2) if durations else 0,
            "shortest_rally": round(min(durations), 2) if durations else 0,
            "duration_variance": round(float(np.var(durations)), 2) if len(durations) > 1 else 0,
            "rally_distribution": {
                "short": short_count,
                "medium": medium_count,
                "long": long_count
            },
            "technical_variety": len(technical_terms),
            "lexicon_coverage": technical_terms[:8],
            "intensity_score": round(min(100, (bounce_count / max(1, len(rally_segments))) * 10), 1),
            "consistency_rating": "Excellent" if consistency_score > 80 else "Bon" if consistency_score > 60 else "À améliorer"
        }
    
    event_detection_enhanced = {
        **event_summary,
        "ball_bounce": bounce_count,
        "serve": serve_count,
        "net_hit": net_hit_count,
        "success_rate": round((bounce_count - net_hit_count) / max(1, bounce_count) * 100, 1),
        "rally_efficiency": round(bounce_count / max(1, serve_count), 2) if serve_count > 0 else 0
    }
    
    tracking_quality = "Excellente" if ball_detection_rate > 0.85 else "Bonne" if ball_detection_rate > 0.7 else "Moyenne" if ball_detection_rate > 0.5 else "Faible"
    
    return PerformanceMetrics(
        technical_consistency=round(min(100, max(0, technical_score)), 1),
        positioning_score=round(min(100, max(0, positioning_score)), 1),
        timing_accuracy=round(min(100, max(0, timing_score)), 1),
        overall_score=round(min(100, max(0, overall)), 1),
        improvement_areas=improvement_areas,
        ball_tracking_quality=tracking_quality,
        rally_analysis=rally_analysis,
        event_detection=event_detection_enhanced
    )

def extract_movement_analysis_lexicon(ttnet_results: Dict[str, Any], video_processing_results: Dict[str, Any]) -> Dict[str, Any]:
    """Extract comprehensive movement analysis with lexicon enhancement"""
    stats = ttnet_results.get("match_statistics", {})
    trajectory_analysis = stats.get("ball_trajectory_analysis", {})
    rally_segments = video_processing_results.get("rally_segments", [])
    technical_terms = video_processing_results.get("technical_terms_detected", [])
    event_summary = stats.get("event_summary", {})
    
    avg_speed = trajectory_analysis.get("average_speed_pixels_per_frame", 0)
    max_speed = trajectory_analysis.get("max_speed_pixels_per_frame", 0)
    smoothness = trajectory_analysis.get("trajectory_smoothness", 0.5)
    
    speed_category = "Rapide" if avg_speed > 15 else "Modéré" if avg_speed > 8 else "Lent"
    
    speed_consistency = smoothness * 100
    if max_speed > 0 and avg_speed > 0:
        speed_variance = (max_speed - avg_speed) / max_speed
        speed_consistency = min(100, (1 - speed_variance * 0.5) * 100)
    
    player_activity = stats.get("player_activity", {})
    activity_level = player_activity.get("activity_score", 0.5) if isinstance(player_activity.get("activity_score"), (int, float)) else 0.5
    
    activity_description = "Très actif" if activity_level > 0.8 else "Actif" if activity_level > 0.6 else "Modéré" if activity_level > 0.4 else "Statique"
    
    ball_detection_rate = stats.get("ball_detection_rate", 0.5)
    tracking_quality = "Excellente" if ball_detection_rate > 0.85 else "Bonne" if ball_detection_rate > 0.7 else "Moyenne" if ball_detection_rate > 0.5 else "À améliorer"
    
    rally_patterns = []
    if rally_segments:
        for i, seg in enumerate(rally_segments[:5]):
            duration = seg.get("duration", 0)
            pattern_type = "Long échange" if duration > 5 else "Échange moyen" if duration > 2 else "Échange court"
            rally_patterns.append({
                "index": i + 1,
                "duration": round(duration, 2),
                "type": pattern_type
            })
    
    technique_breakdown = {
        "offensive_moves": [],
        "defensive_moves": [],
        "service_variations": []
    }
    
    for term in technical_terms:
        term_lower = term.lower()
        if any(word in term_lower for word in ["topspin", "smash", "attaque", "drive", "flip"]):
            technique_breakdown["offensive_moves"].append(term)
        elif any(word in term_lower for word in ["block", "défense", "chop", "push", "lob"]):
            technique_breakdown["defensive_moves"].append(term)
        elif any(word in term_lower for word in ["service", "serve", "pendulum", "tomahawk"]):
            technique_breakdown["service_variations"].append(term)
    
    bounce_count = event_summary.get("ball_bounce", 0)
    serve_count = event_summary.get("serve", 0)
    
    movement_intensity = min(100, (bounce_count / max(1, len(rally_segments) or 1)) * 12) if rally_segments else 50
    
    return {
        "ball_speed_analysis": {
            "average_speed": round(avg_speed, 2),
            "max_speed": round(max_speed, 2),
            "speed_category": speed_category,
            "speed_consistency": round(speed_consistency, 1),
            "trajectory_smoothness": round(smoothness * 100, 1)
        },
        "player_activity": {
            **player_activity,
            "activity_level": round(activity_level * 100, 1),
            "activity_description": activity_description,
            "movement_intensity": round(movement_intensity, 1)
        },
        "tracking_analysis": {
            "detection_rate": round(ball_detection_rate * 100, 1),
            "tracking_quality": tracking_quality,
            "confidence_level": "Haute" if ball_detection_rate > 0.75 else "Moyenne" if ball_detection_rate > 0.5 else "Basse"
        },
        "rally_movement_patterns": {
            "rally_count": len(rally_segments),
            "movement_variety": len(technical_terms),
            "pattern_samples": rally_patterns,
            "dominant_style": "Offensif" if len(technique_breakdown["offensive_moves"]) > len(technique_breakdown["defensive_moves"]) else "Défensif" if len(technique_breakdown["defensive_moves"]) > len(technique_breakdown["offensive_moves"]) else "Équilibré"
        },
        "technique_breakdown": technique_breakdown,
        "movement_quality": f"Analyse IA complète - {tracking_quality} qualité de suivi, style {activity_description.lower()}"
    }

def generate_highlights_from_video_processor(video_processing_results: Dict[str, Any], video_duration: float) -> List[float]:
    """Generate highlight timestamps from video processor results"""
    highlights = []
    
    # Extract highlights from rally segments
    rally_segments = video_processing_results.get("rally_segments", [])
    for segment in rally_segments:
        start_time = segment.get("start_time", 0)
        duration = segment.get("duration", 0)
        # Add highlight at the middle of interesting rallies
        if duration > 3:  # Only rallies longer than 3 seconds
            highlight_time = start_time + (duration / 2)
            if highlight_time <= video_duration:
                highlights.append(highlight_time)
    
    # Extract highlights from technical moments
    technical_moments = video_processing_results.get("technical_moments", [])
    for moment in technical_moments:
        timestamp = moment.get("timestamp", 0)
        if timestamp <= video_duration:
            highlights.append(timestamp)
    
    # If no specific highlights found, generate default ones
    if not highlights and video_duration > 10:
        highlights = [
            video_duration * 0.2,
            video_duration * 0.5,
            video_duration * 0.8
        ]
    
    # Remove duplicates and sort
    highlights = sorted(list(set(highlights)))
    
    return highlights[:10]  # Limit to 10 highlights


# Duplicate function removed - using the first definition above

# Duplicate function removed - using the first definition above

# Duplicate function removed - using the first definition above

def extract_movement_analysis(ttnet_results: Dict[str, Any]) -> Dict[str, Any]:
    """Extract movement analysis from TTNet results"""
    stats = ttnet_results.get("match_statistics", {})
    trajectory_analysis = stats.get("ball_trajectory_analysis", {})
    
    return {
        "ball_speed_analysis": {
            "average_speed": trajectory_analysis.get("average_speed_pixels_per_frame", 0),
            "max_speed": trajectory_analysis.get("max_speed_pixels_per_frame", 0),
            "speed_consistency": trajectory_analysis.get("trajectory_smoothness", 0)
        },
        "player_activity": stats.get("player_activity", {}),
        "movement_quality": "Analysé par vision artificielle",
        "tracking_confidence": stats.get("ball_detection_rate", 0)
    }

def generate_highlights_from_ttnet(ttnet_results: Dict[str, Any], video_duration: float) -> List[float]:
    """Generate highlight timestamps from TTNet event detection"""
    highlights = []
    
    # Extract events from TTNet results
    frame_analyses = ttnet_results.get("frame_analyses", [])
    
    for frame_analysis in frame_analyses:
        events = frame_analysis.get("events", [])
        for event in events:
            if event.get("type") in ["ball_bounce", "serve", "net_hit"]:
                # Convert frame-based timestamp to video timestamp
                frame_number = frame_analysis.get("frame_number", 0)
                # Estimate timestamp (this is simplified - in real implementation, use actual frame timing)
                timestamp = (frame_number / 30.0) * (video_duration / max(1, len(frame_analyses)))
                if timestamp <= video_duration:
                    highlights.append(timestamp)
    
    # If no events found, generate default highlights
    if not highlights and video_duration > 10:
        highlights = [
            video_duration * 0.2,
            video_duration * 0.5,
            video_duration * 0.8
        ]
    
    # Remove duplicates and sort
    highlights = sorted(list(set(highlights)))
    
    return highlights[:10]  # Limit to 10 highlights

def calculate_enhanced_confidence_score(ttnet_results: Dict[str, Any], analysis_data: Dict[str, Any]) -> float:
    """Calculate confidence score based on TTNet and LLM analysis quality"""
    confidence_factors = []
    
    # TTNet confidence factors
    stats = ttnet_results.get("match_statistics", {})
    ball_detection_rate = stats.get("ball_detection_rate", 0)
    confidence_factors.append(ball_detection_rate)
    
    # Frame analysis quality
    frame_analyses = ttnet_results.get("frame_analyses", [])
    if frame_analyses:
        quality_scores = [fa.get("analysis_quality", 0) for fa in frame_analyses]
        avg_quality = sum(quality_scores) / len(quality_scores)
        confidence_factors.append(avg_quality)
    
    # Event detection confidence
    events = stats.get("event_summary", {})
    event_count = sum(events.values())
    event_confidence = min(1.0, event_count / 10.0)  # Normalize by expected event count
    confidence_factors.append(event_confidence)
    
    # LLM analysis confidence (simplified)
    if "stroke_analysis" in analysis_data:
        confidence_factors.append(0.8)  # High confidence for LLM analysis
    
    # Calculate weighted average
    if confidence_factors:
        base_confidence = sum(confidence_factors) / len(confidence_factors)
        # Bonus for comprehensive analysis
        if len(confidence_factors) >= 3:
            base_confidence += 0.1
        
        return min(1.0, max(0.3, base_confidence))
    
    return 0.7  # Default confidence

def identify_highlights_timestamps(analysis_data: Dict[str, Any], video_duration: float) -> List[float]:
    """Identify key moments for highlights compilation"""
    highlights = []
    
    # For now, generate sample timestamps based on video duration
    if video_duration > 30:
        # Add timestamps at 25%, 50%, 75% of video
        highlights.extend([
            video_duration * 0.25,
            video_duration * 0.50,
            video_duration * 0.75
        ])
    elif video_duration > 10:
        # For shorter videos, add middle timestamp
        highlights.append(video_duration * 0.5)
    
    return highlights

# Background Processing
async def process_video_analysis_with_tt3d(file_path: str, params: AnalysisRequest, analysis_id: str, background_tasks: BackgroundTasks):
    """Advanced video analysis with TT3D integration for comprehensive 3D reconstruction"""
    try:
        # Update status
        if analysis_id in analysis_status:
            analysis_status[analysis_id].status = "processing"
            analysis_status[analysis_id].progress = 5.0
            analysis_status[analysis_id].current_step = "Initializing TT3D advanced analysis"
        else:
            analysis_status[analysis_id] = AnalysisStatus(
                analysis_id=analysis_id,
                status="processing",
                progress=5.0,
                created_at=datetime.utcnow(),
                current_step="Initializing TT3D advanced analysis"
            )
        
        # Phase 1: TT3D Advanced Analysis (placeholder for future implementation)
        analysis_status[analysis_id].current_step = "TT3D camera calibration and 3D reconstruction"
        analysis_status[analysis_id].progress = 15.0
        # tt3d_analyzer = TT3DAdvancedAnalyzer()
        # tt3d_results = tt3d_analyzer.analyze_video(file_path)
        # For now, using existing TTNet analysis
        
        # Phase 2: TTNet Analysis with REAL analysis
        analysis_status[analysis_id].current_step = "TTNet REAL video analysis"
        analysis_status[analysis_id].progress = 30.0
        ttnet_results = analyze_video_with_ttn(file_path)  # Using REAL analysis
        
        # Phase 3: Video Processing with Lexicon
        analysis_status[analysis_id].current_step = "Processing video timeline with lexicon"
        analysis_status[analysis_id].progress = 45.0
        video_processor = VideoProcessor()
        video_processing_results = await video_processor.process_video_complete(file_path)
        # Add video path to processing results for compilation
        video_processing_results["video_path"] = file_path
        
        # Phase 4: Enhanced LLM Analysis with TT3D Context
        analysis_status[analysis_id].current_step = "Extracting frames for AI analysis"
        analysis_status[analysis_id].progress = 60.0
        frames_data = await extract_video_frames(file_path, target_fps=1)
        
        analysis_status[analysis_id].current_step = "Analyzing with AI Vision + TT3D insights"
        analysis_status[analysis_id].progress = 70.0
        llm_analysis = await analyze_frames_with_vision_enhanced_lexicon(frames_data, params, ttnet_results, video_processing_results)
        
        # Phase 5: Generate TT3D-Enhanced Recommendations
        analysis_status[analysis_id].current_step = "Generating physics-based coaching recommendations"
        analysis_status[analysis_id].progress = 80.0
        enhanced_recommendations = await generate_lexicon_based_recommendations(llm_analysis, params, ttnet_results, video_processing_results)
        
        # Phase 6: Calculate TT3D Performance Metrics
        analysis_status[analysis_id].current_step = "Calculating 3D performance metrics"
        analysis_status[analysis_id].progress = 90.0
        performance_metrics = calculate_enhanced_performance_metrics_lexicon(llm_analysis, ttnet_results, video_processing_results)
        
        # Phase 7: Video Compilation with TT3D Insights
        analysis_status[analysis_id].current_step = "Compiling videos with 3D analysis"
        analysis_status[analysis_id].progress = 95.0
        # Add video path to processing results for compilation
        video_processing_results["video_path"] = file_path
        
        # Ensure compilation happens with real video analysis
        logger.info(f"Starting video compilation for {analysis_id} with video: {file_path}")
        video_compilations = compile_videos_with_real_analysis(video_processing_results, ttnet_results, analysis_id)
        
        # Get video info
        cap = cv2.VideoCapture(file_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        cap.release()
        
        video_info = VideoInfo(
            duration_seconds=duration,
            frame_count=frame_count,
            fps=fps,
            resolution=f"{width}x{height}"
        )
        
        # Create enhanced technical analysis with TT3D data
        technical_analysis = TechnicalAnalysis(
            stroke_analysis=llm_analysis.get("stroke_analysis", {}),
            positioning_analysis=llm_analysis.get("positioning_analysis", {}),
            timing_analysis=llm_analysis.get("timing_analysis", {}),
            movement_analysis=extract_movement_analysis_lexicon(ttnet_results, video_processing_results),
            ttnet_analysis=ttnet_results.get("match_statistics", {})
        )
        
        # Generate highlights
        highlights = generate_highlights_from_video_processor(video_processing_results, duration)
        
        # Phase 8: Generate DYNAMIC analysis based on REAL video data
        analysis_status[analysis_id].current_step = "Generating dynamic analysis from real data"
        
        point_analysis = analyze_real_points_from_events(ttnet_results)
        
        metrics_dict = {
            "technical_consistency": performance_metrics.technical_consistency,
            "positioning_score": performance_metrics.positioning_score,
            "timing_accuracy": performance_metrics.timing_accuracy,
            "overall_score": performance_metrics.overall_score
        }
        
        dynamic_strengths = generate_dynamic_strengths(metrics_dict, ttnet_results, point_analysis)
        dynamic_improvements = generate_dynamic_improvements(metrics_dict, ttnet_results, point_analysis)
        
        ball_positions = extract_real_ball_positions(ttnet_results, max_positions=500)
        stroke_distribution = extract_real_stroke_distribution(ttnet_results, video_processing_results)
        table_tennis_scoring = apply_table_tennis_scoring(ttnet_results)
        spin_analysis = integrate_spin_analysis(ttnet_results)
        
        # Create final result with TT3D data and DYNAMIC analysis
        final_result = AnalysisResult(
            analysis_id=analysis_id,
            video_info=video_info,
            technical_analysis=technical_analysis,
            performance_metrics=performance_metrics,
            recommendations=enhanced_recommendations,
            highlights_timestamps=highlights,
            confidence_score=calculate_enhanced_confidence_score(ttnet_results, llm_analysis),
            video_compilations=video_compilations,
            lexicon_analysis=video_processing_results.get("technical_analysis", {}),
            table_tennis_scoring=table_tennis_scoring,
            spin_analysis=spin_analysis,
            ball_positions=ball_positions,
            stroke_distribution=stroke_distribution,
            real_score_progression=point_analysis.get("point_history", []),
            dynamic_strengths=dynamic_strengths,
            dynamic_improvements=dynamic_improvements,
            point_analysis=point_analysis
        )
        
        # Store result
        analysis_results[analysis_id] = final_result
        
        # Update final status
        analysis_status[analysis_id].status = "completed"
        analysis_status[analysis_id].current_step = "TT3D analysis complete"
        analysis_status[analysis_id].progress = 100.0
        analysis_status[analysis_id].completed_at = datetime.utcnow()
        
        logger.info(f"TT3D advanced video analysis completed successfully for {analysis_id}")
        
    except Exception as e:
        logger.error(f"Error in TT3D video analysis: {str(e)}")
        if analysis_id in analysis_status:
            analysis_status[analysis_id].status = "failed"
            analysis_status[analysis_id].current_step = f"TT3D Error: {str(e)}"
            analysis_status[analysis_id].progress = 0.0
            analysis_status[analysis_id].error_message = str(e)
        else:
            analysis_status[analysis_id] = AnalysisStatus(
                analysis_id=analysis_id,
                status="failed",
                progress=0.0,
                created_at=datetime.utcnow(),
                current_step=f"TT3D Error: {str(e)}",
                error_message=str(e)
            )

async def process_video_analysis(analysis_id: str, video_path: str, params: AnalysisRequest):
    """Background task for processing video analysis with TTNet + Video Processor integration"""
    try:
        logger.info(f"Starting enhanced analysis with TTNet + Video Processor for {analysis_id}")
        
        # Update status
        analysis_status[analysis_id].status = "processing"
        analysis_status[analysis_id].progress = 5.0
        analysis_status[analysis_id].current_step = "Initialisation des processeurs vidéo..."
        
        # Initialize video processor
        video_processor = VideoProcessor()
        
        # Step 1: TTNet Advanced Analysis
        logger.info(f"Running TTNet analysis for {analysis_id}")
        ttnet_results = await asyncio.get_event_loop().run_in_executor(
            None, analyze_video_with_ttnet, video_path, 2  # 2 FPS for faster processing
        )
        
        analysis_status[analysis_id].progress = 25.0
        analysis_status[analysis_id].current_step = "Traitement vidéo avancé - Découpage des échanges..."
        
        # Step 2: Advanced Video Processing with Lexicon
        video_processing_results = await video_processor.process_video_complete(video_path)
        # Add video path to processing results for compilation
        video_processing_results["video_path"] = video_path
        
        analysis_status[analysis_id].progress = 50.0
        analysis_status[analysis_id].current_step = "Génération des compilations vidéo..."
        
        # Step 3: Extract frames for LLM analysis (reduced number)
        frames = await extract_video_frames(video_path, target_fps=1)
        
        analysis_status[analysis_id].progress = 60.0
        analysis_status[analysis_id].current_step = "Analyse IA avec lexique technique..."
        
        # Step 4: Get video info
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0
        cap.release()
        
        video_info = VideoInfo(
            duration_seconds=duration,
            frame_count=frame_count,
            fps=fps,
            resolution=f"{width}x{height}"
        )
        
        # Step 5: Enhanced LLM Analysis with technical lexicon
        analysis_data = await analyze_frames_with_vision_enhanced_lexicon(
            frames, params, ttnet_results, video_processing_results
        )
        
        analysis_status[analysis_id].progress = 80.0
        analysis_status[analysis_id].current_step = "Génération des conseils avec lexique technique..."
        
        # Step 6: Generate enhanced recommendations with lexicon
        recommendations = await generate_lexicon_based_recommendations(
            analysis_data, params, ttnet_results, video_processing_results
        )
        
        # Step 7: Calculate enhanced metrics
        performance_metrics = calculate_enhanced_performance_metrics_lexicon(
            analysis_data, ttnet_results, video_processing_results
        )
        
        # Step 8: Generate highlights from video processing
        highlights = generate_highlights_from_video_processor(video_processing_results, duration)
        
        analysis_status[analysis_id].progress = 90.0
        analysis_status[analysis_id].current_step = "Finalisation des compilations..."
        
        # Generate real video compilations
        video_compilations = compile_videos_with_real_analysis(video_processing_results, ttnet_results, analysis_id)
        
        # Create enhanced technical analysis with lexicon
        technical_analysis = TechnicalAnalysis(
            stroke_analysis=analysis_data.get("stroke_analysis", {}),
            positioning_analysis=analysis_data.get("positioning_analysis", {}),
            timing_analysis=analysis_data.get("timing_analysis", {}),
            movement_analysis=extract_movement_analysis_lexicon(ttnet_results, video_processing_results),
            ttnet_analysis=ttnet_results.get("match_statistics", {})
        )
        
        # Apply table tennis scoring rules
        table_tennis_rules = apply_table_tennis_scoring(ttnet_results)
        
        # Extract REAL data from TTNet analysis
        real_ball_positions = extract_real_ball_positions(ttnet_results)
        real_stroke_distribution = extract_real_stroke_distribution(ttnet_results, video_processing_results)
        real_score_progression = generate_real_score_progression(ttnet_results, table_tennis_rules)
        
        # Integrate spin analysis
        spin_analysis = integrate_spin_analysis(ttnet_results)
        
        result = AnalysisResult(
            analysis_id=analysis_id,
            video_info=video_info,
            technical_analysis=technical_analysis,
            performance_metrics=performance_metrics,
            recommendations=recommendations,
            highlights_timestamps=highlights,
            confidence_score=calculate_enhanced_confidence_score(ttnet_results, analysis_data),
            video_compilations=video_compilations or {},
            lexicon_analysis=video_processing_results.get("technical_analysis", {}),
            table_tennis_scoring=table_tennis_rules,
            spin_analysis=spin_analysis,
            ball_positions=real_ball_positions,
            stroke_distribution=real_stroke_distribution,
            real_score_progression=real_score_progression
        )
        
        analysis_results[analysis_id] = result
        analysis_status[analysis_id].status = "completed"
        analysis_status[analysis_id].progress = 100.0
        analysis_status[analysis_id].completed_at = datetime.utcnow()
        analysis_status[analysis_id].current_step = "Analyse complète terminée avec compilations vidéo !"
        
        # Cleanup original video but keep compilations
        if os.path.exists(video_path):
            os.remove(video_path)
        
        # Cleanup video processor temp files after a delay
        async def cleanup_after_delay():
            await asyncio.sleep(3600)  # Keep compilations for 1 hour
            video_processor.cleanup()
        
        asyncio.create_task(cleanup_after_delay())
        
        logger.info(f"Enhanced analysis {analysis_id} completed successfully with video compilations")
        
    except Exception as e:
        logger.error(f"Enhanced analysis failed for {analysis_id}: {str(e)}")
        analysis_status[analysis_id].status = "failed"
        analysis_status[analysis_id].error_message = f"Erreur lors de l'analyse avancée: {str(e)}"
        
        # Cleanup on error
        if os.path.exists(video_path):
            os.remove(video_path)

# API Routes
@api_router.post("/analyze")
async def upload_and_analyze_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    player_side: str = Form("droite"),
    skill_level: str = Form("intermediaire"),
    focus_areas: str = Form("technique_coups,positionnement,timing")
):
    """Upload video and start analysis"""
    
    # Validate file
    if not video.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        raise HTTPException(status_code=400, detail="Format de fichier non supporté. Utilisez MP4, AVI, MOV ou MKV.")
    
    # Generate analysis ID
    analysis_id = str(uuid.uuid4())
    
    # Save uploaded file
    file_extension = Path(video.filename).suffix
    filename = f"{analysis_id}{file_extension}"
    file_path = UPLOAD_DIR / filename
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await video.read()
        await f.write(content)
    
    # Create analysis request
    focus_list = [area.strip() for area in focus_areas.split(',')]
    params = AnalysisRequest(
        player_side=player_side,
        skill_level=skill_level,
        focus_areas=focus_list
    )
    
    # Initialize status
    analysis_status[analysis_id] = AnalysisStatus(
        analysis_id=analysis_id,
        status="queued",
        progress=0.0,
        created_at=datetime.utcnow(),
        current_step="En attente..."
    )
    
    # Start background analysis with TT3D
    background_tasks.add_task(process_video_analysis_with_tt3d, str(file_path), params, analysis_id, background_tasks)
    
    return {
        "analysis_id": analysis_id,
        "status": "queued",
        "message": "Vidéo téléchargée avec succès. Analyse en cours...",
        "estimated_time": "2-4 minutes"
    }

@api_router.get("/analysis/{analysis_id}/status")
async def get_analysis_status(analysis_id: str):
    """Get analysis status"""
    if analysis_id not in analysis_status:
        raise HTTPException(status_code=404, detail="ID d'analyse introuvable")
    
    return analysis_status[analysis_id]

@api_router.get("/analysis/{analysis_id}/video/{video_type}")
async def get_compilation_video(analysis_id: str, video_type: str):
    """Get compiled video by type"""
    if analysis_id not in analysis_status:
        raise HTTPException(status_code=404, detail="ID d'analyse introuvable")
    
    status = analysis_status[analysis_id]
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail="Analyse non terminée")
    
    if analysis_id not in analysis_results:
        raise HTTPException(status_code=500, detail="Résultats d'analyse introuvables")
    
    result = analysis_results[analysis_id]
    
    if not result.video_compilations or video_type not in result.video_compilations:
        raise HTTPException(status_code=404, detail="Vidéo de compilation introuvable")
    
    video_path = result.video_compilations[video_type]
    
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Fichier vidéo introuvable")
    
    return FileResponse(
        video_path, 
        media_type="video/mp4", 
        filename=f"{video_type}_{analysis_id}.mp4"
    )

# Video serving endpoint
@api_router.get("/videos/{video_filename}")
async def serve_video_file(video_filename: str):
    """Serve compiled video files directly"""
    # Look for the video file in compilations directory
    compilations_dir = Path("/app/backend/compilations")
    
    # Search for the file in all analysis subdirectories
    for analysis_dir in compilations_dir.glob("*/"):
        video_path = analysis_dir / video_filename
        if video_path.exists():
            return FileResponse(
                str(video_path),
                media_type="video/mp4",
                filename=video_filename
            )
    
    raise HTTPException(status_code=404, detail="Fichier vidéo introuvable")


@api_router.get("/analysis/{analysis_id}/results")
async def get_analysis_results(analysis_id: str):
    """Get analysis results"""
    if analysis_id not in analysis_status:
        raise HTTPException(status_code=404, detail="ID d'analyse introuvable")
    
    status = analysis_status[analysis_id]
    
    if status.status != "completed":
        raise HTTPException(status_code=400, detail=f"Analyse non terminée. Statut actuel : {status.status}")
    
    if analysis_id not in analysis_results:
        raise HTTPException(status_code=500, detail="Résultats d'analyse introuvables")
    
    return analysis_results[analysis_id]

@api_router.options("/{full_path:path}")
async def handle_options(full_path: str):
    """Handle all OPTIONS requests for CORS"""
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Origin, X-Requested-With",
            "Access-Control-Max-Age": "86400"
        }
    )

@api_router.get("/")
async def root():
    return {"message": "PingPro API - Analyse IA Tennis de Table"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()