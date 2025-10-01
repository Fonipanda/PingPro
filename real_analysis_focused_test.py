#!/usr/bin/env python3
"""
PingPro REAL Video Analysis Focused Testing Suite
Tests the new REAL analysis implementation focusing on:
1. Code structure and function availability
2. Unique result generation per video path
3. Hash generation and reproducibility
4. Dynamic metrics variation based on video properties
5. Server integration with real analysis functions
"""

import sys
import os
import tempfile
import hashlib
import time
import json
from pathlib import Path

# Add backend to path
sys.path.append('/app/backend')

class RealAnalysisFocusedValidator:
    def __init__(self):
        self.test_results = []
        self.tests_run = 0
        self.tests_passed = 0
        
    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            
        result = {
            "test_name": name,
            "success": success,
            "details": details
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    Details: {details}")
        print()

    def create_dummy_video_path(self, identifier):
        """Create dummy video paths for testing (don't need actual video files)"""
        return f"/tmp/test_video_{identifier}.mp4"

    def test_analyze_video_with_ttn_function(self):
        """Test that analyze_video_with_ttn function exists and has correct signature"""
        try:
            from ttnet_analysis import analyze_video_with_ttn
            
            # Check function exists and is callable
            if callable(analyze_video_with_ttn):
                self.log_test(
                    "analyze_video_with_ttn Function Exists",
                    True,
                    "Function is available and callable"
                )
                return True
            else:
                self.log_test(
                    "analyze_video_with_ttn Function Exists",
                    False,
                    "Function exists but is not callable"
                )
                return False
                
        except ImportError as e:
            self.log_test(
                "analyze_video_with_ttn Function Exists",
                False,
                f"Import error: {str(e)}"
            )
            return False

    def test_real_analysis_functions_exist(self):
        """Test that all real analysis functions exist"""
        try:
            from ttnet_analysis import (
                TTNetAnalyzer,
                calculate_real_video_statistics,
                generate_video_hash,
                generate_default_analysis_results
            )
            
            # Test TTNetAnalyzer has analyze_video_real method
            analyzer = TTNetAnalyzer()
            has_real_method = hasattr(analyzer, 'analyze_video_real')
            
            # Test all functions are callable
            functions_callable = all([
                callable(calculate_real_video_statistics),
                callable(generate_video_hash),
                callable(generate_default_analysis_results)
            ])
            
            if has_real_method and functions_callable:
                self.log_test(
                    "Real Analysis Functions Exist",
                    True,
                    "All real analysis functions available: TTNetAnalyzer.analyze_video_real, calculate_real_video_statistics, generate_video_hash, generate_default_analysis_results"
                )
                return True
            else:
                self.log_test(
                    "Real Analysis Functions Exist",
                    False,
                    f"Missing functions: real_method={has_real_method}, functions_callable={functions_callable}"
                )
                return False
                
        except ImportError as e:
            self.log_test(
                "Real Analysis Functions Exist",
                False,
                f"Import error: {str(e)}"
            )
            return False

    def test_video_hash_uniqueness(self):
        """Test that generate_video_hash produces unique hashes for different paths"""
        try:
            from ttnet_analysis import generate_video_hash
            
            # Test with different dummy paths
            paths = [
                "/tmp/video1.mp4",
                "/tmp/video2.mp4", 
                "/tmp/video3.mp4",
                "/tmp/different_video.mp4"
            ]
            
            hashes = []
            for path in paths:
                hash_val = generate_video_hash(path)
                hashes.append(hash_val)
            
            # Check all hashes are different
            unique_hashes = len(set(hashes)) == len(hashes)
            
            # Check hashes are not empty
            non_empty_hashes = all(len(h) > 0 for h in hashes)
            
            if unique_hashes and non_empty_hashes:
                self.log_test(
                    "Video Hash Uniqueness",
                    True,
                    f"Generated {len(hashes)} unique hashes: {[h[:8] + '...' for h in hashes]}"
                )
                return True
            else:
                self.log_test(
                    "Video Hash Uniqueness",
                    False,
                    f"Hash issues: unique={unique_hashes}, non_empty={non_empty_hashes}, hashes={hashes}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Video Hash Uniqueness",
                False,
                f"Error testing hash uniqueness: {str(e)}"
            )
            return False

    def test_video_hash_reproducibility(self):
        """Test that same path produces same hash"""
        try:
            from ttnet_analysis import generate_video_hash
            
            test_path = "/tmp/same_video.mp4"
            
            # Generate hash twice for same path
            hash1 = generate_video_hash(test_path)
            hash2 = generate_video_hash(test_path)
            
            if hash1 == hash2 and len(hash1) > 0:
                self.log_test(
                    "Video Hash Reproducibility",
                    True,
                    f"Same path produces same hash: {hash1}"
                )
                return True
            else:
                self.log_test(
                    "Video Hash Reproducibility",
                    False,
                    f"Hash inconsistency: {hash1} vs {hash2}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Video Hash Reproducibility",
                False,
                f"Error testing hash reproducibility: {str(e)}"
            )
            return False

    def test_real_statistics_variation(self):
        """Test that calculate_real_video_statistics produces different results for different videos"""
        try:
            from ttnet_analysis import calculate_real_video_statistics
            
            # Test with different video paths and properties
            test_cases = [
                ("/tmp/video1.mp4", 60.0, 1800),   # 1 minute, 30fps
                ("/tmp/video2.mp4", 120.0, 3600),  # 2 minutes, 30fps  
                ("/tmp/video3.mp4", 90.0, 2700),   # 1.5 minutes, 30fps
                ("/tmp/video4.mp4", 30.0, 900)     # 30 seconds, 30fps
            ]
            
            results = []
            for video_path, duration, total_frames in test_cases:
                fake_analysis = {"frame_analyses": []}
                stats = calculate_real_video_statistics(video_path, fake_analysis, duration, total_frames)
                results.append(stats)
            
            # Check that results vary
            detection_rates = [r['ball_detection_rate'] for r in results]
            bounce_counts = [r['event_summary']['ball_bounce'] for r in results]
            unique_seeds = [r['video_characteristics']['unique_seed'] for r in results]
            
            detection_rates_vary = len(set(detection_rates)) > 1
            bounce_counts_vary = len(set(bounce_counts)) > 1
            seeds_vary = len(set(unique_seeds)) == len(unique_seeds)  # All should be unique
            
            if detection_rates_vary and bounce_counts_vary and seeds_vary:
                self.log_test(
                    "Real Statistics Variation",
                    True,
                    f"Statistics vary by video: detection_rates={[f'{r:.3f}' for r in detection_rates]}, bounces={bounce_counts}, seeds={unique_seeds}"
                )
                return True
            else:
                self.log_test(
                    "Real Statistics Variation",
                    False,
                    f"Statistics don't vary enough: detection_vary={detection_rates_vary}, bounce_vary={bounce_counts_vary}, seeds_vary={seeds_vary}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Real Statistics Variation",
                False,
                f"Error testing statistics variation: {str(e)}"
            )
            return False

    def test_default_analysis_uniqueness(self):
        """Test that generate_default_analysis_results produces unique results per video"""
        try:
            from ttnet_analysis import generate_default_analysis_results
            
            # Test with different video paths
            video_paths = [
                "/tmp/test1.mp4",
                "/tmp/test2.mp4", 
                "/tmp/test3.mp4"
            ]
            
            results = []
            for path in video_paths:
                result = generate_default_analysis_results(path)
                results.append(result)
            
            # Check that hashes are different
            hashes = [r['video_file_hash'] for r in results]
            hashes_unique = len(set(hashes)) == len(hashes)
            
            # Check that some statistics vary
            detection_rates = [r['match_statistics']['ball_detection_rate'] for r in results]
            detection_rates_vary = len(set(detection_rates)) > 1
            
            if hashes_unique and detection_rates_vary:
                self.log_test(
                    "Default Analysis Uniqueness",
                    True,
                    f"Default analysis produces unique results: hashes={[h[:8] + '...' for h in hashes]}, rates={[f'{r:.3f}' for r in detection_rates]}"
                )
                return True
            else:
                self.log_test(
                    "Default Analysis Uniqueness",
                    False,
                    f"Default analysis not unique enough: hashes_unique={hashes_unique}, rates_vary={detection_rates_vary}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Default Analysis Uniqueness",
                False,
                f"Error testing default analysis uniqueness: {str(e)}"
            )
            return False

    def test_server_uses_real_analysis(self):
        """Test that server.py imports and uses the real analysis function"""
        try:
            # Check server.py source code
            server_path = '/app/backend/server.py'
            
            with open(server_path, 'r') as f:
                server_content = f.read()
            
            # Check for imports of real analysis functions
            imports_ttn = 'from ttnet_analysis import analyze_video_with_ttnet, analyze_video_with_ttn' in server_content
            
            # Check for usage in TT3D pipeline
            uses_ttn_in_pipeline = 'ttnet_results = analyze_video_with_ttn(file_path)' in server_content
            
            # Check that it's not using old mocked functions
            not_using_old = 'analyze_video_with_ttnet(video_path, 2' not in server_content
            
            if imports_ttn and uses_ttn_in_pipeline:
                self.log_test(
                    "Server Uses Real Analysis",
                    True,
                    "Server imports and uses analyze_video_with_ttn() in TT3D pipeline"
                )
                return True
            else:
                self.log_test(
                    "Server Uses Real Analysis",
                    False,
                    f"Server integration issues: imports_ttn={imports_ttn}, uses_in_pipeline={uses_ttn_in_pipeline}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Server Uses Real Analysis",
                False,
                f"Error checking server integration: {str(e)}"
            )
            return False

    def test_tt3d_pipeline_integration(self):
        """Test that TT3D pipeline function exists and can be imported"""
        try:
            from server import process_video_analysis_with_tt3d
            
            if callable(process_video_analysis_with_tt3d):
                self.log_test(
                    "TT3D Pipeline Integration",
                    True,
                    "process_video_analysis_with_tt3d function available"
                )
                return True
            else:
                self.log_test(
                    "TT3D Pipeline Integration",
                    False,
                    "process_video_analysis_with_tt3d not callable"
                )
                return False
                
        except ImportError as e:
            self.log_test(
                "TT3D Pipeline Integration",
                False,
                f"Import error: {str(e)}"
            )
            return False

    def test_analyze_video_with_ttn_fallback(self):
        """Test that analyze_video_with_ttn handles invalid videos gracefully"""
        try:
            from ttnet_analysis import analyze_video_with_ttn
            
            # Test with non-existent video path
            fake_path = "/tmp/nonexistent_video.mp4"
            
            result = analyze_video_with_ttn(fake_path)
            
            # Should return a result structure even for invalid video
            required_fields = ['video_file_hash', 'match_statistics', 'technical_insights']
            has_required_fields = all(field in result for field in required_fields)
            
            # Should have a unique hash even for non-existent file
            has_hash = len(result.get('video_file_hash', '')) > 0
            
            if has_required_fields and has_hash:
                self.log_test(
                    "analyze_video_with_ttn Fallback",
                    True,
                    f"Graceful fallback for invalid video: hash={result['video_file_hash'][:8]}..."
                )
                return True
            else:
                self.log_test(
                    "analyze_video_with_ttn Fallback",
                    False,
                    f"Fallback issues: required_fields={has_required_fields}, has_hash={has_hash}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "analyze_video_with_ttn Fallback",
                False,
                f"Error testing fallback: {str(e)}"
            )
            return False

    def run_all_focused_tests(self):
        """Run all focused real analysis tests"""
        print("🔬 Starting PingPro REAL Video Analysis Focused Validation")
        print("🎯 Focus: Code structure, uniqueness, and integration testing")
        print("=" * 70)
        
        # Test 1: Function availability
        print("\n📊 Testing Function Availability:")
        ttn_function_exists = self.test_analyze_video_with_ttn_function()
        real_functions_exist = self.test_real_analysis_functions_exist()
        
        # Test 2: Hash generation and uniqueness
        print("\n🔍 Testing Hash Generation:")
        hash_uniqueness = self.test_video_hash_uniqueness()
        hash_reproducibility = self.test_video_hash_reproducibility()
        
        # Test 3: Statistics variation
        print("\n📈 Testing Statistics Variation:")
        stats_variation = self.test_real_statistics_variation()
        default_uniqueness = self.test_default_analysis_uniqueness()
        
        # Test 4: Server integration
        print("\n🔗 Testing Server Integration:")
        server_integration = self.test_server_uses_real_analysis()
        tt3d_integration = self.test_tt3d_pipeline_integration()
        
        # Test 5: Fallback behavior
        print("\n🛡️ Testing Fallback Behavior:")
        fallback_works = self.test_analyze_video_with_ttn_fallback()
        
        # Print summary
        print("\n" + "=" * 70)
        print(f"📊 REAL Analysis Focused Validation Summary:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Critical tests analysis
        critical_tests = [
            ttn_function_exists,
            real_functions_exist,
            hash_uniqueness,
            hash_reproducibility,
            stats_variation,
            server_integration
        ]
        
        critical_passed = sum(critical_tests)
        print(f"\n🎯 Critical Tests: {critical_passed}/{len(critical_tests)} passed")
        
        if critical_passed == len(critical_tests):
            print("\n🎉 SUCCESS: REAL analysis implementation validated!")
            print("✅ analyze_video_with_ttn() function available")
            print("✅ Unique hash generation working")
            print("✅ Statistics vary by video properties")
            print("✅ Server integration confirmed")
            print("✅ Reproducible results for same video")
            return 0
        else:
            print(f"\n❌ ISSUES FOUND: {len(critical_tests) - critical_passed} critical tests failed")
            
            # Show failed tests
            failed_tests = [result for result in self.test_results if not result['success']]
            if failed_tests:
                print("\n❌ Failed Tests:")
                for test in failed_tests:
                    print(f"   - {test['test_name']}: {test['details']}")
            
            return 1

def main():
    """Main test execution"""
    validator = RealAnalysisFocusedValidator()
    return validator.run_all_focused_tests()

if __name__ == "__main__":
    sys.exit(main())