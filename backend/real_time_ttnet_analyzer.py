"""
Real-Time Table Tennis Analysis System
Inspired by TTNet (https://arxiv.org/pdf/2004.09927) and PingHero.ai

This module implements a complete real-time table tennis analysis system with:
- Ball detection and tracking (Global + Local stages)
- Player and table segmentation 
- Event spotting (bounce, net hit, serve)
- Real-time statistics generation
- Live video annotation
"""

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional, Any, NamedTuple
import time
import threading
from dataclasses import dataclass, field
from collections import deque
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Core data structures
@dataclass
class BallDetection:
    """Single frame ball detection result"""
    x: float
    y: float
    confidence: float
    timestamp: float
    frame_id: int

@dataclass
class PlayerDetection:
    """Player segmentation and tracking result"""
    player_id: int  # 0 or 1
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    mask: np.ndarray
    pose_keypoints: Optional[List[Tuple[float, float]]] = None
    confidence: float = 0.0

@dataclass
class EventDetection:
    """Game event detection result"""
    event_type: str  # 'bounce', 'net_hit', 'serve', 'rally_end'
    timestamp: float
    frame_id: int
    confidence: float
    ball_position: Optional[Tuple[float, float]] = None
    player_id: Optional[int] = None

@dataclass
class GameState:
    """Current game state and statistics"""
    # Score tracking (tennis de table: 11 points, 2 points d'avance)
    player1_score: int = 0
    player2_score: int = 0
    player1_sets: int = 0
    player2_sets: int = 0
    current_set: int = 1
    match_format: int = 3  # Premier à 2 sets (ou 5 sets = premier à 3)
    
    # Rally tracking
    current_rally_length: int = 0
    total_rallies: int = 0
    rally_start_time: Optional[float] = None
    
    # Ball tracking
    ball_position: Optional[Tuple[float, float]] = None
    ball_velocity: Optional[Tuple[float, float]] = None
    ball_trajectory: deque = field(default_factory=lambda: deque(maxlen=30))
    
    # Event history
    events: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Real-time stats
    rally_lengths: List[int] = field(default_factory=list)
    serve_stats: Dict[int, Dict] = field(default_factory=lambda: {0: {'total': 0, 'success': 0}, 1: {'total': 0, 'success': 0}})
    shot_zones: Dict[int, List[Tuple[float, float]]] = field(default_factory=lambda: {0: [], 1: []})
    
    # Game timing
    game_start_time: Optional[float] = None
    last_event_time: Optional[float] = None

class TTNetBackbone(nn.Module):
    """
    TTNet backbone network for feature extraction
    Simplified version of the original TTNet architecture
    """
    
    def __init__(self, input_channels=27):  # 9 frames * 3 channels
        super(TTNetBackbone, self).__init__()
        
        # Shared encoder layers
        self.conv1 = nn.Sequential(
            nn.Conv2d(input_channels, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )
        
        self.conv2 = nn.Sequential(
            nn.MaxPool2d(2, 2),
            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True)
        )
        
        self.conv3 = nn.Sequential(
            nn.MaxPool2d(2, 2),
            nn.Conv2d(128, 256, 3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, 3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True)
        )
        
        self.conv4 = nn.Sequential(
            nn.MaxPool2d(2, 2),
            nn.Conv2d(256, 512, 3, padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.Conv2d(512, 512, 3, padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True)
        )
        
    def forward(self, x):
        conv1 = self.conv1(x)
        conv2 = self.conv2(conv1)
        conv3 = self.conv3(conv2)
        conv4 = self.conv4(conv3)
        
        return {
            'conv1': conv1,
            'conv2': conv2, 
            'conv3': conv3,
            'conv4': conv4
        }

class GlobalBallDetector(nn.Module):
    """
    Global ball detection stage - processes downscaled frames
    """
    
    def __init__(self, backbone_features=512):
        super(GlobalBallDetector, self).__init__()
        
        self.global_head = nn.Sequential(
            nn.AdaptiveAvgPool2d((8, 8)),
            nn.Flatten(),
            nn.Linear(512 * 8 * 8, 1024),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(1024, 256),
            nn.ReLU(inplace=True),
            nn.Linear(256, 3)  # x, y, confidence
        )
        
    def forward(self, features):
        conv4 = features['conv4']
        global_pred = self.global_head(conv4)
        return global_pred

class LocalBallDetector(nn.Module):
    """
    Local ball detection stage - refines detection on high-res crops
    """
    
    def __init__(self, input_channels=27, crop_size=256):
        super(LocalBallDetector, self).__init__()
        self.crop_size = crop_size
        
        # Local feature extractor
        self.local_conv = nn.Sequential(
            nn.Conv2d(input_channels, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64), 
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((8, 8))
        )
        
        self.local_head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 8 * 8, 512),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(512, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, 3)  # dx, dy, confidence (relative to crop)
        )
        
    def forward(self, crop):
        local_features = self.local_conv(crop)
        local_pred = self.local_head(local_features)
        return local_pred

class SegmentationHead(nn.Module):
    """
    Semantic segmentation for players, table, and background
    """
    
    def __init__(self, backbone_features=512, num_classes=4):  # bg, player1, player2, table
        super(SegmentationHead, self).__init__()
        
        # Decoder layers
        self.decoder4 = nn.Sequential(
            nn.ConvTranspose2d(512, 256, 2, stride=2),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True)
        )
        
        self.decoder3 = nn.Sequential(
            nn.Conv2d(256 + 256, 256, 3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(256, 128, 2, stride=2),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True)
        )
        
        self.decoder2 = nn.Sequential(
            nn.Conv2d(128 + 128, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(128, 64, 2, stride=2),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )
        
        self.classifier = nn.Conv2d(64 + 64, num_classes, 1)
        
    def forward(self, features):
        conv1, conv2, conv3, conv4 = features['conv1'], features['conv2'], features['conv3'], features['conv4']
        
        # Decoder path with skip connections
        dec4 = self.decoder4(conv4)
        dec3 = self.decoder3(torch.cat([dec4, conv3], dim=1))
        dec2 = self.decoder2(torch.cat([dec3, conv2], dim=1))
        
        # Final classification
        out = self.classifier(torch.cat([dec2, conv1], dim=1))
        return out

class EventSpottingHead(nn.Module):
    """
    Temporal event detection (bounce, net hit, serve)
    """
    
    def __init__(self, backbone_features=512, num_events=4):  # bounce, net_hit, serve, rally_end
        super(EventSpottingHead, self).__init__()
        
        # Temporal feature aggregation
        self.temporal_conv = nn.Sequential(
            nn.AdaptiveAvgPool2d((4, 4)),
            nn.Flatten(),
            nn.Linear(512 * 4 * 4, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4)
        )
        
        # Event classification
        self.event_classifier = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, num_events)
        )
        
    def forward(self, features):
        conv4 = features['conv4']
        temporal_features = self.temporal_conv(conv4)
        event_probs = torch.sigmoid(self.event_classifier(temporal_features))
        return event_probs

class TTNetRealTime(nn.Module):
    """
    Complete TTNet model for real-time table tennis analysis
    """
    
    def __init__(self, input_channels=27):
        super(TTNetRealTime, self).__init__()
        
        self.backbone = TTNetBackbone(input_channels)
        self.global_ball_detector = GlobalBallDetector()
        self.local_ball_detector = LocalBallDetector(input_channels)
        self.segmentation_head = SegmentationHead()
        self.event_spotting_head = EventSpottingHead()
        
    def forward(self, x, local_crop=None):
        # Extract backbone features
        features = self.backbone(x)
        
        # Global ball detection
        global_ball = self.global_ball_detector(features)
        
        # Local ball detection (if crop provided)
        local_ball = None
        if local_crop is not None:
            local_ball = self.local_ball_detector(local_crop)
        
        # Segmentation
        segmentation = self.segmentation_head(features)
        
        # Event spotting
        events = self.event_spotting_head(features)
        
        return {
            'global_ball': global_ball,
            'local_ball': local_ball,
            'segmentation': segmentation,
            'events': events
        }

class RealTimeAnalyzer:
    """
    Main real-time analysis system
    """
    
    def __init__(self, device='cuda' if torch.cuda.is_available() else 'cpu'):
        self.device = device
        self.model = TTNetRealTime().to(device)
        self.game_state = GameState()
        self.frame_buffer = deque(maxlen=9)
        self.running = False
        
        # Analysis parameters
        self.input_height = 270
        self.input_width = 480
        self.crop_size = 256
        self.confidence_threshold = 0.3
        self.event_threshold = 0.5
        
        # Statistics tracking
        self.stats_history = {
            'ball_detections': deque(maxlen=1000),
            'rally_stats': deque(maxlen=50),
            'event_stats': deque(maxlen=200)
        }
        
        logger.info(f"RealTimeAnalyzer initialized on device: {device}")
        
    def load_pretrained_weights(self, weights_path: str):
        """Load pre-trained TTNet weights"""
        try:
            checkpoint = torch.load(weights_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['state_dict'])
            logger.info(f"Loaded pretrained weights from {weights_path}")
        except Exception as e:
            logger.warning(f"Could not load weights: {e}. Using random initialization.")
            
    def preprocess_frames(self, frames: List[np.ndarray]) -> torch.Tensor:
        """Preprocess frame stack for model input"""
        if len(frames) != 9:
            # Pad with last frame if needed
            while len(frames) < 9:
                frames.append(frames[-1] if frames else np.zeros((480, 640, 3), dtype=np.uint8))
        
        # Resize and normalize frames
        processed = []
        for frame in frames:
            frame_resized = cv2.resize(frame, (self.input_width, self.input_height))
            frame_norm = frame_resized.astype(np.float32) / 255.0
            processed.append(frame_norm)
        
        # Stack frames: (9, H, W, 3) -> (27, H, W)
        stacked = np.concatenate([f.transpose(2, 0, 1) for f in processed], axis=0)
        
        # Convert to tensor and add batch dimension
        tensor = torch.from_numpy(stacked).unsqueeze(0).to(self.device)
        return tensor
        
    def extract_local_crop(self, frame: np.ndarray, ball_pos: Tuple[float, float]) -> torch.Tensor:
        """Extract local crop around ball position for refinement"""
        h, w = frame.shape[:2]
        x, y = ball_pos
        
        # Convert normalized coordinates to pixel coordinates
        x_px = int(x * w)
        y_px = int(y * h)
        
        # Extract crop
        half_crop = self.crop_size // 2
        x1 = max(0, x_px - half_crop)
        y1 = max(0, y_px - half_crop)
        x2 = min(w, x_px + half_crop)
        y2 = min(h, y_px + half_crop)
        
        crop = frame[y1:y2, x1:x2]
        
        # Resize to standard crop size
        crop_resized = cv2.resize(crop, (self.crop_size, self.crop_size))
        
        # Normalize and convert to tensor
        crop_norm = crop_resized.astype(np.float32) / 255.0
        crop_tensor = torch.from_numpy(crop_norm.transpose(2, 0, 1)).unsqueeze(0).to(self.device)
        
        return crop_tensor
        
    def detect_ball(self, model_output: Dict, frame_shape: Tuple[int, int]) -> Optional[BallDetection]:
        """Extract ball detection from model output"""
        global_ball = model_output['global_ball'][0].cpu().numpy()  # Remove batch dim
        
        x_norm, y_norm, confidence = global_ball
        
        if confidence < self.confidence_threshold:
            return None
            
        # Convert to absolute coordinates
        h, w = frame_shape
        x = np.clip(x_norm, 0, 1) * w
        y = np.clip(y_norm, 0, 1) * h
        
        return BallDetection(
            x=float(x),
            y=float(y), 
            confidence=float(confidence),
            timestamp=time.time(),
            frame_id=len(self.stats_history['ball_detections'])
        )
        
    def detect_players(self, model_output: Dict) -> List[PlayerDetection]:
        """Extract player detections from segmentation output"""
        segmentation = model_output['segmentation'][0]  # Remove batch dim
        seg_probs = torch.softmax(segmentation, dim=0).cpu().numpy()
        
        players = []
        
        # Extract player masks (classes 1 and 2)
        for player_id in range(2):
            class_id = player_id + 1
            mask = seg_probs[class_id]
            
            if mask.max() > 0.3:  # Confidence threshold
                # Find bounding box
                coords = np.where(mask > 0.3)
                if len(coords[0]) > 0:
                    y1, x1 = coords[0].min(), coords[1].min()
                    y2, x2 = coords[0].max(), coords[1].max()
                    
                    players.append(PlayerDetection(
                        player_id=player_id,
                        bbox=(int(x1), int(y1), int(x2-x1), int(y2-y1)),
                        mask=(mask > 0.3).astype(np.uint8),
                        confidence=float(mask.max())
                    ))
                    
        return players
        
    def detect_events(self, model_output: Dict) -> List[EventDetection]:
        """Extract event detections from model output"""
        events_probs = model_output['events'][0].cpu().numpy()  # Remove batch dim
        
        detected_events = []
        event_names = ['bounce', 'net_hit', 'serve', 'rally_end']
        
        current_time = time.time()
        
        for i, prob in enumerate(events_probs):
            if prob > self.event_threshold:
                detected_events.append(EventDetection(
                    event_type=event_names[i],
                    timestamp=current_time,
                    frame_id=len(self.stats_history['event_stats']),
                    confidence=float(prob)
                ))
                
        return detected_events
        
    def update_game_state(self, ball_detection: Optional[BallDetection], 
                         events: List[EventDetection],
                         players: List[PlayerDetection]):
        """Update game state with new detections"""
        current_time = time.time()
        
        # Initialize game start time
        if self.game_state.game_start_time is None:
            self.game_state.game_start_time = current_time
            
        # Update ball tracking
        if ball_detection:
            self.game_state.ball_position = (ball_detection.x, ball_detection.y)
            self.game_state.ball_trajectory.append((ball_detection.x, ball_detection.y, ball_detection.timestamp))
            
            # Calculate velocity if we have previous position
            if len(self.game_state.ball_trajectory) >= 2:
                prev_pos = self.game_state.ball_trajectory[-2]
                dt = ball_detection.timestamp - prev_pos[2]
                if dt > 0:
                    vx = (ball_detection.x - prev_pos[0]) / dt
                    vy = (ball_detection.y - prev_pos[1]) / dt
                    self.game_state.ball_velocity = (vx, vy)
                    
        # Process events
        for event in events:
            self.game_state.events.append(event)
            self.game_state.last_event_time = event.timestamp
            
            if event.event_type == 'serve':
                # Start new rally
                if self.game_state.current_rally_length > 0:
                    self.game_state.rally_lengths.append(self.game_state.current_rally_length)
                self.game_state.current_rally_length = 0
                self.game_state.rally_start_time = event.timestamp
                
            elif event.event_type == 'bounce':
                self.game_state.current_rally_length += 1
                
            elif event.event_type == 'rally_end':
                if self.game_state.current_rally_length > 0:
                    self.game_state.rally_lengths.append(self.game_state.current_rally_length)
                self.game_state.current_rally_length = 0
                self.game_state.rally_start_time = None
                
        # Store statistics
        if ball_detection:
            self.stats_history['ball_detections'].append(ball_detection)
        self.stats_history['event_stats'].extend(events)
        
    def get_real_time_statistics(self) -> Dict[str, Any]:
        """Generate real-time statistics for display"""
        current_time = time.time()
        game_duration = current_time - self.game_state.game_start_time if self.game_state.game_start_time else 0
        
        # Score tracking avec règles tennis de table
        avg_rally_length = np.mean(self.game_state.rally_lengths) if self.game_state.rally_lengths else 0
        total_rallies = len(self.game_state.rally_lengths)
        
        # Vérifier fin de set (11 points avec 2 d'avance)
        p1_score = self.game_state.player1_score
        p2_score = self.game_state.player2_score
        set_finished = False
        set_winner = None
        
        if (p1_score >= 11 and p1_score - p2_score >= 2) or (p1_score >= 10 and p2_score >= 10 and abs(p1_score - p2_score) >= 2):
            set_finished = True
            set_winner = 1 if p1_score > p2_score else 2
            
        # Vérifier fin de match
        sets_to_win = (self.game_state.match_format + 1) // 2  # 2 sets pour match 3, 3 sets pour match 5
        match_finished = (self.game_state.player1_sets >= sets_to_win or 
                         self.game_state.player2_sets >= sets_to_win)
        
        # Ball speed analysis
        speeds = []
        if len(self.game_state.ball_trajectory) >= 2:
            for i in range(1, len(self.game_state.ball_trajectory)):
                prev = self.game_state.ball_trajectory[i-1]
                curr = self.game_state.ball_trajectory[i]
                dt = curr[2] - prev[2]
                if dt > 0:
                    dx = curr[0] - prev[0]
                    dy = curr[1] - prev[1]
                    speed = np.sqrt(dx*dx + dy*dy) / dt
                    speeds.append(speed)
                    
        # Event counts
        recent_events = [e for e in self.game_state.events if current_time - e.timestamp < 60]  # Last minute
        event_counts = {}
        for event in recent_events:
            event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
            
        return {
            'game_duration': game_duration,
            'score': {
                'player1': self.game_state.player1_score,
                'player2': self.game_state.player2_score
            },
            'current_rally': {
                'length': self.game_state.current_rally_length,
                'duration': current_time - self.game_state.rally_start_time if self.game_state.rally_start_time else 0
            },
            'rally_stats': {
                'total_rallies': total_rallies,
                'average_length': avg_rally_length,
                'longest_rally': max(self.game_state.rally_lengths) if self.game_state.rally_lengths else 0
            },
            'ball_stats': {
                'current_position': self.game_state.ball_position,
                'velocity': self.game_state.ball_velocity,
                'average_speed': np.mean(speeds) if speeds else 0,
                'max_speed': np.max(speeds) if speeds else 0
            },
            'events_last_minute': event_counts,
            'detection_quality': {
                'ball_detection_rate': len([d for d in self.stats_history['ball_detections'] 
                                          if current_time - d.timestamp < 10]) / 10.0,  # Last 10 seconds
                'avg_confidence': np.mean([d.confidence for d in self.stats_history['ball_detections'][-30:]]) 
                                if self.stats_history['ball_detections'] else 0
            }
        }
        
    def analyze_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Analyze single frame and return all detections"""
        # Add frame to buffer
        self.frame_buffer.append(frame.copy())
        
        if len(self.frame_buffer) < 9:
            # Not enough frames for analysis yet
            return {
                'ball_detection': None,
                'players': [],
                'events': [],
                'statistics': self.get_real_time_statistics()
            }
            
        # Prepare input
        input_tensor = self.preprocess_frames(list(self.frame_buffer))
        
        # Run inference
        with torch.no_grad():
            output = self.model(input_tensor)
            
        # Extract detections
        ball_detection = self.detect_ball(output, frame.shape[:2])
        players = self.detect_players(output)
        events = self.detect_events(output)
        
        # Update game state
        self.update_game_state(ball_detection, events, players)
        
        # Get current statistics
        statistics = self.get_real_time_statistics()
        
        return {
            'ball_detection': ball_detection,
            'players': players, 
            'events': events,
            'statistics': statistics,
            'segmentation_mask': output['segmentation'][0].cpu().numpy(),
            'frame_id': len(self.stats_history['ball_detections'])
        }
        
    def process_video_real_time(self, video_source) -> None:
        """Process video source in real-time (camera or file)"""
        if isinstance(video_source, str):
            cap = cv2.VideoCapture(video_source)
        else:
            cap = video_source
            
        self.running = True
        frame_count = 0
        
        try:
            while self.running and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Analyze frame
                results = self.analyze_frame(frame)
                
                # Yield results for real-time processing
                yield frame_count, frame, results
                
                frame_count += 1
                
        finally:
            cap.release()
            self.running = False
            
    def stop_analysis(self):
        """Stop real-time analysis"""
        self.running = False
        
    def reset_game_state(self):
        """Reset game state for new match"""
        self.game_state = GameState()
        self.frame_buffer.clear()
        for key in self.stats_history:
            self.stats_history[key].clear()
        logger.info("Game state reset for new match")

# Utility functions for video annotation
def draw_ball_detection(frame: np.ndarray, ball: BallDetection, color=(0, 255, 0)) -> np.ndarray:
    """Draw ball detection on frame"""
    if ball is None:
        return frame
        
    annotated = frame.copy()
    
    # Draw ball circle
    center = (int(ball.x), int(ball.y))
    radius = max(5, int(20 * ball.confidence))
    cv2.circle(annotated, center, radius, color, 2)
    
    # Draw confidence text
    conf_text = f"{ball.confidence:.2f}"
    cv2.putText(annotated, conf_text, (center[0] + 15, center[1] - 15), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
    return annotated

def draw_player_detections(frame: np.ndarray, players: List[PlayerDetection]) -> np.ndarray:
    """Draw player detections on frame"""
    annotated = frame.copy()
    colors = [(255, 0, 0), (0, 0, 255)]  # Blue and Red for players
    
    for player in players:
        color = colors[player.player_id % len(colors)]
        
        # Draw bounding box
        x, y, w, h = player.bbox
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
        
        # Draw player ID
        cv2.putText(annotated, f"P{player.player_id + 1}", (x, y - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                   
        # Overlay mask (semi-transparent)
        if player.mask is not None and player.mask.shape == frame.shape[:2]:
            mask_colored = np.zeros_like(frame)
            mask_colored[player.mask > 0] = color
            annotated = cv2.addWeighted(annotated, 0.7, mask_colored, 0.3, 0)
            
    return annotated

def draw_statistics_overlay(frame: np.ndarray, stats: Dict[str, Any]) -> np.ndarray:
    """Draw real-time statistics overlay on frame"""
    annotated = frame.copy()
    h, w = frame.shape[:2]
    
    # Background for stats
    overlay = annotated.copy()
    cv2.rectangle(overlay, (10, 10), (400, 200), (0, 0, 0), -1)
    annotated = cv2.addWeighted(annotated, 0.7, overlay, 0.3, 0)
    
    # Draw statistics text
    y_offset = 30
    line_height = 25
    
    stats_text = [
        f"Game Time: {stats['game_duration']:.1f}s",
        f"Score: P1 {stats['score']['player1']} - {stats['score']['player2']} P2",
        f"Current Rally: {stats['current_rally']['length']} shots",
        f"Rally Duration: {stats['current_rally']['duration']:.1f}s",
        f"Avg Rally Length: {stats['rally_stats']['average_length']:.1f}",
        f"Ball Speed: {stats['ball_stats']['average_speed']:.1f} px/s",
        f"Detection Rate: {stats['detection_quality']['ball_detection_rate']:.1%}"
    ]
    
    for i, text in enumerate(stats_text):
        cv2.putText(annotated, text, (20, y_offset + i * line_height),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                   
    return annotated

def create_event_annotation(frame: np.ndarray, events: List[EventDetection]) -> np.ndarray:
    """Create event annotations for recent events"""
    annotated = frame.copy()
    h, w = frame.shape[:2]
    
    # Show recent events (last 2 seconds)
    current_time = time.time()
    recent_events = [e for e in events if current_time - e.timestamp < 2.0]
    
    if recent_events:
        # Event notification area
        event_y = h - 100
        for i, event in enumerate(recent_events[-3:]):  # Show last 3 events
            color = {
                'bounce': (0, 255, 0),
                'net_hit': (0, 255, 255), 
                'serve': (255, 0, 255),
                'rally_end': (255, 255, 0)
            }.get(event.event_type, (255, 255, 255))
            
            event_text = f"{event.event_type.upper()}! ({event.confidence:.2f})"
            alpha = max(0.3, 1.0 - (current_time - event.timestamp) / 2.0)  # Fade out
            
            # Draw with fading effect
            overlay = annotated.copy()
            cv2.putText(overlay, event_text, (20, event_y - i * 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            annotated = cv2.addWeighted(annotated, 1.0 - alpha * 0.7, overlay, alpha * 0.7, 0)
            
    return annotated

# Export main classes
__all__ = ['RealTimeAnalyzer', 'TTNetRealTime', 'GameState', 'BallDetection', 'PlayerDetection', 'EventDetection']