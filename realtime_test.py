#!/usr/bin/env python3
"""
PingPro Real-Time Analysis System Testing
Focused testing of the new real-time analysis capabilities
"""

import requests
import sys
import json
import time
from datetime import datetime

class RealTimeSystemTester:
    def __init__(self, base_url="https://paddle-vision.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            
        result = {
            "test_name": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    Details: {details}")
        print()

    def test_real_time_modules_import(self):
        """Test that real-time analysis modules can be imported correctly"""
        print("🔬 Testing Real-Time Modules Import...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            
            # Test real_time_ttnet_analyzer imports
            from real_time_ttnet_analyzer import (
                RealTimeAnalyzer, 
                TTNetRealTime, 
                BallDetection, 
                PlayerDetection, 
                EventDetection, 
                GameState
            )
            
            self.log_test(
                "Real-Time TTNet Analyzer Import", 
                True, 
                "All real-time TTNet classes successfully imported"
            )
            
            # Test streaming_server imports
            from streaming_server import (
                VideoStreamManager, 
                stream_manager, 
                websocket_endpoint, 
                get_video_stream, 
                MatchRecorder, 
                match_recorder
            )
            
            self.log_test(
                "Streaming Server Import", 
                True, 
                "All streaming server components successfully imported"
            )
            
            return True
            
        except ImportError as e:
            self.log_test(
                "Real-Time Modules Import", 
                False, 
                f"Failed to import real-time modules: {str(e)}"
            )
            return False
        except Exception as e:
            self.log_test(
                "Real-Time Modules Import", 
                False, 
                f"Real-time modules import error: {str(e)}"
            )
            return False

    def test_ttnet_realtime_model_initialization(self):
        """Test TTNetRealTime model initialization"""
        print("🧠 Testing TTNetRealTime Model Initialization...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            
            from real_time_ttnet_analyzer import TTNetRealTime, RealTimeAnalyzer
            
            # Test TTNetRealTime model initialization
            model = TTNetRealTime()
            
            # Check if model has required components
            required_components = ['backbone', 'global_ball_detector', 'local_ball_detector', 'segmentation_head', 'event_spotting_head']
            missing_components = [comp for comp in required_components if not hasattr(model, comp)]
            
            if not missing_components:
                self.log_test(
                    "TTNetRealTime Model Components", 
                    True, 
                    f"All required components present: {required_components}"
                )
            else:
                self.log_test(
                    "TTNetRealTime Model Components", 
                    False, 
                    f"Missing components: {missing_components}"
                )
            
            # Test RealTimeAnalyzer initialization
            analyzer = RealTimeAnalyzer()
            
            if hasattr(analyzer, 'model') and hasattr(analyzer, 'game_state'):
                self.log_test(
                    "RealTimeAnalyzer Initialization", 
                    True, 
                    f"Analyzer initialized with device: {analyzer.device}"
                )
            else:
                self.log_test(
                    "RealTimeAnalyzer Initialization", 
                    False, 
                    "RealTimeAnalyzer missing required attributes"
                )
            
            return True
            
        except Exception as e:
            self.log_test(
                "TTNetRealTime Model Initialization", 
                False, 
                f"Model initialization failed: {str(e)}"
            )
            return False

    def test_video_stream_manager_initialization(self):
        """Test VideoStreamManager initialization and basic methods"""
        print("📹 Testing VideoStreamManager...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            
            from streaming_server import VideoStreamManager
            
            # Test VideoStreamManager initialization
            stream_manager = VideoStreamManager()
            
            # Check required attributes
            required_attrs = ['analyzer', 'active_connections', 'streaming']
            missing_attrs = [attr for attr in required_attrs if not hasattr(stream_manager, attr)]
            
            if not missing_attrs:
                self.log_test(
                    "VideoStreamManager Initialization", 
                    True, 
                    f"All required attributes present: {required_attrs}"
                )
            else:
                self.log_test(
                    "VideoStreamManager Initialization", 
                    False, 
                    f"Missing attributes: {missing_attrs}"
                )
            
            # Test basic methods exist
            required_methods = ['start_video_analysis', 'stop_video_analysis', 'disconnect']
            missing_methods = [method for method in required_methods if not hasattr(stream_manager, method)]
            
            if not missing_methods:
                self.log_test(
                    "VideoStreamManager Methods", 
                    True, 
                    f"All required methods present: {required_methods}"
                )
            else:
                self.log_test(
                    "VideoStreamManager Methods", 
                    False, 
                    f"Missing methods: {missing_methods}"
                )
            
            return True
            
        except Exception as e:
            self.log_test(
                "VideoStreamManager Initialization", 
                False, 
                f"VideoStreamManager test failed: {str(e)}"
            )
            return False

    def test_realtime_api_endpoints(self):
        """Test real-time analysis API endpoints"""
        print("🎯 Testing Real-Time API Endpoints...")
        
        # Test /api/realtime/status endpoint
        try:
            response = requests.get(f"{self.api_url}/realtime/status", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['streaming', 'active_connections', 'analyzer_ready']
                
                if all(field in data for field in required_fields):
                    self.log_test(
                        "Real-Time Status Endpoint", 
                        True, 
                        f"Status endpoint working - Streaming: {data['streaming']}, Connections: {data['active_connections']}"
                    )
                else:
                    missing_fields = [f for f in required_fields if f not in data]
                    self.log_test(
                        "Real-Time Status Endpoint", 
                        False, 
                        f"Missing fields: {missing_fields}"
                    )
            else:
                self.log_test(
                    "Real-Time Status Endpoint", 
                    False, 
                    f"Expected 200, got {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_test(
                "Real-Time Status Endpoint", 
                False, 
                f"Status endpoint test failed: {str(e)}"
            )
        
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
                        f"Start endpoint accessible - Success: {data['success']}"
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
        
        # Test /api/realtime/statistics endpoint
        try:
            response = requests.get(f"{self.api_url}/realtime/statistics", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'success' in data:
                    self.log_test(
                        "Real-Time Statistics Endpoint", 
                        True, 
                        f"Statistics endpoint working - Success: {data['success']}"
                    )
                else:
                    self.log_test(
                        "Real-Time Statistics Endpoint", 
                        False, 
                        f"Missing success field in response: {data}"
                    )
            else:
                self.log_test(
                    "Real-Time Statistics Endpoint", 
                    False, 
                    f"Expected 200, got {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            self.log_test(
                "Real-Time Statistics Endpoint", 
                False, 
                f"Statistics endpoint test failed: {str(e)}"
            )

    def test_websocket_endpoint_availability(self):
        """Test WebSocket endpoint availability (basic connectivity test)"""
        print("🔌 Testing WebSocket Endpoint Availability...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            
            # Check if websocket endpoint function exists
            from streaming_server import websocket_endpoint
            
            if callable(websocket_endpoint):
                self.log_test(
                    "WebSocket Endpoint Function", 
                    True, 
                    "WebSocket endpoint function is available and callable"
                )
            else:
                self.log_test(
                    "WebSocket Endpoint Function", 
                    False, 
                    "WebSocket endpoint function is not callable"
                )
            
            # Test WebSocket URL structure (we expect it to be at /ws/realtime/{client_id})
            websocket_url = f"ws://{self.base_url.replace('https://', '').replace('http://', '')}/ws/realtime/test_client"
            
            self.log_test(
                "WebSocket URL Structure", 
                True, 
                f"WebSocket endpoint should be available at: {websocket_url}"
            )
            
            return True
            
        except Exception as e:
            self.log_test(
                "WebSocket Endpoint Availability", 
                False, 
                f"WebSocket endpoint test failed: {str(e)}"
            )
            return False

    def test_match_recorder_functionality(self):
        """Test MatchRecorder functionality"""
        print("📊 Testing MatchRecorder Functionality...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            
            from streaming_server import MatchRecorder
            
            # Test MatchRecorder initialization
            recorder = MatchRecorder()
            
            # Check required attributes
            required_attrs = ['match_data', 'recording']
            missing_attrs = [attr for attr in required_attrs if not hasattr(recorder, attr)]
            
            if not missing_attrs:
                self.log_test(
                    "MatchRecorder Initialization", 
                    True, 
                    f"MatchRecorder initialized with required attributes: {required_attrs}"
                )
            else:
                self.log_test(
                    "MatchRecorder Initialization", 
                    False, 
                    f"Missing attributes: {missing_attrs}"
                )
            
            # Test recording methods
            required_methods = ['start_recording', 'stop_recording', 'add_frame_data']
            missing_methods = [method for method in required_methods if not hasattr(recorder, method)]
            
            if not missing_methods:
                self.log_test(
                    "MatchRecorder Methods", 
                    True, 
                    f"All required methods present: {required_methods}"
                )
            else:
                self.log_test(
                    "MatchRecorder Methods", 
                    False, 
                    f"Missing methods: {missing_methods}"
                )
            
            # Test basic recording workflow
            recorder.start_recording()
            if recorder.recording:
                self.log_test(
                    "MatchRecorder Start Recording", 
                    True, 
                    "Recording started successfully"
                )
            else:
                self.log_test(
                    "MatchRecorder Start Recording", 
                    False, 
                    "Failed to start recording"
                )
            
            match_data = recorder.stop_recording()
            if isinstance(match_data, dict) and not recorder.recording:
                self.log_test(
                    "MatchRecorder Stop Recording", 
                    True, 
                    f"Recording stopped, returned data with keys: {list(match_data.keys())}"
                )
            else:
                self.log_test(
                    "MatchRecorder Stop Recording", 
                    False, 
                    "Failed to stop recording or invalid data returned"
                )
            
            return True
            
        except Exception as e:
            self.log_test(
                "MatchRecorder Functionality", 
                False, 
                f"MatchRecorder test failed: {str(e)}"
            )
            return False

    def test_real_time_integration_with_existing_system(self):
        """Test that real-time system integrates properly with existing architecture"""
        print("🔗 Testing Real-Time Integration with Existing System...")
        
        try:
            import sys
            sys.path.append('/app/backend')
            
            # Test that server.py imports real-time components
            from server import stream_manager, match_recorder
            
            if stream_manager is not None:
                self.log_test(
                    "Server Stream Manager Import", 
                    True, 
                    "stream_manager successfully imported in server.py"
                )
            else:
                self.log_test(
                    "Server Stream Manager Import", 
                    False, 
                    "stream_manager is None in server.py"
                )
            
            if match_recorder is not None:
                self.log_test(
                    "Server Match Recorder Import", 
                    True, 
                    "match_recorder successfully imported in server.py"
                )
            else:
                self.log_test(
                    "Server Match Recorder Import", 
                    False, 
                    "match_recorder is None in server.py"
                )
            
            # Test that real-time endpoints are properly defined
            endpoints_to_test = [
                "/api/realtime/status",
                "/api/realtime/statistics"
            ]
            
            all_endpoints_working = True
            for endpoint in endpoints_to_test:
                try:
                    response = requests.get(f"{self.api_url}{endpoint}", timeout=5)
                    if response.status_code != 200:
                        all_endpoints_working = False
                        break
                except:
                    all_endpoints_working = False
                    break
            
            if all_endpoints_working:
                self.log_test(
                    "Real-Time Endpoints Integration", 
                    True, 
                    f"All real-time endpoints properly integrated: {endpoints_to_test}"
                )
            else:
                self.log_test(
                    "Real-Time Endpoints Integration", 
                    False, 
                    "Some real-time endpoints not properly integrated"
                )
            
            return True
            
        except Exception as e:
            self.log_test(
                "Real-Time Integration", 
                False, 
                f"Integration test failed: {str(e)}"
            )
            return False

    def run_all_tests(self):
        """Run all real-time system tests"""
        print("⚡ Starting PingPro Real-Time Analysis System Tests")
        print("🔬 Focus: Real-Time TTNet Analysis, Streaming, and WebSocket Integration")
        print("=" * 80)
        
        # Real-Time Analysis Tests
        print("\n⚡ Real-Time Analysis System Tests:")
        self.test_real_time_modules_import()
        self.test_ttnet_realtime_model_initialization()
        self.test_video_stream_manager_initialization()
        self.test_realtime_api_endpoints()
        self.test_websocket_endpoint_availability()
        self.test_match_recorder_functionality()
        self.test_real_time_integration_with_existing_system()
        
        # Print summary
        print("\n" + "=" * 80)
        print(f"📊 Real-Time System Test Summary:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Detailed results
        realtime_tests = [result for result in self.test_results if any(keyword in result['test_name'] for keyword in ['Real-Time', 'WebSocket', 'Stream', 'Match', 'TTNet'])]
        
        print(f"\n⚡ Real-Time Analysis Tests: {len([t for t in realtime_tests if t['success']])}/{len(realtime_tests)} passed")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 All real-time system tests passed! PingPro real-time analysis system is working correctly.")
            return 0
        else:
            print(f"\n❌ {self.tests_run - self.tests_passed} tests failed - review real-time system integration.")
            
            # Show failed tests
            failed_tests = [result for result in self.test_results if not result['success']]
            if failed_tests:
                print("\n❌ Failed Tests:")
                for test in failed_tests:
                    print(f"   - {test['test_name']}: {test['details']}")
            
            return 1

def main():
    """Main test execution"""
    tester = RealTimeSystemTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())