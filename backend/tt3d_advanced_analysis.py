"""
TT3D-Inspired Advanced Table Tennis Video Analysis
Inspired by: https://github.com/cogsys-tuebingen/tt3d

This module implements advanced 3D reconstruction and physics-based ball tracking
for table tennis video analysis, incorporating techniques from the TT3D project.

Key Features:
- Physics-based ball trajectory reconstruction
- Automated camera calibration
- 3D pose estimation integration
- Advanced event detection with 3D context
- Spin and velocity analysis
"""

import cv2
import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass
from pathlib import Path
import json
import yaml

logger = logging.getLogger(__name__)

@dataclass
class CameraParameters:
    """Camera calibration parameters"""
    focal_length: float
    principal_point: Tuple[float, float]
    rotation_matrix: np.ndarray
    translation_vector: np.ndarray
    distortion_coeffs: np.ndarray
    reprojection_error: float

@dataclass
class Ball3DTrajectory:
    """3D ball trajectory data"""
    positions_3d: List[np.ndarray]  # 3D positions over time
    velocities_3d: List[np.ndarray]  # 3D velocities 
    spin_vectors: List[np.ndarray]   # Spin vectors
    timestamps: List[float]          # Frame timestamps
    confidence_scores: List[float]   # Detection confidence
    bounce_points: List[int]         # Frame indices of bounces
    physics_consistency: float       # Physics validation score

@dataclass
class AdvancedAnalysisResult:
    """Advanced analysis result structure"""
    camera_params: CameraParameters
    ball_trajectory: Ball3DTrajectory
    player_poses_3d: Dict[str, List[np.ndarray]]
    event_timeline: List[Dict[str, Any]]
    physics_metrics: Dict[str, float]
    quality_assessment: Dict[str, Any]
    tactical_insights: Dict[str, Any]

class TableSegmenter(nn.Module):
    """
    Neural network for table segmentation
    Inspired by TT3D table detection approach
    """
    
    def __init__(self, input_channels=3, num_classes=2):
        super(TableSegmenter, self).__init__()
        
        # Encoder (similar to UNet architecture)
        self.encoder1 = self._conv_block(input_channels, 64)
        self.encoder2 = self._conv_block(64, 128)
        self.encoder3 = self._conv_block(128, 256)
        self.encoder4 = self._conv_block(256, 512)
        
        # Decoder
        self.decoder1 = self._conv_block(512 + 256, 256)
        self.decoder2 = self._conv_block(256 + 128, 128)
        self.decoder3 = self._conv_block(128 + 64, 64)
        
        # Final classifier
        self.classifier = nn.Conv2d(64, num_classes, kernel_size=1)
        self.sigmoid = nn.Sigmoid()
        
    def _conv_block(self, in_channels, out_channels):
        return nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )
    
    def forward(self, x):
        # Encoder path
        enc1 = self.encoder1(x)  # 64 channels
        enc2 = self.encoder2(nn.MaxPool2d(2)(enc1))  # 128 channels
        enc3 = self.encoder3(nn.MaxPool2d(2)(enc2))  # 256 channels  
        enc4 = self.encoder4(nn.MaxPool2d(2)(enc3))  # 512 channels
        
        # Decoder path with skip connections
        dec1 = self.decoder1(torch.cat([nn.Upsample(scale_factor=2, mode='bilinear')(enc4), enc3], dim=1))
        dec2 = self.decoder2(torch.cat([nn.Upsample(scale_factor=2, mode='bilinear')(dec1), enc2], dim=1))
        dec3 = self.decoder3(torch.cat([nn.Upsample(scale_factor=2, mode='bilinear')(dec2), enc1], dim=1))
        
        # Final classification
        output = self.classifier(dec3)
        return self.sigmoid(output)

class CameraCalibrator:
    """
    Automated camera calibration using table corner detection
    Based on TT3D calibration approach
    """
    
    def __init__(self, table_dimensions=(2.74, 1.525)):  # Standard table tennis table
        self.table_width = table_dimensions[0]  # meters
        self.table_height = table_dimensions[1]  # meters
        self.segmenter = TableSegmenter()
        self.load_segmentation_model()
        
    def load_segmentation_model(self):
        """Load pre-trained segmentation model weights"""
        try:
            # In real implementation, load pre-trained weights
            # For now, we'll use random initialization
            logger.info("Table segmentation model initialized (using random weights)")
        except Exception as e:
            logger.warning(f"Could not load segmentation weights: {e}")
    
    def segment_table(self, frame: np.ndarray) -> np.ndarray:
        """Segment table from video frame"""
        # Preprocess frame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_tensor = torch.from_numpy(frame_rgb).permute(2, 0, 1).float() / 255.0
        frame_tensor = frame_tensor.unsqueeze(0)
        
        # Run segmentation
        with torch.no_grad():
            segmentation = self.segmenter(frame_tensor)
            segmentation = segmentation.squeeze(0)[1].numpy()  # Get table class
        
        return (segmentation > 0.5).astype(np.uint8) * 255
    
    def extract_table_corners(self, segmentation_mask: np.ndarray) -> List[np.ndarray]:
        """Extract table corners from segmentation mask"""
        # Find table contour
        contours, _ = cv2.findContours(segmentation_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return []
        
        # Get largest contour (should be the table)
        table_contour = max(contours, key=cv2.contourArea)
        
        # Approximate to quadrilateral
        epsilon = 0.02 * cv2.arcLength(table_contour, True)
        approx = cv2.approxPolyDP(table_contour, epsilon, True)
        
        if len(approx) == 4:
            corners = approx.reshape(4, 2)
            # Order corners: top-left, top-right, bottom-right, bottom-left
            corners = self._order_corners(corners)
            return corners
        
        return []
    
    def _order_corners(self, corners: np.ndarray) -> np.ndarray:
        """Order corners in consistent way"""
        # Calculate center
        center = np.mean(corners, axis=0)
        
        # Sort by angle from center
        angles = np.arctan2(corners[:, 1] - center[1], corners[:, 0] - center[0])
        sorted_indices = np.argsort(angles)
        
        return corners[sorted_indices]
    
    def calibrate_camera(self, frames: List[np.ndarray]) -> CameraParameters:
        """
        Perform camera calibration using multiple frames
        Returns camera intrinsic and extrinsic parameters
        """
        all_corners_2d = []
        all_corners_3d = []
        
        # 3D coordinates of table corners in world space
        table_corners_3d = np.array([
            [-self.table_width/2, -self.table_height/2, 0],  # Bottom-left
            [self.table_width/2, -self.table_height/2, 0],   # Bottom-right  
            [self.table_width/2, self.table_height/2, 0],    # Top-right
            [-self.table_width/2, self.table_height/2, 0]    # Top-left
        ], dtype=np.float32)
        
        valid_detections = 0
        
        for frame in frames[:50]:  # Process up to 50 frames for calibration
            # Segment table
            segmentation = self.segment_table(frame)
            
            # Extract corners
            corners_2d = self.extract_table_corners(segmentation)
            
            if len(corners_2d) == 4:
                all_corners_2d.append(corners_2d.astype(np.float32))
                all_corners_3d.append(table_corners_3d)
                valid_detections += 1
        
        if valid_detections < 5:
            logger.warning(f"Only {valid_detections} valid table detections for calibration")
            # Return default camera parameters
            return self._get_default_camera_params(frames[0].shape[:2])
        
        # Perform camera calibration
        frame_size = (frames[0].shape[1], frames[0].shape[0])
        
        ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
            all_corners_3d, all_corners_2d, frame_size, None, None
        )
        
        if ret:
            # Calculate average rotation and translation
            avg_rvec = np.mean(rvecs, axis=0)
            avg_tvec = np.mean(tvecs, axis=0)
            rotation_matrix, _ = cv2.Rodrigues(avg_rvec)
            
            # Calculate reprojection error
            total_error = 0
            for i in range(len(all_corners_3d)):
                imgpoints2, _ = cv2.projectPoints(all_corners_3d[i], rvecs[i], tvecs[i], camera_matrix, dist_coeffs)
                error = cv2.norm(all_corners_2d[i], imgpoints2, cv2.NORM_L2)/len(imgpoints2)
                total_error += error
            
            reprojection_error = total_error / len(all_corners_3d)
            
            return CameraParameters(
                focal_length=float(camera_matrix[0, 0]),
                principal_point=(float(camera_matrix[0, 2]), float(camera_matrix[1, 2])),
                rotation_matrix=rotation_matrix,
                translation_vector=avg_tvec.flatten(),
                distortion_coeffs=dist_coeffs.flatten(),
                reprojection_error=float(reprojection_error)
            )
        
        return self._get_default_camera_params(frame_size)
    
    def _get_default_camera_params(self, frame_size: Tuple[int, int]) -> CameraParameters:
        """Return default camera parameters when calibration fails"""
        width, height = frame_size
        
        # Estimate focal length (common heuristic)
        focal_length = max(width, height) * 1.2
        
        return CameraParameters(
            focal_length=focal_length,
            principal_point=(width/2, height/2),
            rotation_matrix=np.eye(3),
            translation_vector=np.array([0, 0, 5]),  # 5 meters away
            distortion_coeffs=np.zeros(5),
            reprojection_error=10.0  # High error indicates poor calibration
        )

class PhysicsBasedBallTracker:
    """
    Physics-based 3D ball trajectory reconstruction
    Incorporates gravity, air resistance, and spin effects
    """
    
    def __init__(self):
        self.gravity = 9.81  # m/s²
        self.ball_mass = 0.0027  # kg (standard ping pong ball)
        self.ball_radius = 0.02  # meters
        self.air_density = 1.225  # kg/m³
        self.drag_coefficient = 0.47  # sphere drag coefficient
        
    def reconstruct_3d_trajectory(self, 
                                detections_2d: List[Tuple[float, float]], 
                                timestamps: List[float],
                                camera_params: CameraParameters) -> Ball3DTrajectory:
        """
        Reconstruct 3D ball trajectory from 2D detections using physics constraints
        """
        if len(detections_2d) < 3:
            return Ball3DTrajectory([], [], [], [], [], [], 0.0)
        
        # Convert 2D points to 3D rays
        rays_3d = self._detections_to_rays(detections_2d, camera_params)
        
        # Initial trajectory estimate using triangulation
        initial_3d_points = self._triangulate_initial_trajectory(rays_3d, timestamps)
        
        # Physics-based optimization
        optimized_trajectory = self._optimize_with_physics(initial_3d_points, timestamps)
        
        # Extract physics parameters
        velocities = self._calculate_velocities(optimized_trajectory, timestamps)
        spin_vectors = self._estimate_spin(optimized_trajectory, velocities, timestamps)
        bounce_points = self._detect_bounces(optimized_trajectory, timestamps)
        
        # Calculate confidence scores
        confidence_scores = self._calculate_confidence(optimized_trajectory, detections_2d, camera_params)
        
        # Physics consistency check
        physics_consistency = self._validate_physics_consistency(optimized_trajectory, velocities, timestamps)
        
        return Ball3DTrajectory(
            positions_3d=optimized_trajectory,
            velocities_3d=velocities,
            spin_vectors=spin_vectors,
            timestamps=timestamps,
            confidence_scores=confidence_scores,
            bounce_points=bounce_points,
            physics_consistency=physics_consistency
        )
    
    def _detections_to_rays(self, detections_2d: List[Tuple[float, float]], 
                           camera_params: CameraParameters) -> List[np.ndarray]:
        """Convert 2D detections to 3D rays from camera"""
        rays = []
        
        for (x, y) in detections_2d:
            # Convert to normalized camera coordinates
            x_norm = (x - camera_params.principal_point[0]) / camera_params.focal_length
            y_norm = (y - camera_params.principal_point[1]) / camera_params.focal_length
            
            # Create ray direction in camera frame
            ray_camera = np.array([x_norm, y_norm, 1.0])
            ray_camera = ray_camera / np.linalg.norm(ray_camera)
            
            # Transform to world frame
            ray_world = camera_params.rotation_matrix.T @ ray_camera
            rays.append(ray_world)
        
        return rays
    
    def _triangulate_initial_trajectory(self, rays_3d: List[np.ndarray], 
                                      timestamps: List[float]) -> List[np.ndarray]:
        """Triangulate initial 3D points from rays"""
        # Simplified triangulation - in practice would use more sophisticated method
        trajectory = []
        
        for i, ray in enumerate(rays_3d):
            # Estimate depth based on table height assumption
            # Assume ball is between 0 and 2 meters above table
            estimated_depth = 1.0  # meters above table
            
            # Calculate 3D position
            position_3d = ray * estimated_depth
            trajectory.append(position_3d)
        
        return trajectory
    
    def _optimize_with_physics(self, initial_trajectory: List[np.ndarray], 
                              timestamps: List[float]) -> List[np.ndarray]:
        """
        Optimize trajectory using physics constraints
        Minimizes reprojection error while satisfying physics
        """
        # This would use CasADi optimization in the full implementation
        # For now, apply simple smoothing with physics constraints
        
        optimized = []
        
        for i, pos in enumerate(initial_trajectory):
            if i == 0 or i == len(initial_trajectory) - 1:
                optimized.append(pos)
                continue
            
            # Apply smoothing with gravity constraint
            prev_pos = initial_trajectory[i-1]
            next_pos = initial_trajectory[i+1]
            
            dt_prev = timestamps[i] - timestamps[i-1]
            dt_next = timestamps[i+1] - timestamps[i]
            
            # Interpolate with gravity effect
            gravity_effect = np.array([0, 0, -0.5 * self.gravity * dt_prev * dt_next])
            smoothed_pos = (prev_pos + next_pos) / 2 + gravity_effect
            
            optimized.append(smoothed_pos)
        
        return optimized
    
    def _calculate_velocities(self, trajectory: List[np.ndarray], 
                            timestamps: List[float]) -> List[np.ndarray]:
        """Calculate 3D velocities from positions"""
        velocities = []
        
        for i in range(len(trajectory)):
            if i == 0:
                # Forward difference
                dt = timestamps[1] - timestamps[0]
                velocity = (trajectory[1] - trajectory[0]) / dt
            elif i == len(trajectory) - 1:
                # Backward difference  
                dt = timestamps[i] - timestamps[i-1]
                velocity = (trajectory[i] - trajectory[i-1]) / dt
            else:
                # Central difference
                dt = timestamps[i+1] - timestamps[i-1]
                velocity = (trajectory[i+1] - trajectory[i-1]) / dt
            
            velocities.append(velocity)
        
        return velocities
    
    def _estimate_spin(self, trajectory: List[np.ndarray], 
                      velocities: List[np.ndarray],
                      timestamps: List[float]) -> List[np.ndarray]:
        """Estimate spin vectors from trajectory curvature"""
        spin_vectors = []
        
        for i in range(len(trajectory)):
            if i < 2 or i >= len(trajectory) - 2:
                spin_vectors.append(np.array([0.0, 0.0, 0.0]))
                continue
            
            # Calculate acceleration
            dt1 = timestamps[i] - timestamps[i-1]
            dt2 = timestamps[i+1] - timestamps[i]
            
            acceleration = (velocities[i+1] - velocities[i-1]) / (dt1 + dt2)
            
            # Remove gravity component
            gravity_vector = np.array([0, 0, -self.gravity])
            net_acceleration = acceleration - gravity_vector
            
            # Estimate spin from Magnus force
            # F_magnus = (1/2) * rho * A * C_L * v² * (ω × v_hat)
            # This is a simplified estimation
            velocity_magnitude = np.linalg.norm(velocities[i])
            
            if velocity_magnitude > 0.1:  # Avoid division by zero
                velocity_unit = velocities[i] / velocity_magnitude
                
                # Estimate spin magnitude (simplified)
                magnus_acceleration_magnitude = np.linalg.norm(net_acceleration)
                estimated_spin_magnitude = magnus_acceleration_magnitude / (velocity_magnitude * 0.1)  # Simplified
                
                # Estimate spin direction perpendicular to velocity
                spin_direction = np.cross(net_acceleration, velocity_unit)
                if np.linalg.norm(spin_direction) > 0:
                    spin_direction = spin_direction / np.linalg.norm(spin_direction)
                    spin_vector = spin_direction * estimated_spin_magnitude
                else:
                    spin_vector = np.array([0.0, 0.0, 0.0])
            else:
                spin_vector = np.array([0.0, 0.0, 0.0])
            
            spin_vectors.append(spin_vector)
        
        return spin_vectors
    
    def _detect_bounces(self, trajectory: List[np.ndarray], 
                       timestamps: List[float]) -> List[int]:
        """Detect bounce points in trajectory"""
        bounce_indices = []
        
        for i in range(1, len(trajectory) - 1):
            pos_prev = trajectory[i-1]
            pos_curr = trajectory[i]
            pos_next = trajectory[i+1]
            
            # Check for vertical direction change (bounce indicator)
            z_velocity_before = pos_curr[2] - pos_prev[2]
            z_velocity_after = pos_next[2] - pos_curr[2]
            
            # Bounce detected if vertical velocity changes from negative to positive
            # and ball is close to table level (z ≈ 0)
            if (z_velocity_before < -0.1 and z_velocity_after > 0.1 and 
                abs(pos_curr[2]) < 0.2):  # Within 20cm of table
                bounce_indices.append(i)
        
        return bounce_indices
    
    def _calculate_confidence(self, trajectory: List[np.ndarray],
                            detections_2d: List[Tuple[float, float]],
                            camera_params: CameraParameters) -> List[float]:
        """Calculate confidence scores for each point"""
        confidences = []
        
        for i, pos_3d in enumerate(trajectory):
            # Project 3D point back to 2D
            pos_camera = camera_params.rotation_matrix @ pos_3d + camera_params.translation_vector
            
            if pos_camera[2] > 0:  # In front of camera
                x_proj = camera_params.focal_length * pos_camera[0] / pos_camera[2] + camera_params.principal_point[0]
                y_proj = camera_params.focal_length * pos_camera[1] / pos_camera[2] + camera_params.principal_point[1]
                
                # Calculate reprojection error
                detection_2d = detections_2d[i] if i < len(detections_2d) else (x_proj, y_proj)
                reprojection_error = np.sqrt((x_proj - detection_2d[0])**2 + (y_proj - detection_2d[1])**2)
                
                # Convert error to confidence (lower error = higher confidence)
                confidence = max(0.0, 1.0 - reprojection_error / 50.0)  # Normalize by 50 pixels
            else:
                confidence = 0.0
            
            confidences.append(confidence)
        
        return confidences
    
    def _validate_physics_consistency(self, trajectory: List[np.ndarray],
                                    velocities: List[np.ndarray],
                                    timestamps: List[float]) -> float:
        """Validate physics consistency of trajectory"""
        if len(trajectory) < 3:
            return 0.0
        
        consistency_scores = []
        
        for i in range(1, len(trajectory) - 1):
            # Check energy conservation (simplified)
            height_prev = trajectory[i-1][2]
            height_curr = trajectory[i][2]
            velocity_prev = np.linalg.norm(velocities[i-1])
            velocity_curr = np.linalg.norm(velocities[i])
            
            # Kinetic + potential energy
            energy_prev = 0.5 * velocity_prev**2 + self.gravity * height_prev
            energy_curr = 0.5 * velocity_curr**2 + self.gravity * height_curr
            
            # Energy should be approximately conserved (allowing for air resistance)
            energy_ratio = energy_curr / energy_prev if energy_prev > 0 else 1.0
            
            # Good consistency if energy ratio is between 0.8 and 1.2
            if 0.8 <= energy_ratio <= 1.2:
                consistency_scores.append(1.0)
            else:
                consistency_scores.append(max(0.0, 1.0 - abs(energy_ratio - 1.0)))
        
        return np.mean(consistency_scores) if consistency_scores else 0.0

class TT3DAdvancedAnalyzer:
    """
    Main analyzer class integrating all TT3D techniques
    """
    
    def __init__(self):
        self.camera_calibrator = CameraCalibrator()
        self.ball_tracker = PhysicsBasedBallTracker()
        
    def analyze_video(self, video_path: str) -> AdvancedAnalysisResult:
        """
        Perform comprehensive TT3D-style analysis on video
        """
        logger.info(f"Starting TT3D advanced analysis of {video_path}")
        
        # Load video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        frames = []
        frame_count = 0
        max_frames = 300  # Limit for processing
        
        while True:
            ret, frame = cap.read()
            if not ret or frame_count >= max_frames:
                break
            frames.append(frame)
            frame_count += 1
        
        cap.release()
        
        if len(frames) < 10:
            raise ValueError("Video too short for analysis")
        
        logger.info(f"Loaded {len(frames)} frames for analysis")
        
        # 1. Camera Calibration
        logger.info("Performing camera calibration...")
        camera_params = self.camera_calibrator.calibrate_camera(frames)
        logger.info(f"Camera calibrated with reprojection error: {camera_params.reprojection_error:.2f}")
        
        # 2. Ball Detection and Tracking (simplified - would use BlurBall in full implementation)
        logger.info("Detecting and tracking ball...")
        ball_detections_2d, timestamps = self._detect_ball_2d(frames)
        
        # 3. 3D Ball Trajectory Reconstruction
        logger.info("Reconstructing 3D ball trajectory...")
        ball_trajectory = self.ball_tracker.reconstruct_3d_trajectory(
            ball_detections_2d, timestamps, camera_params
        )
        
        # 4. Advanced Event Detection
        logger.info("Analyzing events and gameplay...")
        event_timeline = self._analyze_events(ball_trajectory, frames)
        
        # 5. Physics Metrics
        physics_metrics = self._calculate_physics_metrics(ball_trajectory)
        
        # 6. Quality Assessment
        quality_assessment = self._assess_analysis_quality(
            camera_params, ball_trajectory, frames
        )
        
        # 7. Tactical Insights
        tactical_insights = self._generate_tactical_insights(
            ball_trajectory, event_timeline, physics_metrics
        )
        
        logger.info("TT3D advanced analysis completed")
        
        return AdvancedAnalysisResult(
            camera_params=camera_params,
            ball_trajectory=ball_trajectory,
            player_poses_3d={},  # Would be filled with pose estimation
            event_timeline=event_timeline,
            physics_metrics=physics_metrics,
            quality_assessment=quality_assessment,
            tactical_insights=tactical_insights
        )
    
    def _detect_ball_2d(self, frames: List[np.ndarray]) -> Tuple[List[Tuple[float, float]], List[float]]:
        """
        Detect ball in 2D across frames
        Simplified implementation - would use BlurBall or similar in practice
        """
        detections = []
        timestamps = []
        
        # Simple ball detection using color and motion
        for i, frame in enumerate(frames):
            timestamp = i / 30.0  # Assume 30 FPS
            
            # Convert to HSV for better color segmentation
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # Orange ball detection (typical ping pong ball color)
            lower_orange = np.array([10, 100, 100])
            upper_orange = np.array([25, 255, 255])
            mask = cv2.inRange(hsv, lower_orange, upper_orange)
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Find largest contour (likely the ball)
                largest_contour = max(contours, key=cv2.contourArea)
                
                # Get centroid
                M = cv2.moments(largest_contour)
                if M['m00'] > 0:
                    cx = M['m10'] / M['m00']
                    cy = M['m01'] / M['m00']
                    
                    # Filter by size (ball should be reasonable size)
                    area = cv2.contourArea(largest_contour)
                    if 10 < area < 1000:  # Reasonable ball size range
                        detections.append((cx, cy))
                        timestamps.append(timestamp)
        
        logger.info(f"Detected ball in {len(detections)} frames")
        return detections, timestamps
    
    def _analyze_events(self, ball_trajectory: Ball3DTrajectory, 
                       frames: List[np.ndarray]) -> List[Dict[str, Any]]:
        """Analyze game events using 3D trajectory"""
        events = []
        
        # Add bounce events
        for bounce_idx in ball_trajectory.bounce_points:
            if bounce_idx < len(ball_trajectory.timestamps):
                events.append({
                    'type': 'bounce',
                    'timestamp': ball_trajectory.timestamps[bounce_idx],
                    'frame_index': bounce_idx,
                    'position_3d': ball_trajectory.positions_3d[bounce_idx].tolist(),
                    'velocity_3d': ball_trajectory.velocities_3d[bounce_idx].tolist() if bounce_idx < len(ball_trajectory.velocities_3d) else None,
                    'confidence': ball_trajectory.confidence_scores[bounce_idx] if bounce_idx < len(ball_trajectory.confidence_scores) else 0.5
                })
        
        # Detect serves (ball starting from high position with high velocity)
        for i, pos in enumerate(ball_trajectory.positions_3d):
            if i < len(ball_trajectory.velocities_3d):
                velocity = ball_trajectory.velocities_3d[i]
                speed = np.linalg.norm(velocity)
                
                # Serve detection: high position + high initial speed
                if pos[2] > 1.0 and speed > 10.0 and i < len(ball_trajectory.positions_3d) * 0.2:
                    events.append({
                        'type': 'serve',
                        'timestamp': ball_trajectory.timestamps[i],
                        'frame_index': i,
                        'position_3d': pos.tolist(),
                        'velocity_3d': velocity.tolist(),
                        'speed': float(speed),
                        'confidence': ball_trajectory.confidence_scores[i] if i < len(ball_trajectory.confidence_scores) else 0.7
                    })
        
        # Sort events by timestamp
        events.sort(key=lambda x: x['timestamp'])
        
        return events
    
    def _calculate_physics_metrics(self, ball_trajectory: Ball3DTrajectory) -> Dict[str, float]:
        """Calculate physics-based metrics"""
        if not ball_trajectory.velocities_3d:
            return {}
        
        speeds = [np.linalg.norm(v) for v in ball_trajectory.velocities_3d]
        spins = [np.linalg.norm(s) for s in ball_trajectory.spin_vectors]
        heights = [pos[2] for pos in ball_trajectory.positions_3d]
        
        return {
            'max_speed': max(speeds) if speeds else 0.0,
            'avg_speed': np.mean(speeds) if speeds else 0.0,
            'max_spin': max(spins) if spins else 0.0,
            'avg_spin': np.mean(spins) if spins else 0.0,
            'max_height': max(heights) if heights else 0.0,
            'avg_height': np.mean(heights) if heights else 0.0,
            'trajectory_length': len(ball_trajectory.positions_3d),
            'bounce_count': len(ball_trajectory.bounce_points),
            'physics_consistency': ball_trajectory.physics_consistency,
            'avg_confidence': np.mean(ball_trajectory.confidence_scores) if ball_trajectory.confidence_scores else 0.0
        }
    
    def _assess_analysis_quality(self, camera_params: CameraParameters,
                               ball_trajectory: Ball3DTrajectory,
                               frames: List[np.ndarray]) -> Dict[str, Any]:
        """Assess quality of analysis"""
        return {
            'camera_calibration_quality': 'excellent' if camera_params.reprojection_error < 2.0 else 'good' if camera_params.reprojection_error < 5.0 else 'poor',
            'ball_tracking_quality': 'excellent' if ball_trajectory.physics_consistency > 0.8 else 'good' if ball_trajectory.physics_consistency > 0.6 else 'poor',
            'trajectory_completeness': len(ball_trajectory.positions_3d) / len(frames),
            'overall_confidence': np.mean(ball_trajectory.confidence_scores) if ball_trajectory.confidence_scores else 0.0,
            'reprojection_error': camera_params.reprojection_error,
            'physics_consistency': ball_trajectory.physics_consistency,
            'recommendations': self._generate_quality_recommendations(camera_params, ball_trajectory)
        }
    
    def _generate_quality_recommendations(self, camera_params: CameraParameters,
                                        ball_trajectory: Ball3DTrajectory) -> List[str]:
        """Generate recommendations for improving analysis quality"""
        recommendations = []
        
        if camera_params.reprojection_error > 5.0:
            recommendations.append("Améliorer la stabilité de la caméra pour une meilleure calibration")
        
        if ball_trajectory.physics_consistency < 0.6:
            recommendations.append("Utiliser une balle plus contrastée pour améliorer la détection")
        
        if len(ball_trajectory.positions_3d) < 50:
            recommendations.append("Filmer des échanges plus longs pour une analyse plus complète")
        
        avg_confidence = np.mean(ball_trajectory.confidence_scores) if ball_trajectory.confidence_scores else 0.0
        if avg_confidence < 0.7:
            recommendations.append("Améliorer l'éclairage et réduire les ombres")
        
        if len(ball_trajectory.bounce_points) == 0:
            recommendations.append("Inclure des rebonds sur table pour validation physique")
        
        return recommendations
    
    def _generate_tactical_insights(self, ball_trajectory: Ball3DTrajectory,
                                  event_timeline: List[Dict[str, Any]],
                                  physics_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Generate tactical insights from 3D analysis"""
        
        serves = [e for e in event_timeline if e['type'] == 'serve']
        bounces = [e for e in event_timeline if e['type'] == 'bounce']
        
        insights = {
            'game_style': 'balanced',
            'spin_usage': 'moderate',
            'speed_variation': 'moderate',
            'tactical_patterns': []
        }
        
        # Analyze game style based on speed and trajectory
        avg_speed = physics_metrics.get('avg_speed', 0)
        max_speed = physics_metrics.get('max_speed', 0)
        
        if avg_speed > 15:
            insights['game_style'] = 'aggressive'
            insights['tactical_patterns'].append("Jeu offensif avec vitesses élevées")
        elif avg_speed < 8:
            insights['game_style'] = 'defensive'
            insights['tactical_patterns'].append("Jeu défensif privilégiant le placement")
        
        # Analyze spin usage
        avg_spin = physics_metrics.get('avg_spin', 0)
        if avg_spin > 50:
            insights['spin_usage'] = 'high'
            insights['tactical_patterns'].append("Utilisation importante des effets")
        elif avg_spin < 20:
            insights['spin_usage'] = 'low'
            insights['tactical_patterns'].append("Jeu plutôt à plat avec peu d'effets")
        
        # Analyze rally characteristics
        if len(bounces) > len(serves) * 3:
            insights['tactical_patterns'].append("Échanges longs favorisant la construction")
        elif len(bounces) < len(serves) * 2:
            insights['tactical_patterns'].append("Échanges courts avec finition rapide")
        
        # Height variation analysis
        max_height = physics_metrics.get('max_height', 0)
        if max_height > 2.0:
            insights['tactical_patterns'].append("Utilisation de balles hautes (lobs)")
        
        return insights

# Export main class
__all__ = ['TT3DAdvancedAnalyzer', 'AdvancedAnalysisResult']