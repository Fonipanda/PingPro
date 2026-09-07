"""
Module d'estimation du spin (effet) de balle - Computer Vision Pure
Basé sur l'analyse de trajectoire et l'effet Magnus

Références:
- CVPR 2025: "Towards Ball Spin and Trajectory Analysis in Table Tennis Broadcast Videos"
- SpinDOE: Dot-pattern-based spin estimation (Gossard et al.)
"""

import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
import math

logger = logging.getLogger(__name__)


class SpinType(Enum):
    """Types d'effets au tennis de table"""
    TOPSPIN = "topspin"         # Lift - rotation vers l'avant
    BACKSPIN = "backspin"       # Coupé - rotation vers l'arrière  
    SIDESPIN_LEFT = "sidespin_left"   # Latéral gauche
    SIDESPIN_RIGHT = "sidespin_right" # Latéral droit
    NO_SPIN = "no_spin"         # Sans effet
    MIXED = "mixed"             # Effet combiné


@dataclass
class SpinEstimate:
    """Estimation du spin pour une frappe"""
    spin_type: SpinType
    spin_magnitude: float       # RPM estimé (0-4000)
    confidence: float           # Confiance 0-1
    trajectory_deviation: float # Déviation par rapport à trajectoire balistique
    magnus_effect: float        # Force Magnus estimée
    bounce_angle_change: float  # Changement d'angle au rebond


@dataclass
class TrajectoryPoint:
    """Point de trajectoire avec métadonnées"""
    x: float
    y: float
    frame: int
    timestamp: float
    velocity: Optional[Tuple[float, float]] = None
    acceleration: Optional[Tuple[float, float]] = None


class SpinEstimator:
    """
    Estimateur de spin basé sur l'analyse de trajectoire.
    Utilise l'effet Magnus pour déduire le spin de la déviation de trajectoire.
    """
    
    GRAVITY = 9.81  # m/s²
    BALL_DIAMETER = 0.040  # 40mm en mètres
    BALL_MASS = 0.0027  # 2.7g en kg
    AIR_DENSITY = 1.225  # kg/m³
    
    DRAG_COEFFICIENT = 0.5
    LIFT_COEFFICIENT = 0.25  # Magnus coefficient
    
    TABLE_LENGTH = 2.74  # mètres
    TABLE_WIDTH = 1.525  # mètres
    NET_HEIGHT = 0.1525  # 15.25cm
    
    def __init__(self, fps: float = 30.0, pixels_per_meter: float = 200.0):
        self.fps = fps
        self.ppm = pixels_per_meter
        self.dt = 1.0 / fps
        
    def estimate_spin_from_trajectory(
        self, 
        ball_positions: List[Tuple[float, float]],
        frame_indices: Optional[List[int]] = None
    ) -> List[SpinEstimate]:
        """
        Estime le spin à partir d'une séquence de positions de balle.
        
        Args:
            ball_positions: Liste de (x, y) en pixels
            frame_indices: Indices de frames optionnels
            
        Returns:
            Liste d'estimations de spin pour chaque segment
        """
        if len(ball_positions) < 5:
            return [self._create_default_estimate()]
        
        trajectory = self._build_trajectory(ball_positions, frame_indices)
        segments = self._segment_trajectory(trajectory)
        
        estimates = []
        for segment in segments:
            estimate = self._analyze_segment(segment)
            estimates.append(estimate)
            
        return estimates
    
    def _build_trajectory(
        self,
        positions: List[Tuple[float, float]],
        frame_indices: Optional[List[int]] = None
    ) -> List[TrajectoryPoint]:
        """Construit une trajectoire avec vélocités et accélérations"""
        
        trajectory = []
        
        for i, (x, y) in enumerate(positions):
            frame = frame_indices[i] if frame_indices else i
            timestamp = frame / self.fps
            
            point = TrajectoryPoint(
                x=x / self.ppm,  # Convertir en mètres
                y=y / self.ppm,
                frame=frame,
                timestamp=timestamp
            )
            trajectory.append(point)
        
        for i in range(1, len(trajectory) - 1):
            dt = trajectory[i+1].timestamp - trajectory[i-1].timestamp
            if dt > 0:
                vx = (trajectory[i+1].x - trajectory[i-1].x) / dt
                vy = (trajectory[i+1].y - trajectory[i-1].y) / dt
                trajectory[i].velocity = (vx, vy)
        
        for i in range(2, len(trajectory) - 2):
            if trajectory[i-1].velocity and trajectory[i+1].velocity:
                dt = trajectory[i+1].timestamp - trajectory[i-1].timestamp
                if dt > 0:
                    ax = (trajectory[i+1].velocity[0] - trajectory[i-1].velocity[0]) / dt
                    ay = (trajectory[i+1].velocity[1] - trajectory[i-1].velocity[1]) / dt
                    trajectory[i].acceleration = (ax, ay)
        
        return trajectory
    
    def _segment_trajectory(
        self, 
        trajectory: List[TrajectoryPoint]
    ) -> List[List[TrajectoryPoint]]:
        """Segmente la trajectoire en échanges (rebond = nouveau segment)"""
        
        segments = []
        current_segment = []
        
        for i, point in enumerate(trajectory):
            current_segment.append(point)
            
            if i > 0 and i < len(trajectory) - 1:
                if self._detect_bounce(trajectory[i-1], point, trajectory[i+1]):
                    if len(current_segment) >= 3:
                        segments.append(current_segment[:-1])
                    current_segment = [point]
        
        if len(current_segment) >= 3:
            segments.append(current_segment)
            
        return segments if segments else [trajectory]
    
    def _detect_bounce(
        self, 
        prev: TrajectoryPoint, 
        curr: TrajectoryPoint, 
        next_pt: TrajectoryPoint
    ) -> bool:
        """Détecte un rebond par changement de direction verticale"""
        
        if prev.velocity and next_pt.velocity:
            vy_before = prev.velocity[1]
            vy_after = next_pt.velocity[1]
            
            if vy_before > 0 and vy_after < 0:
                return True
            if vy_before < 0 and vy_after > 0:
                return True
        
        dy1 = curr.y - prev.y
        dy2 = next_pt.y - curr.y
        if dy1 * dy2 < 0:
            return True
            
        return False
    
    def _analyze_segment(self, segment: List[TrajectoryPoint]) -> SpinEstimate:
        """Analyse un segment de trajectoire pour estimer le spin"""
        
        if len(segment) < 3:
            return self._create_default_estimate()
        
        expected = self._compute_ballistic_trajectory(segment)
        deviation = self._compute_trajectory_deviation(segment, expected)
        
        spin_type, magnitude = self._infer_spin_from_deviation(segment, deviation)
        
        bounce_angle = self._compute_bounce_angle_change(segment)
        
        magnus = self._estimate_magnus_force(segment, deviation)
        
        confidence = self._compute_confidence(segment, deviation)
        
        return SpinEstimate(
            spin_type=spin_type,
            spin_magnitude=magnitude,
            confidence=confidence,
            trajectory_deviation=deviation,
            magnus_effect=magnus,
            bounce_angle_change=bounce_angle
        )
    
    def _compute_ballistic_trajectory(
        self, 
        segment: List[TrajectoryPoint]
    ) -> List[Tuple[float, float]]:
        """Calcule la trajectoire balistique attendue (sans spin)"""
        
        if len(segment) < 2 or not segment[0].velocity:
            return [(p.x, p.y) for p in segment]
        
        x0, y0 = segment[0].x, segment[0].y
        vx0, vy0 = segment[0].velocity if segment[0].velocity else (0, 0)
        
        expected = []
        for point in segment:
            t = point.timestamp - segment[0].timestamp
            
            x = x0 + vx0 * t
            y = y0 + vy0 * t + 0.5 * self.GRAVITY * t * t
            
            expected.append((x, y))
            
        return expected
    
    def _compute_trajectory_deviation(
        self,
        actual: List[TrajectoryPoint],
        expected: List[Tuple[float, float]]
    ) -> float:
        """Calcule la déviation moyenne par rapport à la trajectoire balistique"""
        
        if len(actual) != len(expected):
            return 0.0
        
        total_deviation = 0.0
        for point, (ex, ey) in zip(actual, expected):
            dx = point.x - ex
            dy = point.y - ey
            deviation = math.sqrt(dx*dx + dy*dy)
            total_deviation += deviation
            
        return total_deviation / len(actual)
    
    def _infer_spin_from_deviation(
        self,
        segment: List[TrajectoryPoint],
        deviation: float
    ) -> Tuple[SpinType, float]:
        """Déduit le type et la magnitude du spin de la déviation"""
        
        curve_x = 0.0
        curve_y = 0.0
        
        for i in range(len(segment) - 2):
            p1, p2, p3 = segment[i], segment[i+1], segment[i+2]
            
            v1x = p2.x - p1.x
            v1y = p2.y - p1.y
            v2x = p3.x - p2.x
            v2y = p3.y - p2.y
            
            curve_x += v2x - v1x
            curve_y += v2y - v1y
        
        if len(segment) > 2:
            curve_x /= (len(segment) - 2)
            curve_y /= (len(segment) - 2)
        
        magnitude = min(4000, deviation * 15000)
        
        if abs(curve_y) < 0.001 and abs(curve_x) < 0.001:
            return SpinType.NO_SPIN, magnitude * 0.1
        
        if curve_y < -0.002:
            return SpinType.TOPSPIN, magnitude
        elif curve_y > 0.002:
            return SpinType.BACKSPIN, magnitude
        elif curve_x < -0.002:
            return SpinType.SIDESPIN_LEFT, magnitude * 0.8
        elif curve_x > 0.002:
            return SpinType.SIDESPIN_RIGHT, magnitude * 0.8
        else:
            return SpinType.MIXED, magnitude * 0.5
    
    def _compute_bounce_angle_change(self, segment: List[TrajectoryPoint]) -> float:
        """Calcule le changement d'angle au rebond (indicateur de spin)"""
        
        for i in range(1, len(segment) - 1):
            if self._detect_bounce(segment[i-1], segment[i], segment[i+1]):
                if segment[i-1].velocity and segment[i+1].velocity:
                    v_before = segment[i-1].velocity
                    v_after = segment[i+1].velocity
                    
                    angle_before = math.atan2(v_before[1], v_before[0])
                    angle_after = math.atan2(v_after[1], v_after[0])
                    
                    return math.degrees(abs(angle_after - angle_before))
        
        return 0.0
    
    def _estimate_magnus_force(
        self,
        segment: List[TrajectoryPoint],
        deviation: float
    ) -> float:
        """Estime la force Magnus à partir de la déviation"""
        
        avg_speed = 0.0
        count = 0
        
        for point in segment:
            if point.velocity:
                vx, vy = point.velocity
                speed = math.sqrt(vx*vx + vy*vy)
                avg_speed += speed
                count += 1
        
        if count > 0:
            avg_speed /= count
        
        magnus = self.LIFT_COEFFICIENT * self.AIR_DENSITY * avg_speed * deviation
        
        return min(1.0, magnus * 10)
    
    def _compute_confidence(
        self,
        segment: List[TrajectoryPoint],
        deviation: float
    ) -> float:
        """Calcule la confiance de l'estimation"""
        
        length_factor = min(1.0, len(segment) / 10.0)
        
        velocity_count = sum(1 for p in segment if p.velocity)
        data_quality = velocity_count / len(segment) if segment else 0
        
        deviation_factor = min(1.0, deviation / 0.1) if deviation > 0 else 0.5
        
        confidence = (length_factor * 0.3 + data_quality * 0.4 + deviation_factor * 0.3)
        
        return max(0.3, min(0.95, confidence))
    
    def _create_default_estimate(self) -> SpinEstimate:
        """Crée une estimation par défaut quand les données sont insuffisantes"""
        return SpinEstimate(
            spin_type=SpinType.NO_SPIN,
            spin_magnitude=0.0,
            confidence=0.3,
            trajectory_deviation=0.0,
            magnus_effect=0.0,
            bounce_angle_change=0.0
        )
    
    def analyze_stroke_spin(
        self,
        ball_positions: List[Tuple[float, float]],
        stroke_type: str
    ) -> Dict[str, Any]:
        """
        Analyse le spin d'un coup spécifique.
        
        Args:
            ball_positions: Positions de la balle pendant le coup
            stroke_type: Type de coup (topspin_cd, service_coupe, etc.)
            
        Returns:
            Dictionnaire avec analyse complète du spin
        """
        
        estimates = self.estimate_spin_from_trajectory(ball_positions)
        
        if not estimates:
            return self._default_stroke_analysis(stroke_type)
        
        main_estimate = estimates[0]
        
        expected_spin = self._get_expected_spin_for_stroke(stroke_type)
        
        technique_quality = self._assess_spin_quality(main_estimate, expected_spin)
        
        return {
            "stroke_type": stroke_type,
            "detected_spin": {
                "type": main_estimate.spin_type.value,
                "magnitude_rpm": round(main_estimate.spin_magnitude),
                "confidence": round(main_estimate.confidence, 2)
            },
            "expected_spin": expected_spin,
            "spin_matches_technique": main_estimate.spin_type.value == expected_spin.get("type"),
            "technique_quality": technique_quality,
            "trajectory_analysis": {
                "deviation_meters": round(main_estimate.trajectory_deviation, 4),
                "magnus_effect": round(main_estimate.magnus_effect, 3),
                "bounce_angle_change_deg": round(main_estimate.bounce_angle_change, 1)
            },
            "recommendations": self._generate_spin_recommendations(main_estimate, stroke_type)
        }
    
    def _get_expected_spin_for_stroke(self, stroke_type: str) -> Dict[str, Any]:
        """Retourne le spin attendu pour un type de coup"""
        
        spin_expectations = {
            "topspin_cd": {"type": "topspin", "min_rpm": 2000, "max_rpm": 4000},
            "topspin_rv": {"type": "topspin", "min_rpm": 1500, "max_rpm": 3500},
            "chop": {"type": "backspin", "min_rpm": 1000, "max_rpm": 2500},
            "poussette_cd": {"type": "backspin", "min_rpm": 500, "max_rpm": 1500},
            "poussette_rv": {"type": "backspin", "min_rpm": 500, "max_rpm": 1500},
            "service_coupe": {"type": "backspin", "min_rpm": 1500, "max_rpm": 3000},
            "service_lifte": {"type": "topspin", "min_rpm": 1000, "max_rpm": 2500},
            "service_lateral": {"type": "sidespin_right", "min_rpm": 1500, "max_rpm": 3000},
            "smash": {"type": "topspin", "min_rpm": 500, "max_rpm": 1500},
            "bloc": {"type": "no_spin", "min_rpm": 0, "max_rpm": 500},
            "flip_cd": {"type": "topspin", "min_rpm": 800, "max_rpm": 2000},
        }
        
        return spin_expectations.get(stroke_type, {"type": "mixed", "min_rpm": 500, "max_rpm": 2000})
    
    def _assess_spin_quality(self, estimate: SpinEstimate, expected: Dict) -> float:
        """Évalue la qualité du spin par rapport à ce qui est attendu"""
        
        type_match = 1.0 if estimate.spin_type.value == expected.get("type") else 0.5
        
        min_rpm = expected.get("min_rpm", 0)
        max_rpm = expected.get("max_rpm", 2000)
        optimal = (min_rpm + max_rpm) / 2
        
        if min_rpm <= estimate.spin_magnitude <= max_rpm:
            magnitude_score = 1.0
        elif estimate.spin_magnitude < min_rpm:
            magnitude_score = max(0.3, estimate.spin_magnitude / min_rpm)
        else:
            magnitude_score = max(0.5, 1.0 - (estimate.spin_magnitude - max_rpm) / max_rpm)
        
        quality = (type_match * 0.4 + magnitude_score * 0.4 + estimate.confidence * 0.2)
        
        return round(min(1.0, quality) * 100, 1)
    
    def _generate_spin_recommendations(
        self, 
        estimate: SpinEstimate, 
        stroke_type: str
    ) -> List[str]:
        """Génère des recommandations basées sur l'analyse du spin"""
        
        recommendations = []
        expected = self._get_expected_spin_for_stroke(stroke_type)
        
        if estimate.spin_magnitude < expected.get("min_rpm", 0):
            recommendations.append(
                f"Augmenter la rotation: votre {stroke_type} génère {estimate.spin_magnitude:.0f} RPM, "
                f"visez au moins {expected.get('min_rpm', 0)} RPM"
            )
            recommendations.append("Accentuer le brossage de la balle avec le poignet")
        
        if estimate.spin_type.value != expected.get("type"):
            recommendations.append(
                f"Type d'effet incorrect: détecté {estimate.spin_type.value}, "
                f"attendu {expected.get('type')} pour un {stroke_type}"
            )
            recommendations.append("Vérifier l'angle de la raquette au moment du contact")
        
        if estimate.confidence < 0.6:
            recommendations.append(
                "Trajectoire irrégulière détectée - travaillez la régularité du geste"
            )
        
        if not recommendations:
            recommendations.append(f"Bon spin sur le {stroke_type}! Continuez ainsi.")
        
        return recommendations
    
    def _default_stroke_analysis(self, stroke_type: str) -> Dict[str, Any]:
        """Analyse par défaut si données insuffisantes"""
        return {
            "stroke_type": stroke_type,
            "detected_spin": {
                "type": "unknown",
                "magnitude_rpm": 0,
                "confidence": 0.0
            },
            "expected_spin": self._get_expected_spin_for_stroke(stroke_type),
            "spin_matches_technique": False,
            "technique_quality": 50.0,
            "trajectory_analysis": {
                "deviation_meters": 0.0,
                "magnus_effect": 0.0,
                "bounce_angle_change_deg": 0.0
            },
            "recommendations": ["Données insuffisantes pour analyser le spin"]
        }


def integrate_spin_analysis(ttnet_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Intègre l'analyse de spin aux résultats TTNet.
    
    Args:
        ttnet_results: Résultats de l'analyse TTNet
        
    Returns:
        Résultats enrichis avec l'analyse de spin
    """
    estimator = SpinEstimator()
    
    ball_detections = ttnet_results.get("ball_detections", [])
    
    if not ball_detections:
        return {
            "spin_analysis_available": False,
            "reason": "Pas de détections de balle disponibles",
            "spin_estimates": []
        }
    
    positions = [(d.get("x", 0), d.get("y", 0)) for d in ball_detections if d]
    
    if len(positions) < 5:
        return {
            "spin_analysis_available": False,
            "reason": f"Seulement {len(positions)} positions détectées (minimum 5)",
            "spin_estimates": []
        }
    
    estimates = estimator.estimate_spin_from_trajectory(positions)
    
    spin_distribution = {
        SpinType.TOPSPIN.value: 0,
        SpinType.BACKSPIN.value: 0,
        SpinType.SIDESPIN_LEFT.value: 0,
        SpinType.SIDESPIN_RIGHT.value: 0,
        SpinType.NO_SPIN.value: 0,
        SpinType.MIXED.value: 0
    }
    
    total_magnitude = 0.0
    total_confidence = 0.0
    
    for est in estimates:
        spin_distribution[est.spin_type.value] += 1
        total_magnitude += est.spin_magnitude
        total_confidence += est.confidence
    
    n = len(estimates) if estimates else 1
    
    dominant_spin = max(spin_distribution, key=spin_distribution.get)
    
    return {
        "spin_analysis_available": True,
        "total_spin_segments": len(estimates),
        "dominant_spin_type": dominant_spin,
        "average_spin_rpm": round(total_magnitude / n),
        "average_confidence": round(total_confidence / n, 2),
        "spin_distribution": spin_distribution,
        "spin_estimates": [
            {
                "type": e.spin_type.value,
                "magnitude_rpm": round(e.spin_magnitude),
                "confidence": round(e.confidence, 2),
                "trajectory_deviation": round(e.trajectory_deviation, 4),
                "magnus_effect": round(e.magnus_effect, 3),
                "bounce_angle_change": round(e.bounce_angle_change, 1)
            }
            for e in estimates[:10]
        ]
    }
