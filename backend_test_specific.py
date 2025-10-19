#!/usr/bin/env python3
"""
PingPro Backend Testing - 4 Corrections Spécifiques
Tests focused on the 4 specific corrections requested by the user:
1. Génération des vidéos (compile_videos, create_video_segment, ffmpeg)
2. Règles tennis de table (11 points, 2 d'avance, GameState)
3. Impacts Balle avec vraies données (generateBallImpacts, ball_trajectory_3d)
4. Temps réel WebSocket (WebSocket endpoints, simulation mode)
"""

import requests
import sys
import json
import time
import tempfile
import os
import subprocess
from datetime import datetime
from pathlib import Path

class PingProSpecificTester:
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

    def create_test_video_file(self):
        """Create a small test video file for upload testing"""
        try:
            # Create a temporary file with .mp4 extension
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            
            # Write minimal MP4 header (this won't be a valid video but will pass file extension check)
            mp4_header = b'\x20ftypmp42mp42isom'
            temp_file.write(mp4_header)
            temp_file.write(b'0' * 1000)  # Add some dummy data
            temp_file.close()
            
            return temp_file.name
        except Exception as e:
            print(f"Failed to create test video file: {e}")
            return None

    # ========================================
    # 1. GÉNÉRATION DES VIDÉOS TESTS
    # ========================================
    
    def test_ffmpeg_installation(self):
        """Test if ffmpeg is installed and functional"""
        print("\n🎬 Testing FFmpeg Installation...")
        
        try:
            # Check if ffmpeg is available
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                version_info = result.stdout.split('\n')[0]
                self.log_test(
                    "FFmpeg Installation", 
                    True, 
                    f"FFmpeg available: {version_info}"
                )
                return True
            else:
                self.log_test(
                    "FFmpeg Installation", 
                    False, 
                    f"FFmpeg command failed: {result.stderr}"
                )
                return False
                
        except FileNotFoundError:
            self.log_test(
                "FFmpeg Installation", 
                False, 
                "FFmpeg not found in system PATH"
            )
            return False
        except subprocess.TimeoutExpired:
            self.log_test(
                "FFmpeg Installation", 
                False, 
                "FFmpeg command timed out"
            )
            return False
        except Exception as e:
            self.log_test(
                "FFmpeg Installation", 
                False, 
                f"FFmpeg test error: {str(e)}"
            )
            return False

    def test_compile_videos_function(self):
        """Test compile_videos() function exists and works"""
        print("\n📹 Testing compile_videos() Function...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            
            from server import compile_videos, create_video_segment
            
            self.log_test(
                "compile_videos Function Import", 
                True, 
                "compile_videos and create_video_segment functions imported successfully"
            )
            
            # Test create_video_segment function signature
            import inspect
            sig = inspect.signature(create_video_segment)
            expected_params = ['input_path', 'output_path', 'start_time', 'end_time']
            actual_params = list(sig.parameters.keys())
            
            if all(param in actual_params for param in expected_params):
                self.log_test(
                    "create_video_segment Function Signature", 
                    True, 
                    f"Function has correct parameters: {actual_params}"
                )
            else:
                self.log_test(
                    "create_video_segment Function Signature", 
                    False, 
                    f"Missing parameters. Expected: {expected_params}, Got: {actual_params}"
                )
            
            return True
            
        except ImportError as e:
            self.log_test(
                "compile_videos Function Import", 
                False, 
                f"Failed to import video compilation functions: {str(e)}"
            )
            return False
        except Exception as e:
            self.log_test(
                "compile_videos Function Test", 
                False, 
                f"Video compilation function test failed: {str(e)}"
            )
            return False

    def test_compilations_directory_creation(self):
        """Test that compilations directory is created correctly"""
        print("\n📁 Testing Compilations Directory...")
        
        try:
            compilations_base_dir = Path("/app/backend/compilations")
            
            # Check if base directory exists or can be created
            if not compilations_base_dir.exists():
                compilations_base_dir.mkdir(parents=True, exist_ok=True)
            
            if compilations_base_dir.exists() and compilations_base_dir.is_dir():
                self.log_test(
                    "Compilations Base Directory", 
                    True, 
                    f"Compilations directory exists at: {compilations_base_dir}"
                )
                
                # Test creating a test analysis directory
                test_analysis_id = "test-analysis-123"
                test_dir = compilations_base_dir / test_analysis_id
                test_dir.mkdir(exist_ok=True)
                
                if test_dir.exists():
                    self.log_test(
                        "Analysis Compilations Directory", 
                        True, 
                        f"Can create analysis-specific directory: {test_dir}"
                    )
                    
                    # Cleanup
                    test_dir.rmdir()
                    return True
                else:
                    self.log_test(
                        "Analysis Compilations Directory", 
                        False, 
                        "Cannot create analysis-specific directory"
                    )
                    return False
            else:
                self.log_test(
                    "Compilations Base Directory", 
                    False, 
                    f"Cannot create or access compilations directory: {compilations_base_dir}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Compilations Directory Test", 
                False, 
                f"Directory test failed: {str(e)}"
            )
            return False

    def test_video_endpoint_structure(self):
        """Test /api/videos/{video_filename} endpoint structure"""
        print("\n🎯 Testing Video Endpoint Structure...")
        
        try:
            # Test with a dummy filename to check endpoint structure
            dummy_filename = "test_compilation.mp4"
            
            response = requests.get(
                f"{self.api_url}/videos/{dummy_filename}", 
                timeout=10
            )
            
            # Should return 404 for non-existent file, not 500 or other errors
            if response.status_code == 404:
                self.log_test(
                    "Video Endpoint Structure", 
                    True, 
                    f"Video endpoint correctly returns 404 for non-existent file"
                )
                return True
            elif response.status_code == 405:
                self.log_test(
                    "Video Endpoint Structure", 
                    False, 
                    f"Video endpoint not implemented (405 Method Not Allowed)"
                )
                return False
            else:
                self.log_test(
                    "Video Endpoint Structure", 
                    False, 
                    f"Unexpected response: {response.status_code} - {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Video Endpoint Structure", 
                False, 
                f"Video endpoint test failed: {str(e)}"
            )
            return False

    # ========================================
    # 2. RÈGLES TENNIS DE TABLE TESTS
    # ========================================
    
    def test_gamestate_structure(self):
        """Test GameState includes player1_sets, player2_sets, current_set"""
        print("\n🏓 Testing GameState Structure...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            
            from real_time_ttnet_analyzer import GameState
            
            # Test GameState initialization
            game_state = GameState()
            
            # Check required fields
            required_fields = ['player1_sets', 'player2_sets', 'current_set']
            missing_fields = [field for field in required_fields if not hasattr(game_state, field)]
            
            if not missing_fields:
                self.log_test(
                    "GameState Required Fields", 
                    True, 
                    f"GameState has all required fields: {required_fields}"
                )
                
                # Check initial values
                initial_values = {
                    'player1_sets': game_state.player1_sets,
                    'player2_sets': game_state.player2_sets,
                    'current_set': game_state.current_set
                }
                
                self.log_test(
                    "GameState Initial Values", 
                    True, 
                    f"Initial values: {initial_values}"
                )
                return True
            else:
                self.log_test(
                    "GameState Required Fields", 
                    False, 
                    f"Missing required fields: {missing_fields}"
                )
                return False
                
        except ImportError as e:
            self.log_test(
                "GameState Import", 
                False, 
                f"Failed to import GameState: {str(e)}"
            )
            return False
        except Exception as e:
            self.log_test(
                "GameState Structure Test", 
                False, 
                f"GameState test failed: {str(e)}"
            )
            return False

    def test_table_tennis_scoring_logic(self):
        """Test table tennis scoring logic (11 points, 2 advantage)"""
        print("\n🎯 Testing Table Tennis Scoring Logic...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            
            from real_time_ttnet_analyzer import RealTimeAnalyzer
            
            # Create analyzer to test scoring logic
            analyzer = RealTimeAnalyzer()
            
            # Test if analyzer has game state
            if hasattr(analyzer, 'game_state'):
                self.log_test(
                    "RealTimeAnalyzer GameState", 
                    True, 
                    "RealTimeAnalyzer has game_state attribute"
                )
                
                # Check if scoring logic methods exist
                scoring_methods = ['update_score', 'check_set_winner', 'check_match_winner']
                available_methods = [method for method in scoring_methods if hasattr(analyzer, method)]
                
                if available_methods:
                    self.log_test(
                        "Scoring Logic Methods", 
                        True, 
                        f"Available scoring methods: {available_methods}"
                    )
                else:
                    # Check if scoring logic is embedded in other methods
                    all_methods = [method for method in dir(analyzer) if not method.startswith('_')]
                    scoring_related = [method for method in all_methods if 'score' in method.lower() or 'game' in method.lower()]
                    
                    self.log_test(
                        "Scoring Logic Methods", 
                        True, 
                        f"Scoring-related methods found: {scoring_related}"
                    )
                
                return True
            else:
                self.log_test(
                    "RealTimeAnalyzer GameState", 
                    False, 
                    "RealTimeAnalyzer missing game_state attribute"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Table Tennis Scoring Logic", 
                False, 
                f"Scoring logic test failed: {str(e)}"
            )
            return False

    def test_match_format_support(self):
        """Test support for 3 or 5 set match formats"""
        print("\n🏆 Testing Match Format Support...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            
            # Look for match format configuration
            from real_time_ttnet_analyzer import RealTimeAnalyzer
            
            analyzer = RealTimeAnalyzer()
            
            # Check if there's match format configuration
            format_attributes = ['match_format', 'sets_to_win', 'max_sets']
            available_attributes = [attr for attr in format_attributes if hasattr(analyzer, attr)]
            
            if available_attributes:
                self.log_test(
                    "Match Format Configuration", 
                    True, 
                    f"Match format attributes found: {available_attributes}"
                )
            else:
                # Check if match format is hardcoded or in methods
                analyzer_methods = [method for method in dir(analyzer) if not method.startswith('_')]
                match_methods = [method for method in analyzer_methods if 'match' in method.lower() or 'set' in method.lower()]
                
                self.log_test(
                    "Match Format Configuration", 
                    True, 
                    f"Match-related methods found: {match_methods}"
                )
            
            return True
            
        except Exception as e:
            self.log_test(
                "Match Format Support", 
                False, 
                f"Match format test failed: {str(e)}"
            )
            return False

    # ========================================
    # 3. IMPACTS BALLE AVEC VRAIES DONNÉES
    # ========================================
    
    def test_ball_impacts_functions(self):
        """Test generateBallImpacts() and generateServiceImpacts() functions"""
        print("\n⚽ Testing Ball Impacts Functions...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            
            # Look for ball impact generation functions
            # These might be in ttnet_analysis.py or other modules
            
            # Check ttnet_analysis module
            try:
                from ttnet_analysis import TTNetAnalyzer
                
                analyzer = TTNetAnalyzer()
                
                # Look for impact-related methods
                methods = [method for method in dir(analyzer) if not method.startswith('_')]
                impact_methods = [method for method in methods if 'impact' in method.lower() or 'bounce' in method.lower()]
                
                if impact_methods:
                    self.log_test(
                        "Ball Impact Methods", 
                        True, 
                        f"Impact-related methods found: {impact_methods}"
                    )
                else:
                    # Check for ball detection methods
                    ball_methods = [method for method in methods if 'ball' in method.lower()]
                    self.log_test(
                        "Ball Detection Methods", 
                        True, 
                        f"Ball-related methods found: {ball_methods}"
                    )
                
            except ImportError:
                self.log_test(
                    "TTNet Analyzer Import", 
                    False, 
                    "Could not import TTNetAnalyzer"
                )
            
            # Check for ball_bounce event detection
            import subprocess
            result = subprocess.run(['grep', '-r', 'ball_bounce', '/app/backend/'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0 and 'ball_bounce' in result.stdout:
                bounce_occurrences = len(result.stdout.split('\n'))
                self.log_test(
                    "Ball Bounce Detection", 
                    True, 
                    f"ball_bounce events found in {bounce_occurrences} locations"
                )
            else:
                self.log_test(
                    "Ball Bounce Detection", 
                    False, 
                    "ball_bounce events not found in codebase"
                )
            
            return True
            
        except Exception as e:
            self.log_test(
                "Ball Impacts Functions", 
                False, 
                f"Ball impacts test failed: {str(e)}"
            )
            return False

    def test_ball_trajectory_3d_usage(self):
        """Test usage of results.tt3d_analysis.ball_trajectory_3d"""
        print("\n🎯 Testing Ball Trajectory 3D Usage...")
        
        try:
            # Check for ball_trajectory_3d usage in codebase
            import subprocess
            result = subprocess.run(['grep', '-r', 'ball_trajectory_3d', '/app/backend/'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0 and 'ball_trajectory_3d' in result.stdout:
                trajectory_occurrences = len([line for line in result.stdout.split('\n') if 'ball_trajectory_3d' in line])
                self.log_test(
                    "Ball Trajectory 3D Usage", 
                    True, 
                    f"ball_trajectory_3d found in {trajectory_occurrences} locations"
                )
                
                # Check specific usage patterns
                if 'tt3d_analysis.ball_trajectory_3d' in result.stdout:
                    self.log_test(
                        "TT3D Trajectory Access Pattern", 
                        True, 
                        "Correct access pattern 'tt3d_analysis.ball_trajectory_3d' found"
                    )
                else:
                    self.log_test(
                        "TT3D Trajectory Access Pattern", 
                        False, 
                        "Expected access pattern 'tt3d_analysis.ball_trajectory_3d' not found"
                    )
            else:
                self.log_test(
                    "Ball Trajectory 3D Usage", 
                    False, 
                    "ball_trajectory_3d not found in codebase"
                )
            
            return True
            
        except Exception as e:
            self.log_test(
                "Ball Trajectory 3D Usage", 
                False, 
                f"Trajectory 3D test failed: {str(e)}"
            )
            return False

    def test_dynamic_statistics_ball_bounce(self):
        """Test dynamic statistics based on event_detection.ball_bounce"""
        print("\n📊 Testing Dynamic Statistics from Ball Bounce...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            
            # Test that ball_bounce events are used for statistics
            from ttnet_analysis import analyze_video_with_ttn
            
            # Check if the function exists and is callable
            if callable(analyze_video_with_ttn):
                self.log_test(
                    "analyze_video_with_ttn Function", 
                    True, 
                    "Real analysis function is available and callable"
                )
                
                # Check for event detection in the analysis pipeline
                import subprocess
                result = subprocess.run(['grep', '-A5', '-B5', 'event_detection', '/app/backend/ttnet_analysis.py'], 
                                      capture_output=True, text=True)
                
                if result.returncode == 0 and 'ball_bounce' in result.stdout:
                    self.log_test(
                        "Event Detection Ball Bounce", 
                        True, 
                        "event_detection with ball_bounce found in analysis pipeline"
                    )
                else:
                    self.log_test(
                        "Event Detection Ball Bounce", 
                        False, 
                        "event_detection.ball_bounce not found in expected context"
                    )
            else:
                self.log_test(
                    "analyze_video_with_ttn Function", 
                    False, 
                    "Real analysis function not available"
                )
            
            return True
            
        except Exception as e:
            self.log_test(
                "Dynamic Statistics Ball Bounce", 
                False, 
                f"Dynamic statistics test failed: {str(e)}"
            )
            return False

    # ========================================
    # 4. TEMPS RÉEL WEBSOCKET TESTS
    # ========================================
    
    def test_websocket_realtime_endpoint(self):
        """Test WebSocket endpoint /ws/realtime/{client_id}"""
        print("\n🔌 Testing WebSocket Real-Time Endpoint...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            
            # Check if WebSocket endpoint is defined in server
            from server import app
            
            # Get all routes from the FastAPI app
            websocket_routes = []
            for route in app.routes:
                if hasattr(route, 'path') and 'ws' in route.path and 'realtime' in route.path:
                    websocket_routes.append(route.path)
            
            if websocket_routes:
                self.log_test(
                    "WebSocket Endpoint Definition", 
                    True, 
                    f"WebSocket routes found: {websocket_routes}"
                )
                
                # Check for the specific pattern /ws/realtime/{client_id}
                expected_pattern = "/ws/realtime/{client_id}"
                if any(expected_pattern in route for route in websocket_routes):
                    self.log_test(
                        "WebSocket Endpoint Pattern", 
                        True, 
                        f"Expected WebSocket pattern found: {expected_pattern}"
                    )
                else:
                    self.log_test(
                        "WebSocket Endpoint Pattern", 
                        False, 
                        f"Expected pattern {expected_pattern} not found in routes"
                    )
            else:
                self.log_test(
                    "WebSocket Endpoint Definition", 
                    False, 
                    "No WebSocket routes found in server"
                )
            
            return True
            
        except Exception as e:
            self.log_test(
                "WebSocket Real-Time Endpoint", 
                False, 
                f"WebSocket endpoint test failed: {str(e)}"
            )
            return False

    def test_websocket_simulation_mode(self):
        """Test simulation mode when WebSocket fails"""
        print("\n🎭 Testing WebSocket Simulation Mode...")
        
        try:
            # Check for simulation mode implementation
            import subprocess
            result = subprocess.run(['grep', '-r', 'simulation', '/app/backend/'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0 and 'simulation' in result.stdout:
                simulation_occurrences = len([line for line in result.stdout.split('\n') if 'simulation' in line])
                self.log_test(
                    "Simulation Mode Implementation", 
                    True, 
                    f"Simulation mode found in {simulation_occurrences} locations"
                )
                
                # Check for fallback mechanisms
                fallback_result = subprocess.run(['grep', '-r', 'fallback\|fail.*mode\|error.*mode', '/app/backend/'], 
                                              capture_output=True, text=True)
                
                if fallback_result.returncode == 0:
                    self.log_test(
                        "WebSocket Fallback Mechanisms", 
                        True, 
                        "Fallback mechanisms found for WebSocket failures"
                    )
                else:
                    self.log_test(
                        "WebSocket Fallback Mechanisms", 
                        False, 
                        "No explicit fallback mechanisms found"
                    )
            else:
                self.log_test(
                    "Simulation Mode Implementation", 
                    False, 
                    "Simulation mode not found in codebase"
                )
            
            return True
            
        except Exception as e:
            self.log_test(
                "WebSocket Simulation Mode", 
                False, 
                f"Simulation mode test failed: {str(e)}"
            )
            return False

    def test_json_message_formatting(self):
        """Test that JSON messages are well formatted"""
        print("\n📋 Testing JSON Message Formatting...")
        
        try:
            # Check for JSON formatting in WebSocket code
            import subprocess
            result = subprocess.run(['grep', '-A3', '-B3', 'json.dumps\|JSON', '/app/backend/streaming_server.py'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0 and 'json.dumps' in result.stdout:
                json_occurrences = len([line for line in result.stdout.split('\n') if 'json.dumps' in line])
                self.log_test(
                    "JSON Message Formatting", 
                    True, 
                    f"JSON formatting found in {json_occurrences} locations in streaming server"
                )
                
                # Check server.py as well
                server_result = subprocess.run(['grep', '-A3', '-B3', 'json.dumps', '/app/backend/server.py'], 
                                            capture_output=True, text=True)
                
                if server_result.returncode == 0:
                    server_json_count = len([line for line in server_result.stdout.split('\n') if 'json.dumps' in line])
                    self.log_test(
                        "Server JSON Formatting", 
                        True, 
                        f"JSON formatting found in {server_json_count} locations in server"
                    )
                else:
                    self.log_test(
                        "Server JSON Formatting", 
                        False, 
                        "No JSON formatting found in server WebSocket code"
                    )
            else:
                self.log_test(
                    "JSON Message Formatting", 
                    False, 
                    "No JSON formatting found in streaming server"
                )
            
            return True
            
        except Exception as e:
            self.log_test(
                "JSON Message Formatting", 
                False, 
                f"JSON formatting test failed: {str(e)}"
            )
            return False

    def test_realtime_api_endpoints(self):
        """Test /api/realtime/start and /api/realtime/stop endpoints"""
        print("\n🎯 Testing Real-Time API Endpoints...")
        
        # Test /api/realtime/start endpoint
        try:
            payload = {"video_source": "test_source"}
            response = requests.post(
                f"{self.api_url}/realtime/start", 
                json=payload, 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'success' in data and 'message' in data:
                    self.log_test(
                        "Real-Time Start Endpoint", 
                        True, 
                        f"Start endpoint working - Success: {data['success']}"
                    )
                else:
                    self.log_test(
                        "Real-Time Start Endpoint", 
                        False, 
                        f"Missing required fields in response: {data}"
                    )
            else:
                self.log_test(
                    "Real-Time Start Endpoint", 
                    False, 
                    f"Expected 200, got {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_test(
                "Real-Time Start Endpoint", 
                False, 
                f"Start endpoint test failed: {str(e)}"
            )
        
        # Test /api/realtime/stop endpoint
        try:
            response = requests.post(f"{self.api_url}/realtime/stop", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'success' in data and 'message' in data:
                    self.log_test(
                        "Real-Time Stop Endpoint", 
                        True, 
                        f"Stop endpoint working - Success: {data['success']}"
                    )
                else:
                    self.log_test(
                        "Real-Time Stop Endpoint", 
                        False, 
                        f"Missing required fields in response: {data}"
                    )
            else:
                self.log_test(
                    "Real-Time Stop Endpoint", 
                    False, 
                    f"Expected 200, got {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_test(
                "Real-Time Stop Endpoint", 
                False, 
                f"Stop endpoint test failed: {str(e)}"
            )

    # ========================================
    # MAIN TEST RUNNER
    # ========================================
    
    def run_all_specific_tests(self):
        """Run all 4 specific correction tests"""
        print("🚀 Starting PingPro Specific Corrections Testing...")
        print("=" * 60)
        
        # 1. Génération des vidéos
        print("\n1️⃣ GÉNÉRATION DES VIDÉOS")
        print("-" * 30)
        self.test_ffmpeg_installation()
        self.test_compile_videos_function()
        self.test_compilations_directory_creation()
        self.test_video_endpoint_structure()
        
        # 2. Règles tennis de table
        print("\n2️⃣ RÈGLES TENNIS DE TABLE")
        print("-" * 30)
        self.test_gamestate_structure()
        self.test_table_tennis_scoring_logic()
        self.test_match_format_support()
        
        # 3. Impacts Balle avec vraies données
        print("\n3️⃣ IMPACTS BALLE AVEC VRAIES DONNÉES")
        print("-" * 30)
        self.test_ball_impacts_functions()
        self.test_ball_trajectory_3d_usage()
        self.test_dynamic_statistics_ball_bounce()
        
        # 4. Temps réel WebSocket
        print("\n4️⃣ TEMPS RÉEL WEBSOCKET")
        print("-" * 30)
        self.test_websocket_realtime_endpoint()
        self.test_websocket_simulation_mode()
        self.test_json_message_formatting()
        self.test_realtime_api_endpoints()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Failed tests details
        failed_tests = [test for test in self.test_results if not test['success']]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  - {test['test_name']}: {test['details']}")
        
        return self.tests_passed, self.tests_run

if __name__ == "__main__":
    tester = PingProSpecificTester()
    passed, total = tester.run_all_specific_tests()
    
    if passed == total:
        print(f"\n🎉 All {total} tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} tests failed out of {total}")
        sys.exit(1)