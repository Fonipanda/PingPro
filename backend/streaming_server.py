"""
Real-Time Video Streaming Server for Table Tennis Analysis
Provides WebSocket-based live video analysis and annotation
"""

import asyncio
import websockets
import json
import cv2
import base64
import numpy as np
from typing import Dict, Any, Optional
import logging
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import threading
import time
from pathlib import Path

from real_time_ttnet_analyzer import (
    RealTimeAnalyzer, 
    draw_ball_detection, 
    draw_player_detections,
    draw_statistics_overlay,
    create_event_annotation
)

logger = logging.getLogger(__name__)

class VideoStreamManager:
    """Manages video streams and real-time analysis"""
    
    def __init__(self):
        self.analyzer = RealTimeAnalyzer()
        self.active_connections: Dict[str, WebSocket] = {}
        self.current_stream = None
        self.streaming = False
        self.stream_thread = None
        
        # Load model weights if available
        weights_path = Path("models/ttnet_weights.pth")
        if weights_path.exists():
            self.analyzer.load_pretrained_weights(str(weights_path))
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a new client"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")
        
        # Send initial status
        await self.send_message(client_id, {
            "type": "status",
            "message": "Connected to PingPro Real-Time Analyzer",
            "analyzer_ready": True
        })
        
    def disconnect(self, client_id: str):
        """Disconnect a client"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")
            
    async def send_message(self, client_id: str, message: Dict[str, Any]):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
            
        disconnected_clients = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
                
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
            
    def start_video_analysis(self, video_source: str):
        """Start real-time video analysis"""
        if self.streaming:
            logger.warning("Analysis already running")
            return False
            
        self.current_stream = video_source
        self.streaming = True
        self.stream_thread = threading.Thread(target=self._run_analysis)
        self.stream_thread.start()
        logger.info(f"Started video analysis for {video_source}")
        return True
        
    def stop_video_analysis(self):
        """Stop video analysis"""
        self.streaming = False
        if self.stream_thread:
            self.stream_thread.join(timeout=5)
        self.analyzer.stop_analysis()
        logger.info("Stopped video analysis")
        
    def _run_analysis(self):
        """Run video analysis in separate thread"""
        try:
            for frame_id, frame, results in self.analyzer.process_video_real_time(self.current_stream):
                if not self.streaming:
                    break
                    
                # Create annotated frame
                annotated_frame = self._create_annotated_frame(frame, results)
                
                # Encode frame for transmission
                encoded_frame = self._encode_frame(annotated_frame)
                
                # Prepare analysis results
                analysis_data = self._prepare_analysis_data(results, frame_id)
                
                # Send to all connected clients
                asyncio.run(self.broadcast_message({
                    "type": "frame_analysis",
                    "frame_id": frame_id,
                    "frame_data": encoded_frame,
                    "analysis": analysis_data,
                    "timestamp": time.time()
                }))
                
                # Throttle to reasonable frame rate
                time.sleep(0.033)  # ~30 FPS
                
        except Exception as e:
            logger.error(f"Error in analysis thread: {e}")
            asyncio.run(self.broadcast_message({
                "type": "error",
                "message": f"Analysis error: {str(e)}"
            }))
        finally:
            self.streaming = False
            
    def _create_annotated_frame(self, frame: np.ndarray, results: Dict[str, Any]) -> np.ndarray:
        """Create annotated frame with all visualizations"""
        annotated = frame.copy()
        
        # Draw ball detection
        if results['ball_detection']:
            annotated = draw_ball_detection(annotated, results['ball_detection'])
            
        # Draw player detections
        if results['players']:
            annotated = draw_player_detections(annotated, results['players'])
            
        # Draw statistics overlay
        if results['statistics']:
            annotated = draw_statistics_overlay(annotated, results['statistics'])
            
        # Draw event annotations
        if results['events']:
            annotated = create_event_annotation(annotated, results['events'])
            
        return annotated
        
    def _encode_frame(self, frame: np.ndarray) -> str:
        """Encode frame for web transmission"""
        # Resize for web transmission
        height, width = frame.shape[:2]
        if width > 640:
            scale = 640 / width
            new_width = 640
            new_height = int(height * scale)
            frame = cv2.resize(frame, (new_width, new_height))
            
        # Encode as JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        
        # Convert to base64
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        return frame_b64
        
    def _prepare_analysis_data(self, results: Dict[str, Any], frame_id: int) -> Dict[str, Any]:
        """Prepare analysis data for client"""
        analysis_data = {
            "frame_id": frame_id,
            "ball": None,
            "players": [],
            "events": [],
            "statistics": results.get('statistics', {}),
            "detections_quality": {}
        }
        
        # Ball detection data
        if results['ball_detection']:
            ball = results['ball_detection']
            analysis_data["ball"] = {
                "x": ball.x,
                "y": ball.y,
                "confidence": ball.confidence,
                "timestamp": ball.timestamp
            }
            
        # Player detection data
        for player in results.get('players', []):
            analysis_data["players"].append({
                "id": player.player_id,
                "bbox": player.bbox,
                "confidence": player.confidence
            })
            
        # Event detection data
        for event in results.get('events', []):
            analysis_data["events"].append({
                "type": event.event_type,
                "confidence": event.confidence,
                "timestamp": event.timestamp
            })
            
        return analysis_data
        
    async def handle_client_message(self, client_id: str, message: Dict[str, Any]):
        """Handle incoming client messages"""
        msg_type = message.get("type")
        
        if msg_type == "start_analysis":
            video_source = message.get("video_source", 0)  # Default to webcam
            success = self.start_video_analysis(video_source)
            await self.send_message(client_id, {
                "type": "analysis_status",
                "status": "started" if success else "failed",
                "message": "Analysis started" if success else "Could not start analysis"
            })
            
        elif msg_type == "stop_analysis":
            self.stop_video_analysis()
            await self.broadcast_message({
                "type": "analysis_status", 
                "status": "stopped",
                "message": "Analysis stopped"
            })
            
        elif msg_type == "reset_game":
            self.analyzer.reset_game_state()
            await self.broadcast_message({
                "type": "game_reset",
                "message": "Game state reset"
            })
            
        elif msg_type == "get_statistics":
            stats = self.analyzer.get_real_time_statistics()
            await self.send_message(client_id, {
                "type": "current_statistics",
                "statistics": stats
            })
            
        elif msg_type == "update_score":
            # Manual score update
            player1_score = message.get("player1_score", 0)
            player2_score = message.get("player2_score", 0)
            self.analyzer.game_state.player1_score = player1_score
            self.analyzer.game_state.player2_score = player2_score
            
            await self.broadcast_message({
                "type": "score_updated",
                "score": {
                    "player1": player1_score,
                    "player2": player2_score
                }
            })

# Global stream manager instance
stream_manager = VideoStreamManager()

# FastAPI WebSocket endpoints
async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    """Main WebSocket endpoint for real-time communication"""
    if not client_id:
        client_id = f"client_{int(time.time())}"
        
    await stream_manager.connect(websocket, client_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await stream_manager.handle_client_message(client_id, message)
            
    except WebSocketDisconnect:
        stream_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        stream_manager.disconnect(client_id)

def generate_video_stream():
    """Generate video stream for HTTP streaming"""
    while stream_manager.streaming:
        if hasattr(stream_manager, '_current_frame'):
            frame = stream_manager._current_frame
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            time.sleep(0.1)

def get_video_stream():
    """HTTP endpoint for video streaming"""
    return StreamingResponse(
        generate_video_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

# Analysis utilities
class MatchRecorder:
    """Records match data for post-analysis"""
    
    def __init__(self):
        self.match_data = {
            "frames": [],
            "detections": [],
            "events": [],
            "statistics_history": []
        }
        self.recording = False
        
    def start_recording(self):
        """Start recording match data"""
        self.recording = True
        self.match_data = {
            "frames": [],
            "detections": [], 
            "events": [],
            "statistics_history": []
        }
        
    def stop_recording(self):
        """Stop recording and return data"""
        self.recording = False
        return self.match_data.copy()
        
    def add_frame_data(self, frame_id: int, results: Dict[str, Any]):
        """Add frame analysis data"""
        if not self.recording:
            return
            
        self.match_data["frames"].append(frame_id)
        
        if results.get('ball_detection'):
            ball = results['ball_detection']
            self.match_data["detections"].append({
                "frame_id": frame_id,
                "type": "ball",
                "x": ball.x,
                "y": ball.y,
                "confidence": ball.confidence,
                "timestamp": ball.timestamp
            })
            
        for event in results.get('events', []):
            self.match_data["events"].append({
                "frame_id": frame_id,
                "type": event.event_type,
                "confidence": event.confidence,
                "timestamp": event.timestamp
            })
            
        if results.get('statistics'):
            self.match_data["statistics_history"].append({
                "frame_id": frame_id,
                "timestamp": time.time(),
                "statistics": results['statistics']
            })

# Global recorder instance  
match_recorder = MatchRecorder()

# Export main components
__all__ = [
    'VideoStreamManager', 
    'stream_manager', 
    'websocket_endpoint', 
    'get_video_stream',
    'MatchRecorder',
    'match_recorder'
]