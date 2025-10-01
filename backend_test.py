#!/usr/bin/env python3
"""
PingPro Backend API Testing Suite
Tests all backend endpoints for the table tennis video analysis application
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

    def run_all_tests(self):
        """Run all backend API tests"""
        print("🏓 Starting PingPro Backend API Tests")
        print("=" * 50)
        
        # Test 1: Root endpoint
        self.test_root_endpoint()
        
        # Test 2: CORS headers
        self.test_cors_headers()
        
        # Test 3: Invalid file format upload
        self.test_video_upload_invalid_format()
        
        # Test 4: Valid file format upload
        upload_success, analysis_id = self.test_video_upload_valid_format()
        
        # Test 5: Analysis status check
        if upload_success and analysis_id:
            self.test_analysis_status(analysis_id)
            
            # Test 6: Analysis results when not ready
            self.test_analysis_results_not_ready(analysis_id)
        
        # Test 7: Invalid analysis ID
        self.test_invalid_analysis_id()
        
        # Print summary
        print("=" * 50)
        print(f"📊 Test Summary:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("❌ Some tests failed!")
            return 1

def main():
    """Main test execution"""
    tester = PingProAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())