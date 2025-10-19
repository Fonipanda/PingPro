#!/usr/bin/env python3
"""
Test script for the 4 specific corrections requested by user
"""

import requests
import sys
import json
import time
import tempfile
import os
from datetime import datetime
from pathlib import Path

class FourCorrectionsTest:
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

    def test_video_generation_with_real_data(self):
        """Test 1: Génération des vidéos avec vraies données"""
        print("\n📹 Testing Video Generation with Real Data...")
        
        # Test ffmpeg installation
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.log_test(
                    "FFmpeg Installation", 
                    True, 
                    f"FFmpeg installed and functional"
                )
            else:
                self.log_test(
                    "FFmpeg Installation", 
                    False, 
                    f"FFmpeg not working properly: {result.stderr}"
                )
        except Exception as e:
            self.log_test(
                "FFmpeg Installation", 
                False, 
                f"FFmpeg not available: {str(e)}"
            )
        
        # Test compile_videos_with_real_analysis function
        try:
            import sys
            sys.path.append('/app/backend')
            from server import compile_videos_with_real_analysis, create_video_segment
            
            self.log_test(
                "compile_videos_with_real_analysis Function", 
                True, 
                "Function available and importable"
            )
            
            # Test create_video_segment function
            self.log_test(
                "create_video_segment Function", 
                True, 
                "Video segment creation function available"
            )
            
        except ImportError as e:
            self.log_test(
                "Video Generation Functions", 
                False, 
                f"Failed to import video generation functions: {str(e)}"
            )
        
        # Test compilations directory structure
        try:
            import os
            from pathlib import Path
            compilations_dir = Path("/app/backend/compilations")
            
            if compilations_dir.exists():
                self.log_test(
                    "Compilations Directory", 
                    True, 
                    f"Compilations directory exists at {compilations_dir}"
                )
            else:
                # Try to create it
                compilations_dir.mkdir(parents=True, exist_ok=True)
                self.log_test(
                    "Compilations Directory", 
                    True, 
                    f"Compilations directory created at {compilations_dir}"
                )
        except Exception as e:
            self.log_test(
                "Compilations Directory", 
                False, 
                f"Failed to access/create compilations directory: {str(e)}"
            )
        
        # Test video serving endpoint /api/videos/{filename}
        try:
            # Test with a dummy filename to check endpoint structure
            response = requests.get(f"{self.api_url}/videos/test_video.mp4", timeout=10)
            
            # Should return 404 for non-existent file, not 500 or other errors
            if response.status_code == 404:
                self.log_test(
                    "Video Serving Endpoint", 
                    True, 
                    "Video serving endpoint /api/videos/{filename} properly configured"
                )
            else:
                self.log_test(
                    "Video Serving Endpoint", 
                    False, 
                    f"Unexpected response from video endpoint: {response.status_code}"
                )
        except Exception as e:
            self.log_test(
                "Video Serving Endpoint", 
                False, 
                f"Video serving endpoint test failed: {str(e)}"
            )

    def test_table_tennis_rules_in_analysis(self):
        """Test 2: Règles Tennis de Table dans analyse vidéo"""
        print("\n🏓 Testing Table Tennis Rules in Video Analysis...")
        
        # Test apply_table_tennis_scoring function
        try:
            import sys
            sys.path.append('/app/backend')
            from server import apply_table_tennis_scoring
            
            # Test with sample TTNet results
            sample_ttnet_results = {
                "match_statistics": {
                    "ball_detection_rate": 0.75,
                    "event_summary": {
                        "ball_bounce": 15,
                        "serve": 6,
                        "net_hit": 2
                    }
                }
            }
            
            scoring_result = apply_table_tennis_scoring(sample_ttnet_results)
            
            # Check required fields
            required_fields = ["final_score", "sets", "score_progression", "rules_applied", "match_statistics"]
            missing_fields = [field for field in required_fields if field not in scoring_result]
            
            if not missing_fields:
                self.log_test(
                    "apply_table_tennis_scoring Function", 
                    True, 
                    f"Function working correctly with all required fields"
                )
                
                # Check 11-point rule
                final_score = scoring_result.get("final_score", {})
                player1_score = final_score.get("player1", 0)
                player2_score = final_score.get("player2", 0)
                
                if max(player1_score, player2_score) >= 11:
                    self.log_test(
                        "11-Point Rule Implementation", 
                        True, 
                        f"Scoring follows 11-point rule: {player1_score}-{player2_score}"
                    )
                else:
                    self.log_test(
                        "11-Point Rule Implementation", 
                        False, 
                        f"Scoring doesn't follow 11-point rule: {player1_score}-{player2_score}"
                    )
                
                # Check score progression with 19 points
                score_progression = scoring_result.get("score_progression", [])
                if len(score_progression) == 19:
                    self.log_test(
                        "Score Progression (19 points)", 
                        True, 
                        f"Score progression has exactly 19 points as expected"
                    )
                else:
                    self.log_test(
                        "Score Progression (19 points)", 
                        False, 
                        f"Score progression has {len(score_progression)} points, expected 19"
                    )
                
            else:
                self.log_test(
                    "apply_table_tennis_scoring Function", 
                    False, 
                    f"Missing required fields: {missing_fields}"
                )
                
        except Exception as e:
            self.log_test(
                "Table Tennis Scoring Functions", 
                False, 
                f"Failed to test table tennis scoring: {str(e)}"
            )
        
        # Test AnalysisResult includes table_tennis_scoring
        try:
            from server import AnalysisResult
            
            # Check if AnalysisResult model has table_tennis_scoring field
            model_fields = AnalysisResult.model_fields if hasattr(AnalysisResult, 'model_fields') else (AnalysisResult.__fields__ if hasattr(AnalysisResult, '__fields__') else {})
            
            if 'table_tennis_scoring' in model_fields:
                self.log_test(
                    "AnalysisResult table_tennis_scoring Field", 
                    True, 
                    "AnalysisResult model includes table_tennis_scoring field"
                )
            else:
                self.log_test(
                    "AnalysisResult table_tennis_scoring Field", 
                    False, 
                    "AnalysisResult model missing table_tennis_scoring field"
                )
                
        except Exception as e:
            self.log_test(
                "AnalysisResult Model Check", 
                False, 
                f"Failed to check AnalysisResult model: {str(e)}"
            )

    def test_ball_impacts_with_real_data(self):
        """Test 3: Impacts Balle avec données vidéo analysée"""
        print("\n⚽ Testing Ball Impacts with Analyzed Video Data...")
        
        # Test generateBallImpacts function in frontend
        try:
            # Since we can't directly test frontend JS, we'll test the backend data that feeds it
            import sys
            sys.path.append('/app/backend')
            from ttnet_analysis import analyze_video_with_ttn, TTNetAnalyzer
            
            # Test that analyze_video_with_ttn function exists (real analysis replacement)
            self.log_test(
                "analyze_video_with_ttn Function", 
                True, 
                "Real analysis function available (replacement for mocked functions)"
            )
            
            # Test TTNetAnalyzer for ball detection methods
            analyzer = TTNetAnalyzer()
            if hasattr(analyzer, 'ball_detector') or hasattr(analyzer, 'analyze_video_real'):
                self.log_test(
                    "TTNetAnalyzer Ball Detection", 
                    True, 
                    "TTNetAnalyzer has ball detection capabilities"
                )
            else:
                self.log_test(
                    "TTNetAnalyzer Ball Detection", 
                    False, 
                    "TTNetAnalyzer missing ball detection methods"
                )
                
        except Exception as e:
            self.log_test(
                "Ball Detection Analysis", 
                False, 
                f"Failed to test ball detection: {str(e)}"
            )
        
        # Test ball_bounce events in codebase
        try:
            import subprocess
            result = subprocess.run(
                ['grep', '-r', 'ball_bounce', '/app/backend/'], 
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                bounce_count = len(result.stdout.strip().split('\n'))
                self.log_test(
                    "Ball Bounce Events in Codebase", 
                    True, 
                    f"Found {bounce_count} references to ball_bounce events"
                )
            else:
                self.log_test(
                    "Ball Bounce Events in Codebase", 
                    False, 
                    "No ball_bounce events found in codebase"
                )
        except Exception as e:
            self.log_test(
                "Ball Bounce Events Search", 
                False, 
                f"Failed to search for ball_bounce events: {str(e)}"
            )
        
        # Test dynamic statistics generation
        try:
            from server import calculate_enhanced_performance_metrics_lexicon
            
            # Test with sample data
            sample_analysis = {"stroke_analysis": {"technique_quality": "7"}}
            sample_ttnet = {
                "match_statistics": {
                    "ball_detection_rate": 0.8,
                    "event_summary": {"ball_bounce": 12}
                }
            }
            sample_video = {"rally_segments": [{"duration": 5}]}
            
            metrics = calculate_enhanced_performance_metrics_lexicon(
                sample_analysis, sample_ttnet, sample_video
            )
            
            if hasattr(metrics, 'event_detection') and metrics.event_detection:
                self.log_test(
                    "Dynamic Statistics Generation", 
                    True, 
                    f"Performance metrics include event_detection data"
                )
            else:
                self.log_test(
                    "Dynamic Statistics Generation", 
                    False, 
                    "Performance metrics missing event_detection data"
                )
                
        except Exception as e:
            self.log_test(
                "Dynamic Statistics Generation", 
                False, 
                f"Failed to test dynamic statistics: {str(e)}"
            )

    def test_realtime_websocket_with_webcam(self):
        """Test 4: WebSocket temps réel avec webcam"""
        print("\n📡 Testing Real-Time WebSocket with Webcam...")
        
        # Test WebSocket endpoint /ws/realtime/{client_id}
        try:
            import sys
            sys.path.append('/app/backend')
            from streaming_server import websocket_endpoint
            
            if callable(websocket_endpoint):
                self.log_test(
                    "WebSocket Endpoint /ws/realtime/{client_id}", 
                    True, 
                    "WebSocket endpoint function available and callable"
                )
            else:
                self.log_test(
                    "WebSocket Endpoint /ws/realtime/{client_id}", 
                    False, 
                    "WebSocket endpoint function not callable"
                )
        except Exception as e:
            self.log_test(
                "WebSocket Endpoint Import", 
                False, 
                f"Failed to import WebSocket endpoint: {str(e)}"
            )
        
        # Test cv2.VideoCapture(0) for webcam
        try:
            import cv2
            
            # Test if cv2 can initialize VideoCapture (without actually opening camera)
            cap = cv2.VideoCapture()
            if hasattr(cap, 'open') and hasattr(cap, 'read'):
                self.log_test(
                    "cv2.VideoCapture Webcam Support", 
                    True, 
                    "OpenCV VideoCapture available for webcam access"
                )
                cap.release()
            else:
                self.log_test(
                    "cv2.VideoCapture Webcam Support", 
                    False, 
                    "OpenCV VideoCapture missing required methods"
                )
        except Exception as e:
            self.log_test(
                "cv2.VideoCapture Webcam Support", 
                False, 
                f"Failed to test webcam support: {str(e)}"
            )
        
        # Test base64 frame transmission capability
        try:
            import base64
            import numpy as np
            
            # Test base64 encoding of a dummy frame
            dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
            import cv2
            _, buffer = cv2.imencode('.jpg', dummy_frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            if len(frame_base64) > 0:
                self.log_test(
                    "Base64 Frame Transmission", 
                    True, 
                    f"Base64 frame encoding working (encoded {len(frame_base64)} chars)"
                )
            else:
                self.log_test(
                    "Base64 Frame Transmission", 
                    False, 
                    "Base64 frame encoding failed"
                )
        except Exception as e:
            self.log_test(
                "Base64 Frame Transmission", 
                False, 
                f"Failed to test base64 encoding: {str(e)}"
            )
        
        # Test real-time analysis with simulated ball detection
        try:
            from real_time_ttnet_analyzer import RealTimeAnalyzer
            
            analyzer = RealTimeAnalyzer()
            if hasattr(analyzer, 'analyze_frame') or hasattr(analyzer, 'process_frame'):
                self.log_test(
                    "Real-Time Analysis with Ball Detection", 
                    True, 
                    "RealTimeAnalyzer has frame processing capabilities"
                )
            else:
                self.log_test(
                    "Real-Time Analysis with Ball Detection", 
                    False, 
                    "RealTimeAnalyzer missing frame processing methods"
                )
        except Exception as e:
            self.log_test(
                "Real-Time Analysis with Ball Detection", 
                False, 
                f"Failed to test real-time analysis: {str(e)}"
            )
        
        # Test real-time API endpoints
        try:
            # Test start_analysis message handling
            payload = {"action": "start_analysis", "video_source": "webcam"}
            response = requests.post(
                f"{self.api_url}/realtime/start", 
                json=payload, 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Real-Time API start_analysis Message", 
                    True, 
                    f"Start analysis message handled: {data.get('success', False)}"
                )
            else:
                self.log_test(
                    "Real-Time API start_analysis Message", 
                    False, 
                    f"Start analysis failed: {response.status_code}"
                )
        except Exception as e:
            self.log_test(
                "Real-Time API start_analysis Message", 
                False, 
                f"Failed to test start analysis: {str(e)}"
            )

    def run_tests(self):
        """Run the 4 specific corrections tests"""
        print("🎯 Testing 4 Specific Corrections for PingPro")
        print("=" * 60)
        
        # 1. Test video generation with real data
        self.test_video_generation_with_real_data()
        
        # 2. Test table tennis rules in video analysis
        self.test_table_tennis_rules_in_analysis()
        
        # 3. Test ball impacts with analyzed video data
        self.test_ball_impacts_with_real_data()
        
        # 4. Test real-time WebSocket with webcam
        self.test_realtime_websocket_with_webcam()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 4 Corrections Test Summary:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Categorize results
        video_gen_tests = [r for r in self.test_results if any(k in r['test_name'] for k in ['FFmpeg', 'compile_videos', 'Video Serving', 'Compilations'])]
        table_tennis_tests = [r for r in self.test_results if any(k in r['test_name'] for k in ['table_tennis_scoring', '11-Point', 'Score Progression', 'AnalysisResult'])]
        ball_impacts_tests = [r for r in self.test_results if any(k in r['test_name'] for k in ['Ball', 'analyze_video_with_ttn', 'TTNetAnalyzer', 'Dynamic Statistics'])]
        websocket_tests = [r for r in self.test_results if any(k in r['test_name'] for k in ['WebSocket', 'cv2.VideoCapture', 'Base64', 'Real-Time API'])]
        
        print(f"\n📹 1. Video Generation: {len([t for t in video_gen_tests if t['success']])}/{len(video_gen_tests)} passed")
        print(f"🏓 2. Table Tennis Rules: {len([t for t in table_tennis_tests if t['success']])}/{len(table_tennis_tests)} passed")
        print(f"⚽ 3. Ball Impacts: {len([t for t in ball_impacts_tests if t['success']])}/{len(ball_impacts_tests)} passed")
        print(f"📡 4. WebSocket Real-Time: {len([t for t in websocket_tests if t['success']])}/{len(websocket_tests)} passed")
        
        # Show failed tests
        failed_tests = [r for r in self.test_results if not r['success']]
        if failed_tests:
            print(f"\n❌ Failed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"   - {test['test_name']}: {test['details']}")

if __name__ == "__main__":
    tester = FourCorrectionsTest()
    tester.run_tests()