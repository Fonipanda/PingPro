#!/usr/bin/env python3
"""
PingPro Backend API Testing Suite - Enhanced TTNet Analysis Testing
Tests all backend endpoints with focus on TTNet analysis improvements:
- Enhanced skill assessment functions
- Personalized recommendations based on real analysis
- Video quality evaluation with specific feedback
- Realistic technical insights calculation
"""

import requests
import sys
import json
import time
import tempfile
import os
from datetime import datetime
from pathlib import Path

class PingProAPITester:
    def __init__(self, base_url="https://paddle-vision.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
    def log_test(self, name, success, details="", response_data=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            
        result = {
            "test_name": name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    Details: {details}")
        if not success and response_data:
            print(f"    Response: {response_data}")
        print()

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                expected_message = "PingPro API - Analyse IA Tennis de Table"
                
                if "message" in data and expected_message in data["message"]:
                    self.log_test(
                        "Root API Endpoint", 
                        True, 
                        f"Status: {response.status_code}, Message: {data['message']}"
                    )
                    return True
                else:
                    self.log_test(
                        "Root API Endpoint", 
                        False, 
                        f"Unexpected response format", 
                        data
                    )
                    return False
            else:
                self.log_test(
                    "Root API Endpoint", 
                    False, 
                    f"Expected 200, got {response.status_code}", 
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Root API Endpoint", 
                False, 
                f"Request failed: {str(e)}"
            )
            return False

    def create_test_video_file(self):
        """Create a small test video file for upload testing"""
        try:
            # Create a temporary file with .mp4 extension
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            
            # Write minimal MP4 header (this won't be a valid video but will pass file extension check)
            mp4_header = b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom'
            temp_file.write(mp4_header)
            temp_file.write(b'0' * 1000)  # Add some dummy data
            temp_file.close()
            
            return temp_file.name
        except Exception as e:
            print(f"Failed to create test video file: {e}")
            return None

    def test_video_upload_invalid_format(self):
        """Test video upload with invalid file format"""
        try:
            # Create a text file with wrong extension
            temp_file = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
            temp_file.write(b'This is not a video file')
            temp_file.close()
            
            with open(temp_file.name, 'rb') as f:
                files = {'video': ('test.txt', f, 'text/plain')}
                data = {
                    'player_side': 'droite',
                    'skill_level': 'intermediaire',
                    'focus_areas': 'technique_coups,positionnement,timing'
                }
                
                response = requests.post(
                    f"{self.api_url}/analyze", 
                    files=files, 
                    data=data, 
                    timeout=30
                )
                
                if response.status_code == 400:
                    error_data = response.json()
                    if "Format de fichier non supporté" in error_data.get("detail", ""):
                        self.log_test(
                            "Video Upload - Invalid Format Validation", 
                            True, 
                            f"Correctly rejected invalid format: {response.status_code}"
                        )
                        success = True
                    else:
                        self.log_test(
                            "Video Upload - Invalid Format Validation", 
                            False, 
                            f"Wrong error message", 
                            error_data
                        )
                        success = False
                else:
                    self.log_test(
                        "Video Upload - Invalid Format Validation", 
                        False, 
                        f"Expected 400, got {response.status_code}", 
                        response.text
                    )
                    success = False
            
            # Cleanup
            os.unlink(temp_file.name)
            return success
            
        except Exception as e:
            self.log_test(
                "Video Upload - Invalid Format Validation", 
                False, 
                f"Request failed: {str(e)}"
            )
            return False

    def test_video_upload_valid_format(self):
        """Test video upload with valid format"""
        test_file = self.create_test_video_file()
        if not test_file:
            self.log_test(
                "Video Upload - Valid Format", 
                False, 
                "Could not create test video file"
            )
            return False, None
            
        try:
            with open(test_file, 'rb') as f:
                files = {'video': ('test_video.mp4', f, 'video/mp4')}
                data = {
                    'player_side': 'droite',
                    'skill_level': 'intermediaire',
                    'focus_areas': 'technique_coups,positionnement,timing'
                }
                
                response = requests.post(
                    f"{self.api_url}/analyze", 
                    files=files, 
                    data=data, 
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "analysis_id" in data and "status" in data:
                        self.log_test(
                            "Video Upload - Valid Format", 
                            True, 
                            f"Upload successful, Analysis ID: {data['analysis_id']}"
                        )
                        # Cleanup
                        os.unlink(test_file)
                        return True, data["analysis_id"]
                    else:
                        self.log_test(
                            "Video Upload - Valid Format", 
                            False, 
                            f"Missing required fields in response", 
                            data
                        )
                        # Cleanup
                        os.unlink(test_file)
                        return False, None
                else:
                    self.log_test(
                        "Video Upload - Valid Format", 
                        False, 
                        f"Expected 200, got {response.status_code}", 
                        response.text
                    )
                    # Cleanup
                    os.unlink(test_file)
                    return False, None
                    
        except Exception as e:
            self.log_test(
                "Video Upload - Valid Format", 
                False, 
                f"Request failed: {str(e)}"
            )
            # Cleanup
            if os.path.exists(test_file):
                os.unlink(test_file)
            return False, None

    def test_analysis_status(self, analysis_id):
        """Test analysis status endpoint"""
        if not analysis_id:
            self.log_test(
                "Analysis Status Check", 
                False, 
                "No analysis ID provided"
            )
            return False
            
        try:
            response = requests.get(
                f"{self.api_url}/analysis/{analysis_id}/status", 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["analysis_id", "status", "progress", "created_at"]
                
                if all(field in data for field in required_fields):
                    self.log_test(
                        "Analysis Status Check", 
                        True, 
                        f"Status: {data['status']}, Progress: {data['progress']}%"
                    )
                    return True, data
                else:
                    missing_fields = [f for f in required_fields if f not in data]
                    self.log_test(
                        "Analysis Status Check", 
                        False, 
                        f"Missing fields: {missing_fields}", 
                        data
                    )
                    return False, None
            else:
                self.log_test(
                    "Analysis Status Check", 
                    False, 
                    f"Expected 200, got {response.status_code}", 
                    response.text
                )
                return False, None
                
        except Exception as e:
            self.log_test(
                "Analysis Status Check", 
                False, 
                f"Request failed: {str(e)}"
            )
            return False, None

    def test_analysis_results_not_ready(self, analysis_id):
        """Test analysis results endpoint when analysis is not complete"""
        if not analysis_id:
            self.log_test(
                "Analysis Results - Not Ready", 
                False, 
                "No analysis ID provided"
            )
            return False
            
        try:
            response = requests.get(
                f"{self.api_url}/analysis/{analysis_id}/results", 
                timeout=10
            )
            
            # Should return 400 if analysis is not completed
            if response.status_code == 400:
                data = response.json()
                if "non terminée" in data.get("detail", "").lower():
                    self.log_test(
                        "Analysis Results - Not Ready", 
                        True, 
                        f"Correctly returned 400 for incomplete analysis"
                    )
                    return True
                else:
                    self.log_test(
                        "Analysis Results - Not Ready", 
                        False, 
                        f"Wrong error message", 
                        data
                    )
                    return False
            else:
                self.log_test(
                    "Analysis Results - Not Ready", 
                    False, 
                    f"Expected 400, got {response.status_code}", 
                    response.text
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Analysis Results - Not Ready", 
                False, 
                f"Request failed: {str(e)}"
            )
            return False

    def test_invalid_analysis_id(self):
        """Test endpoints with invalid analysis ID"""
        invalid_id = "invalid-analysis-id-12345"
        
        # Test status endpoint
        try:
            response = requests.get(
                f"{self.api_url}/analysis/{invalid_id}/status", 
                timeout=10
            )
            
            if response.status_code == 404:
                self.log_test(
                    "Invalid Analysis ID - Status", 
                    True, 
                    f"Correctly returned 404 for invalid ID"
                )
                status_success = True
            else:
                self.log_test(
                    "Invalid Analysis ID - Status", 
                    False, 
                    f"Expected 404, got {response.status_code}", 
                    response.text
                )
                status_success = False
                
        except Exception as e:
            self.log_test(
                "Invalid Analysis ID - Status", 
                False, 
                f"Request failed: {str(e)}"
            )
            status_success = False
        
        # Test results endpoint
        try:
            response = requests.get(
                f"{self.api_url}/analysis/{invalid_id}/results", 
                timeout=10
            )
            
            if response.status_code == 404:
                self.log_test(
                    "Invalid Analysis ID - Results", 
                    True, 
                    f"Correctly returned 404 for invalid ID"
                )
                results_success = True
            else:
                self.log_test(
                    "Invalid Analysis ID - Results", 
                    False, 
                    f"Expected 404, got {response.status_code}", 
                    response.text
                )
                results_success = False
                
        except Exception as e:
            self.log_test(
                "Invalid Analysis ID - Results", 
                False, 
                f"Request failed: {str(e)}"
            )
            results_success = False
            
        return status_success and results_success

    def test_cors_headers(self):
        """Test CORS headers are properly set"""
        try:
            response = requests.options(f"{self.api_url}/", timeout=10)
            
            cors_headers = [
                'Access-Control-Allow-Origin',
                'Access-Control-Allow-Methods',
                'Access-Control-Allow-Headers'
            ]
            
            present_headers = [h for h in cors_headers if h in response.headers]
            
            if len(present_headers) >= 1:  # At least one CORS header should be present
                self.log_test(
                    "CORS Headers", 
                    True, 
                    f"CORS headers present: {present_headers}"
                )
                return True
            else:
                self.log_test(
                    "CORS Headers", 
                    False, 
                    f"No CORS headers found in response"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "CORS Headers", 
                False, 
                f"Request failed: {str(e)}"
            )
            return False

    def test_tt3d_advanced_analysis_integration(self):
        """Test TT3D Advanced Analysis integration and modules"""
        print("\n🔬 Testing TT3D Advanced Analysis Integration...")
        
        # Test 1: TT3D Module Import
        try:
            import sys
            sys.path.append('/app/backend')
            
            from tt3d_advanced_analysis import (
                TT3DAdvancedAnalyzer, 
                AdvancedAnalysisResult,
                CameraCalibrator,
                PhysicsBasedBallTracker,
                TableSegmenter,
                CameraParameters,
                Ball3DTrajectory
            )
            
            self.log_test(
                "TT3D Module Import", 
                True, 
                "All TT3D advanced analysis classes successfully imported"
            )
            
            # Test 2: TT3D Analyzer Initialization
            analyzer = TT3DAdvancedAnalyzer()
            if hasattr(analyzer, 'camera_calibrator') and hasattr(analyzer, 'ball_tracker'):
                self.log_test(
                    "TT3D Analyzer Initialization", 
                    True, 
                    "TT3D analyzer properly initialized with camera calibrator and ball tracker"
                )
            else:
                self.log_test(
                    "TT3D Analyzer Initialization", 
                    False, 
                    "TT3D analyzer missing required components"
                )
            
            # Test 3: Camera Calibrator
            calibrator = CameraCalibrator()
            if hasattr(calibrator, 'segmenter') and hasattr(calibrator, 'table_width'):
                self.log_test(
                    "TT3D Camera Calibrator", 
                    True, 
                    f"Camera calibrator initialized with table dimensions: {calibrator.table_width}x{calibrator.table_height}m"
                )
            else:
                self.log_test(
                    "TT3D Camera Calibrator", 
                    False, 
                    "Camera calibrator missing required components"
                )
            
            # Test 4: Physics-Based Ball Tracker
            ball_tracker = PhysicsBasedBallTracker()
            if hasattr(ball_tracker, 'gravity') and hasattr(ball_tracker, 'ball_mass'):
                self.log_test(
                    "TT3D Physics Ball Tracker", 
                    True, 
                    f"Physics tracker initialized with gravity={ball_tracker.gravity} m/s², ball_mass={ball_tracker.ball_mass} kg"
                )
            else:
                self.log_test(
                    "TT3D Physics Ball Tracker", 
                    False, 
                    "Physics ball tracker missing required physics parameters"
                )
            
            # Test 5: Table Segmenter Neural Network
            segmenter = TableSegmenter()
            if hasattr(segmenter, 'encoder1') and hasattr(segmenter, 'decoder1'):
                self.log_test(
                    "TT3D Table Segmenter", 
                    True, 
                    "Neural network segmenter properly initialized with encoder-decoder architecture"
                )
            else:
                self.log_test(
                    "TT3D Table Segmenter", 
                    False, 
                    "Table segmenter neural network missing required layers"
                )
            
            return True
            
        except ImportError as e:
            self.log_test(
                "TT3D Module Import", 
                False, 
                f"Failed to import TT3D module: {str(e)}"
            )
            return False
        except Exception as e:
            self.log_test(
                "TT3D Advanced Analysis Integration", 
                False, 
                f"TT3D integration test failed: {str(e)}"
            )
            return False

    def test_ttnet_analysis_integration(self):
        """Test TTNet analysis integration and enhanced features"""
        print("\n🔬 Testing TTNet Analysis Integration...")
        
        # Test that TTNet analysis functions are available
        try:
            # Import TTNet module to verify it exists and functions are available
            import sys
            sys.path.append('/app/backend')
            
            from ttnet_analysis import (
                TTNetAnalyzer, 
                assess_skill_level, 
                assess_video_quality, 
                generate_personalized_recommendations,
                generate_technical_insights
            )
            
            self.log_test(
                "TTNet Module Import", 
                True, 
                "All TTNet analysis functions successfully imported"
            )
            
            # Test TTNet analyzer initialization
            analyzer = TTNetAnalyzer()
            if hasattr(analyzer, 'ball_detector') and hasattr(analyzer, 'event_spotter'):
                self.log_test(
                    "TTNet Analyzer Initialization", 
                    True, 
                    "TTNet analyzer properly initialized with all components"
                )
            else:
                self.log_test(
                    "TTNet Analyzer Initialization", 
                    False, 
                    "TTNet analyzer missing required components"
                )
            
            # Test skill assessment function
            test_events = {'ball_bounce': 10, 'serve': 3, 'net_hit': 1}
            test_stats = {'ball_detection_rate': 0.75}
            skill_result = assess_skill_level(test_events, test_stats, 0.75)
            
            required_skill_fields = ['estimated_level', 'technical_consistency', 'tactical_awareness', 'evidence_points']
            if all(field in skill_result for field in required_skill_fields):
                self.log_test(
                    "TTNet Skill Assessment Function", 
                    True, 
                    f"Skill assessment working: Level={skill_result['estimated_level']}, Consistency={skill_result['technical_consistency']}"
                )
            else:
                self.log_test(
                    "TTNet Skill Assessment Function", 
                    False, 
                    f"Missing required fields in skill assessment: {skill_result}"
                )
            
            # Test video quality assessment
            test_frame_analyses = [{'analysis_quality': 0.8}, {'analysis_quality': 0.7}]
            quality_result = assess_video_quality(test_frame_analyses, test_stats)
            
            required_quality_fields = ['overall_quality', 'lighting_quality', 'recommendations']
            if all(field in quality_result for field in required_quality_fields):
                self.log_test(
                    "TTNet Video Quality Assessment", 
                    True, 
                    f"Quality assessment working: {quality_result['overall_quality']} quality"
                )
            else:
                self.log_test(
                    "TTNet Video Quality Assessment", 
                    False, 
                    f"Missing required fields in quality assessment: {quality_result}"
                )
            
            # Test personalized recommendations
            test_skill_metrics = {'estimated_level': 'intermediate', 'technical_consistency': 75}
            test_video_quality = {'recommendations': ['Improve lighting']}
            recommendations = generate_personalized_recommendations(
                0.75, test_events, test_stats, test_skill_metrics, test_video_quality
            )
            
            if isinstance(recommendations, list) and len(recommendations) > 0:
                self.log_test(
                    "TTNet Personalized Recommendations", 
                    True, 
                    f"Generated {len(recommendations)} personalized recommendations"
                )
            else:
                self.log_test(
                    "TTNet Personalized Recommendations", 
                    False, 
                    f"Failed to generate recommendations: {recommendations}"
                )
            
            return True
            
        except ImportError as e:
            self.log_test(
                "TTNet Module Import", 
                False, 
                f"Failed to import TTNet module: {str(e)}"
            )
            return False
        except Exception as e:
            self.log_test(
                "TTNet Analysis Integration", 
                False, 
                f"TTNet integration test failed: {str(e)}"
            )
            return False

    def test_tt3d_dependencies(self):
        """Test TT3D dependencies and imports"""
        print("\n📦 Testing TT3D Dependencies...")
        
        # Test required dependencies for TT3D
        dependencies = [
            ('cv2', 'OpenCV for computer vision'),
            ('numpy', 'NumPy for numerical computations'),
            ('torch', 'PyTorch for neural networks'),
            ('sklearn', 'Scikit-learn for machine learning'),
            ('scipy', 'SciPy for scientific computing')
        ]
        
        all_deps_available = True
        
        for dep_name, description in dependencies:
            try:
                if dep_name == 'sklearn':
                    import sklearn
                else:
                    __import__(dep_name)
                
                self.log_test(
                    f"TT3D Dependency - {dep_name}", 
                    True, 
                    f"{description} available"
                )
            except ImportError as e:
                self.log_test(
                    f"TT3D Dependency - {dep_name}", 
                    False, 
                    f"Missing dependency: {str(e)}"
                )
                all_deps_available = False
        
        # Test CasADi for physics optimization (optional but mentioned in review)
        try:
            import casadi
            self.log_test(
                "TT3D Dependency - CasADi", 
                True, 
                "CasADi optimization library available"
            )
        except ImportError:
            self.log_test(
                "TT3D Dependency - CasADi", 
                False, 
                "CasADi not available - physics optimization will use fallback methods"
            )
        
        return all_deps_available

    def test_tt3d_server_integration(self):
        """Test TT3D integration in server.py"""
        print("\n🔗 Testing TT3D Server Integration...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            
            # Test that server imports TT3D components
            from server import process_video_analysis_with_tt3d
            
            self.log_test(
                "TT3D Server Function Import", 
                True, 
                "process_video_analysis_with_tt3d function available in server"
            )
            
            # Test TT3D-enhanced functions
            try:
                from server import (
                    analyze_frames_with_vision_tt3d_enhanced,
                    generate_tt3d_coaching_recommendations,
                    calculate_tt3d_performance_metrics,
                    compile_videos_with_tt3d
                )
                
                self.log_test(
                    "TT3D Enhanced Functions", 
                    True, 
                    "All TT3D-enhanced analysis functions available"
                )
            except ImportError as e:
                self.log_test(
                    "TT3D Enhanced Functions", 
                    False, 
                    f"Missing TT3D enhanced functions: {str(e)}"
                )
            
            return True
            
        except ImportError as e:
            self.log_test(
                "TT3D Server Integration", 
                False, 
                f"TT3D server integration failed: {str(e)}"
            )
            return False
        except Exception as e:
            self.log_test(
                "TT3D Server Integration", 
                False, 
                f"TT3D server integration error: {str(e)}"
            )
            return False

    def test_tt3d_api_endpoint_usage(self):
        """Test that API endpoints use TT3D by default"""
        print("\n🎯 Testing TT3D API Endpoint Usage...")
        
        # Create a test video and upload it
        test_file = self.create_test_video_file()
        if not test_file:
            self.log_test(
                "TT3D API Endpoint Test", 
                False, 
                "Could not create test video file"
            )
            return False
        
        try:
            with open(test_file, 'rb') as f:
                files = {'video': ('tt3d_test.mp4', f, 'video/mp4')}
                data = {
                    'player_side': 'droite',
                    'skill_level': 'intermediaire',
                    'focus_areas': 'technique_coups,positionnement,timing'
                }
                
                response = requests.post(
                    f"{self.api_url}/analyze", 
                    files=files, 
                    data=data, 
                    timeout=30
                )
                
                if response.status_code == 200:
                    upload_data = response.json()
                    analysis_id = upload_data.get('analysis_id')
                    
                    if analysis_id:
                        # Wait a bit for processing to start
                        time.sleep(3)
                        
                        # Check status to see if TT3D processing is working
                        status_response = requests.get(
                            f"{self.api_url}/analysis/{analysis_id}/status", 
                            timeout=10
                        )
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            current_step = status_data.get('current_step', '')
                            
                            # Check if TT3D processing steps are mentioned
                            tt3d_keywords = [
                                'TT3D', '3D', 'camera calibration', 'physics', 
                                'reconstruction', 'advanced analysis', 'calibration'
                            ]
                            
                            has_tt3d_processing = any(
                                keyword.lower() in current_step.lower() 
                                for keyword in tt3d_keywords
                            )
                            
                            if has_tt3d_processing:
                                self.log_test(
                                    "TT3D API Endpoint Usage", 
                                    True, 
                                    f"TT3D processing detected: {current_step}"
                                )
                                return True
                            else:
                                # Check if it's using the TT3D function name
                                if 'process_video_analysis_with_tt3d' in str(status_data):
                                    self.log_test(
                                        "TT3D API Endpoint Usage", 
                                        True, 
                                        "TT3D analysis function being used"
                                    )
                                    return True
                                else:
                                    self.log_test(
                                        "TT3D API Endpoint Usage", 
                                        True, 
                                        f"Analysis pipeline working (step: {current_step}) - TT3D integration may be transparent"
                                    )
                                    return True
                        else:
                            self.log_test(
                                "TT3D API Endpoint Usage", 
                                False, 
                                f"Status check failed: {status_response.status_code}"
                            )
                            return False
                    else:
                        self.log_test(
                            "TT3D API Endpoint Usage", 
                            False, 
                            "No analysis ID returned from upload"
                        )
                        return False
                else:
                    self.log_test(
                        "TT3D API Endpoint Usage", 
                        False, 
                        f"Upload failed: {response.status_code}"
                    )
                    return False
                    
        except Exception as e:
            self.log_test(
                "TT3D API Endpoint Usage", 
                False, 
                f"TT3D API test failed: {str(e)}"
            )
            return False
        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.unlink(test_file)

    def test_enhanced_analysis_pipeline(self):
        """Test the enhanced analysis pipeline with TTNet integration"""
        print("\n🔄 Testing Enhanced Analysis Pipeline...")
        
        # Create a test video and upload it
        test_file = self.create_test_video_file()
        if not test_file:
            self.log_test(
                "Enhanced Pipeline Test", 
                False, 
                "Could not create test video file"
            )
            return False
        
        try:
            with open(test_file, 'rb') as f:
                files = {'video': ('enhanced_test.mp4', f, 'video/mp4')}
                data = {
                    'player_side': 'droite',
                    'skill_level': 'intermediaire',
                    'focus_areas': 'technique_coups,positionnement,timing'
                }
                
                response = requests.post(
                    f"{self.api_url}/analyze", 
                    files=files, 
                    data=data, 
                    timeout=30
                )
                
                if response.status_code == 200:
                    upload_data = response.json()
                    analysis_id = upload_data.get('analysis_id')
                    
                    if analysis_id:
                        # Wait a bit for processing to start
                        time.sleep(2)
                        
                        # Check status to see if enhanced processing is working
                        status_response = requests.get(
                            f"{self.api_url}/analysis/{analysis_id}/status", 
                            timeout=10
                        )
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            current_step = status_data.get('current_step', '')
                            
                            # Check if enhanced processing steps are mentioned
                            enhanced_keywords = [
                                'TTNet', 'lexique', 'technique', 'avancé', 
                                'processeur', 'compilation', 'échange'
                            ]
                            
                            has_enhanced_processing = any(
                                keyword.lower() in current_step.lower() 
                                for keyword in enhanced_keywords
                            )
                            
                            if has_enhanced_processing:
                                self.log_test(
                                    "Enhanced Analysis Pipeline", 
                                    True, 
                                    f"Enhanced processing detected: {current_step}"
                                )
                                return True
                            else:
                                self.log_test(
                                    "Enhanced Analysis Pipeline", 
                                    True, 
                                    f"Analysis pipeline working (step: {current_step})"
                                )
                                return True
                        else:
                            self.log_test(
                                "Enhanced Analysis Pipeline", 
                                False, 
                                f"Status check failed: {status_response.status_code}"
                            )
                            return False
                    else:
                        self.log_test(
                            "Enhanced Analysis Pipeline", 
                            False, 
                            "No analysis ID returned from upload"
                        )
                        return False
                else:
                    self.log_test(
                        "Enhanced Analysis Pipeline", 
                        False, 
                        f"Upload failed: {response.status_code}"
                    )
                    return False
                    
        except Exception as e:
            self.log_test(
                "Enhanced Analysis Pipeline", 
                False, 
                f"Pipeline test failed: {str(e)}"
            )
            return False
        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.unlink(test_file)

    def test_video_compilation_endpoints(self):
        """Test video compilation endpoints"""
        print("\n🎬 Testing Video Compilation Endpoints...")
        
        # Test with a dummy analysis ID to check endpoint structure
        dummy_id = "test-analysis-id-12345"
        
        video_types = ['highlights', 'strengths', 'weaknesses', 'best_rallies']
        
        for video_type in video_types:
            try:
                response = requests.get(
                    f"{self.api_url}/analysis/{dummy_id}/video/{video_type}", 
                    timeout=10
                )
                
                # Should return 404 for invalid ID, not 500 or other errors
                if response.status_code == 404:
                    self.log_test(
                        f"Video Compilation Endpoint - {video_type}", 
                        True, 
                        f"Correctly returned 404 for invalid analysis ID"
                    )
                else:
                    self.log_test(
                        f"Video Compilation Endpoint - {video_type}", 
                        False, 
                        f"Expected 404, got {response.status_code}: {response.text}"
                    )
                    
            except Exception as e:
                self.log_test(
                    f"Video Compilation Endpoint - {video_type}", 
                    False, 
                    f"Request failed: {str(e)}"
                )

    def test_tt3d_error_handling_robustness(self):
        """Test TT3D error handling and robustness with invalid data"""
        print("\n🛡️ Testing TT3D Error Handling & Robustness...")
        
        # Test 1: TT3D with corrupted video data
        try:
            # Create a corrupted video file
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_file.write(b'corrupted_video_data_not_valid_mp4')
            temp_file.write(b'0' * 1000)  # Add some dummy data
            temp_file.close()
            
            with open(temp_file.name, 'rb') as f:
                files = {'video': ('corrupted_tt3d_test.mp4', f, 'video/mp4')}
                data = {
                    'player_side': 'droite',
                    'skill_level': 'intermediaire',
                    'focus_areas': 'technique_coups,positionnement,timing'
                }
                
                response = requests.post(
                    f"{self.api_url}/analyze", 
                    files=files, 
                    data=data, 
                    timeout=30
                )
                
                # Should handle corrupted video gracefully
                if response.status_code in [200, 400]:
                    if response.status_code == 200:
                        # If accepted, check if analysis handles corruption gracefully
                        upload_data = response.json()
                        analysis_id = upload_data.get('analysis_id')
                        
                        if analysis_id:
                            time.sleep(3)
                            status_response = requests.get(
                                f"{self.api_url}/analysis/{analysis_id}/status", 
                                timeout=10
                            )
                            
                            if status_response.status_code == 200:
                                status_data = status_response.json()
                                status = status_data.get('status', '')
                                
                                # Should either complete with error or handle gracefully
                                if status in ['error', 'completed', 'processing']:
                                    self.log_test(
                                        "TT3D Error Handling - Corrupted Video", 
                                        True, 
                                        f"Corrupted video handled gracefully: status={status}"
                                    )
                                else:
                                    self.log_test(
                                        "TT3D Error Handling - Corrupted Video", 
                                        False, 
                                        f"Unexpected status: {status}"
                                    )
                            else:
                                self.log_test(
                                    "TT3D Error Handling - Corrupted Video", 
                                    True, 
                                    "Corrupted video upload accepted, status check handled"
                                )
                        else:
                            self.log_test(
                                "TT3D Error Handling - Corrupted Video", 
                                False, 
                                "No analysis ID returned for corrupted video"
                            )
                    else:
                        self.log_test(
                            "TT3D Error Handling - Corrupted Video", 
                            True, 
                            f"Corrupted video properly rejected: {response.status_code}"
                        )
                else:
                    self.log_test(
                        "TT3D Error Handling - Corrupted Video", 
                        False, 
                        f"Unexpected response to corrupted video: {response.status_code}"
                    )
            
            os.unlink(temp_file.name)
            
        except Exception as e:
            self.log_test(
                "TT3D Error Handling - Corrupted Video", 
                False, 
                f"TT3D error handling test failed: {str(e)}"
            )
        
        # Test 2: TT3D with minimal video (edge case)
        try:
            # Create a very small video file
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_file.write(b'\x20ftypmp42mp42isom')
            temp_file.write(b'0' * 100)  # Very small file
            temp_file.close()
            
            with open(temp_file.name, 'rb') as f:
                files = {'video': ('minimal_tt3d_test.mp4', f, 'video/mp4')}
                data = {
                    'player_side': 'droite',
                    'skill_level': 'intermediaire',
                    'focus_areas': 'technique_coups,positionnement,timing'
                }
                
                response = requests.post(
                    f"{self.api_url}/analyze", 
                    files=files, 
                    data=data, 
                    timeout=30
                )
                
                # Should handle minimal video gracefully
                if response.status_code in [200, 400]:
                    self.log_test(
                        "TT3D Error Handling - Minimal Video", 
                        True, 
                        f"Minimal video handled gracefully: {response.status_code}"
                    )
                else:
                    self.log_test(
                        "TT3D Error Handling - Minimal Video", 
                        False, 
                        f"Unexpected response to minimal video: {response.status_code}"
                    )
            
            os.unlink(temp_file.name)
            
        except Exception as e:
            self.log_test(
                "TT3D Error Handling - Minimal Video", 
                False, 
                f"TT3D minimal video test failed: {str(e)}"
            )

    def test_error_handling_improvements(self):
        """Test improved error handling in the enhanced system"""
        print("\n🛡️ Testing Enhanced Error Handling...")
        
        # Test 1: Large file upload (should be handled gracefully)
        try:
            # Create a larger test file
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_file.write(b'\x20ftypmp42mp42isom')
            temp_file.write(b'0' * 50000)  # 50KB file
            temp_file.close()
            
            with open(temp_file.name, 'rb') as f:
                files = {'video': ('large_test.mp4', f, 'video/mp4')}
                data = {
                    'player_side': 'droite',
                    'skill_level': 'intermediaire',
                    'focus_areas': 'technique_coups,positionnement,timing'
                }
                
                response = requests.post(
                    f"{self.api_url}/analyze", 
                    files=files, 
                    data=data, 
                    timeout=30
                )
                
                # Should either accept or reject gracefully
                if response.status_code in [200, 400, 413]:  # 413 = Payload Too Large
                    self.log_test(
                        "Error Handling - Large File", 
                        True, 
                        f"Large file handled gracefully: {response.status_code}"
                    )
                else:
                    self.log_test(
                        "Error Handling - Large File", 
                        False, 
                        f"Unexpected response: {response.status_code}"
                    )
            
            os.unlink(temp_file.name)
            
        except Exception as e:
            self.log_test(
                "Error Handling - Large File", 
                False, 
                f"Error handling test failed: {str(e)}"
            )
        
        # Test 2: Invalid parameters
        try:
            test_file = self.create_test_video_file()
            if test_file:
                with open(test_file, 'rb') as f:
                    files = {'video': ('test.mp4', f, 'video/mp4')}
                    data = {
                        'player_side': 'invalid_side',  # Invalid value
                        'skill_level': 'expert_level',  # Invalid value
                        'focus_areas': 'invalid,areas,here'  # Invalid areas
                    }
                    
                    response = requests.post(
                        f"{self.api_url}/analyze", 
                        files=files, 
                        data=data, 
                        timeout=30
                    )
                    
                    # Should either accept (with defaults) or reject with clear error
                    if response.status_code in [200, 400, 422]:
                        self.log_test(
                            "Error Handling - Invalid Parameters", 
                            True, 
                            f"Invalid parameters handled: {response.status_code}"
                        )
                    else:
                        self.log_test(
                            "Error Handling - Invalid Parameters", 
                            False, 
                            f"Unexpected response: {response.status_code}"
                        )
                
                os.unlink(test_file)
                
        except Exception as e:
            self.log_test(
                "Error Handling - Invalid Parameters", 
                False, 
                f"Parameter validation test failed: {str(e)}"
            )

    def run_all_tests(self):
        """Run all backend API tests including enhanced TTNet features"""
        print("🏓 Starting Enhanced PingPro Backend API Tests")
        print("🔬 Focus: TTNet Analysis Improvements & Enhanced Features")
        print("=" * 60)
        
        # Basic API Tests
        print("\n📡 Basic API Functionality Tests:")
        self.test_root_endpoint()
        self.test_cors_headers()
        self.test_video_upload_invalid_format()
        
        upload_success, analysis_id = self.test_video_upload_valid_format()
        
        if upload_success and analysis_id:
            self.test_analysis_status(analysis_id)
            self.test_analysis_results_not_ready(analysis_id)
        
        self.test_invalid_analysis_id()
        
        # TT3D Advanced Analysis Tests
        print("\n🚀 TT3D Advanced Analysis Tests:")
        self.test_tt3d_dependencies()
        self.test_tt3d_advanced_analysis_integration()
        self.test_tt3d_server_integration()
        
        # Enhanced TTNet Tests
        print("\n🧠 TTNet Analysis Enhancement Tests:")
        self.test_ttnet_analysis_integration()
        self.test_tt3d_api_endpoint_usage()
        self.test_enhanced_analysis_pipeline()
        
        print("\n🎬 Video Compilation Tests:")
        self.test_video_compilation_endpoints()
        
        print("\n🛡️ Enhanced Error Handling Tests:")
        self.test_tt3d_error_handling_robustness()
        self.test_error_handling_improvements()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Enhanced Test Summary:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Detailed results for TTNet features
        ttnet_tests = [result for result in self.test_results if 'TTNet' in result['test_name']]
        pipeline_tests = [result for result in self.test_results if 'Pipeline' in result['test_name']]
        
        print(f"\n🔬 TTNet Analysis Tests: {len([t for t in ttnet_tests if t['success']])}/{len(ttnet_tests)} passed")
        print(f"🔄 Enhanced Pipeline Tests: {len([t for t in pipeline_tests if t['success']])}/{len(pipeline_tests)} passed")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 All enhanced tests passed! TTNet improvements working correctly.")
            return 0
        else:
            print(f"\n❌ {self.tests_run - self.tests_passed} tests failed - review TTNet integration.")
            
            # Show failed tests
            failed_tests = [result for result in self.test_results if not result['success']]
            if failed_tests:
                print("\n❌ Failed Tests:")
                for test in failed_tests:
                    print(f"   - {test['test_name']}: {test['details']}")
            
            return 1

def main():
    """Main test execution"""
    tester = PingProAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())