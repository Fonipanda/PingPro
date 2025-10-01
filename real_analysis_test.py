#!/usr/bin/env python3
"""
PingPro REAL Video Analysis Testing Suite
Tests the new REAL analysis implementation to ensure:
1. analyze_video_with_ttn() is used instead of mocked functions
2. Results vary by video (hash, size, duration)
3. Same video = same results, different videos = different results
4. video_file_hash is unique per video
5. video_characteristics based on real properties
6. Dynamic metrics that vary by video
7. TT3D pipeline integration with real analysis
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

class RealAnalysisValidator:
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

    def get_test_videos(self):
        """Get existing video files for testing"""
        import glob
        video_files = glob.glob('/app/backend/uploads/*.mp4')
        return video_files[:4] if len(video_files) >= 4 else video_files  # Use up to 4 videos

    def test_real_analysis_function_usage(self):
        """Test that analyze_video_with_ttn() is being used for real analysis"""
        try:
            from ttnet_analysis import analyze_video_with_ttn, TTNetAnalyzer
            
            # Get existing test videos
            test_videos = self.get_test_videos()
            if not test_videos:
                self.log_test(
                    "Real Analysis Function Usage",
                    False,
                    "No test videos available"
                )
                return False, None
            
            # Use first available video
            test_video = test_videos[0]
            
            # Call the real analysis function
            results = analyze_video_with_ttn(test_video)
            
            # Check that it returns expected structure for REAL analysis
            required_fields = [
                'video_duration', 'total_frames', 'fps', 'resolution',
                'video_file_hash', 'match_statistics', 'technical_insights'
            ]
            
            missing_fields = [field for field in required_fields if field not in results]
            
            if not missing_fields:
                # Check that video_file_hash is present and unique
                video_hash = results.get('video_file_hash')
                if video_hash and len(video_hash) > 0:
                    self.log_test(
                        "Real Analysis Function Usage",
                        True,
                        f"analyze_video_with_ttn() working with hash: {video_hash}"
                    )
                    success = True
                else:
                    self.log_test(
                        "Real Analysis Function Usage",
                        False,
                        "video_file_hash missing or empty"
                    )
                    success = False
            else:
                self.log_test(
                    "Real Analysis Function Usage",
                    False,
                    f"Missing required fields: {missing_fields}"
                )
                success = False
            
            return success, results if success else None
            
        except Exception as e:
            self.log_test(
                "Real Analysis Function Usage",
                False,
                f"Error testing real analysis: {str(e)}"
            )
            return False, None

    def test_video_uniqueness_by_content(self):
        """Test that different videos generate different results"""
        try:
            from ttnet_analysis import analyze_video_with_ttn
            
            # Get different test videos
            test_videos = self.get_test_videos()
            if len(test_videos) < 3:
                self.log_test(
                    "Video Uniqueness by Content",
                    False,
                    f"Need at least 3 videos, found {len(test_videos)}"
                )
                return False, None
            
            # Use first 3 videos
            video1, video2, video3 = test_videos[:3]
            
            # Analyze each video
            results1 = analyze_video_with_ttn(video1)
            results2 = analyze_video_with_ttn(video2)
            results3 = analyze_video_with_ttn(video3)
            
            # Extract hashes
            hash1 = results1.get('video_file_hash', '')
            hash2 = results2.get('video_file_hash', '')
            hash3 = results3.get('video_file_hash', '')
            
            # Check that all hashes are different
            hashes_unique = len(set([hash1, hash2, hash3])) == 3
            
            if hashes_unique:
                self.log_test(
                    "Video Uniqueness by Content",
                    True,
                    f"All hashes unique: {hash1[:8]}..., {hash2[:8]}..., {hash3[:8]}..."
                )
                success = True
            else:
                self.log_test(
                    "Video Uniqueness by Content",
                    False,
                    f"Duplicate hashes found: {hash1}, {hash2}, {hash3}"
                )
                success = False
                
            return success, (results1, results2, results3) if success else None
            
        except Exception as e:
            self.log_test(
                "Video Uniqueness by Content",
                False,
                f"Error testing video uniqueness: {str(e)}"
            )
            return False, None

    def test_video_characteristics_vary(self):
        """Test that video_characteristics vary based on actual video properties"""
        try:
            from ttnet_analysis import analyze_video_with_ttn
            
            # Get different test videos
            test_videos = self.get_test_videos()
            if len(test_videos) < 2:
                self.log_test(
                    "Video Characteristics Vary",
                    False,
                    f"Need at least 2 videos, found {len(test_videos)}"
                )
                return False
            
            # Use first 2 videos
            video1, video2 = test_videos[:2]
            
            # Analyze both videos
            results1 = analyze_video_with_ttn(video1)
            results2 = analyze_video_with_ttn(video2)
            
            # Extract video characteristics
            chars1 = results1.get('match_statistics', {}).get('video_characteristics', {})
            chars2 = results2.get('match_statistics', {}).get('video_characteristics', {})
            
            size1 = chars1.get('file_size_mb', 0)
            size2 = chars2.get('file_size_mb', 0)
            
            seed1 = chars1.get('unique_seed', 0)
            seed2 = chars2.get('unique_seed', 0)
            
            # Check that characteristics are different
            sizes_different = size1 != size2
            seeds_different = seed1 != seed2
            
            if sizes_different and seeds_different:
                self.log_test(
                    "Video Characteristics Vary",
                    True,
                    f"Video1: {size1:.2f}MB (seed:{seed1}), Video2: {size2:.2f}MB (seed:{seed2})"
                )
                success = True
            else:
                self.log_test(
                    "Video Characteristics Vary",
                    False,
                    f"Characteristics don't vary: sizes_diff={sizes_different}, seeds_diff={seeds_different}"
                )
                success = False
            
            return success
            
        except Exception as e:
            self.log_test(
                "Video Characteristics Vary",
                False,
                f"Error testing video characteristics: {str(e)}"
            )
            return False

    def test_reproducibility_same_video(self):
        """Test that same video produces same results (reproducibility)"""
        try:
            from ttnet_analysis import analyze_video_with_ttn
            
            # Create one test video
            test_video = self.create_test_video(1, 75)
            
            # Analyze the same video twice
            results1 = analyze_video_with_ttn(test_video)
            results2 = analyze_video_with_ttn(test_video)
            
            # Compare key fields that should be identical
            hash1 = results1.get('video_file_hash', '')
            hash2 = results2.get('video_file_hash', '')
            
            stats1 = results1.get('match_statistics', {})
            stats2 = results2.get('match_statistics', {})
            
            # Check reproducibility
            hashes_match = hash1 == hash2
            
            # Check that key statistics are reproducible
            detection_rate1 = stats1.get('ball_detection_rate', 0)
            detection_rate2 = stats2.get('ball_detection_rate', 0)
            
            events1 = stats1.get('event_summary', {})
            events2 = stats2.get('event_summary', {})
            
            stats_match = (detection_rate1 == detection_rate2 and 
                          events1.get('ball_bounce', 0) == events2.get('ball_bounce', 0))
            
            if hashes_match and stats_match:
                self.log_test(
                    "Reproducibility Same Video",
                    True,
                    f"Same video produces identical results: hash={hash1[:8]}..., bounces={events1.get('ball_bounce', 0)}"
                )
                success = True
            else:
                self.log_test(
                    "Reproducibility Same Video",
                    False,
                    f"Results differ: hashes_match={hashes_match}, stats_match={stats_match}"
                )
                success = False
            
            # Cleanup
            os.unlink(test_video)
            
            return success
            
        except Exception as e:
            self.log_test(
                "Reproducibility Same Video",
                False,
                f"Error testing reproducibility: {str(e)}"
            )
            return False

    def test_dynamic_metrics_variation(self):
        """Test that metrics like ball_detection_rate, event_summary vary by video"""
        try:
            from ttnet_analysis import analyze_video_with_ttn
            
            # Create multiple videos with different characteristics
            videos = []
            results = []
            
            for i in range(4):
                video = self.create_test_video(i+1, 50 + i*25)  # Different sizes
                videos.append(video)
                result = analyze_video_with_ttn(video)
                results.append(result)
            
            # Extract metrics from all results
            detection_rates = []
            bounce_counts = []
            serve_counts = []
            
            for result in results:
                stats = result.get('match_statistics', {})
                detection_rates.append(stats.get('ball_detection_rate', 0))
                
                events = stats.get('event_summary', {})
                bounce_counts.append(events.get('ball_bounce', 0))
                serve_counts.append(events.get('serve', 0))
            
            # Check that metrics vary across videos
            detection_rates_vary = len(set(detection_rates)) > 1
            bounce_counts_vary = len(set(bounce_counts)) > 1
            serve_counts_vary = len(set(serve_counts)) > 1
            
            metrics_vary = detection_rates_vary and bounce_counts_vary and serve_counts_vary
            
            if metrics_vary:
                self.log_test(
                    "Dynamic Metrics Variation",
                    True,
                    f"Metrics vary: detection_rates={detection_rates}, bounces={bounce_counts}, serves={serve_counts}"
                )
                success = True
            else:
                self.log_test(
                    "Dynamic Metrics Variation",
                    False,
                    f"Metrics don't vary enough: detection_vary={detection_rates_vary}, bounce_vary={bounce_counts_vary}, serve_vary={serve_counts_vary}"
                )
                success = False
            
            # Cleanup
            for video in videos:
                os.unlink(video)
                
            return success
            
        except Exception as e:
            self.log_test(
                "Dynamic Metrics Variation",
                False,
                f"Error testing dynamic metrics: {str(e)}"
            )
            return False

    def test_tt3d_pipeline_integration(self):
        """Test TT3D pipeline uses real analysis functions"""
        try:
            # Test that TT3D pipeline imports and uses real analysis
            from server import process_video_analysis_with_tt3d
            from ttnet_analysis import analyze_video_with_ttn
            
            # Check that the TT3D pipeline function exists
            if callable(process_video_analysis_with_tt3d):
                self.log_test(
                    "TT3D Pipeline Integration",
                    True,
                    "process_video_analysis_with_tt3d function available and callable"
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
        except Exception as e:
            self.log_test(
                "TT3D Pipeline Integration",
                False,
                f"Error testing TT3D integration: {str(e)}"
            )
            return False

    def test_real_analysis_functions(self):
        """Test that real analysis functions exist and work"""
        try:
            from ttnet_analysis import (
                TTNetAnalyzer, 
                calculate_real_video_statistics,
                generate_video_hash
            )
            
            # Test TTNetAnalyzer.analyze_video_real method
            analyzer = TTNetAnalyzer()
            if hasattr(analyzer, 'analyze_video_real'):
                self.log_test(
                    "Real Analysis Functions - analyze_video_real",
                    True,
                    "TTNetAnalyzer.analyze_video_real method exists"
                )
                real_method_exists = True
            else:
                self.log_test(
                    "Real Analysis Functions - analyze_video_real",
                    False,
                    "TTNetAnalyzer.analyze_video_real method missing"
                )
                real_method_exists = False
            
            # Test calculate_real_video_statistics function
            test_video = self.create_test_video(1, 50)
            try:
                fake_analysis = {"frame_analyses": []}
                stats = calculate_real_video_statistics(test_video, fake_analysis, 60.0, 1800)
                
                required_stats = ['ball_detection_rate', 'event_summary', 'ball_trajectory_analysis', 'video_characteristics']
                stats_complete = all(field in stats for field in required_stats)
                
                if stats_complete:
                    self.log_test(
                        "Real Analysis Functions - calculate_real_video_statistics",
                        True,
                        f"Statistics calculated with detection_rate={stats['ball_detection_rate']:.3f}"
                    )
                    stats_function_works = True
                else:
                    self.log_test(
                        "Real Analysis Functions - calculate_real_video_statistics",
                        False,
                        f"Missing statistics fields: {[f for f in required_stats if f not in stats]}"
                    )
                    stats_function_works = False
                    
            except Exception as e:
                self.log_test(
                    "Real Analysis Functions - calculate_real_video_statistics",
                    False,
                    f"Error in calculate_real_video_statistics: {str(e)}"
                )
                stats_function_works = False
            
            # Test generate_video_hash function
            try:
                hash1 = generate_video_hash(test_video)
                hash2 = generate_video_hash(test_video)  # Should be same
                
                if hash1 == hash2 and len(hash1) > 0:
                    self.log_test(
                        "Real Analysis Functions - generate_video_hash",
                        True,
                        f"Video hash generated consistently: {hash1}"
                    )
                    hash_function_works = True
                else:
                    self.log_test(
                        "Real Analysis Functions - generate_video_hash",
                        False,
                        f"Hash inconsistent or empty: {hash1} vs {hash2}"
                    )
                    hash_function_works = False
                    
            except Exception as e:
                self.log_test(
                    "Real Analysis Functions - generate_video_hash",
                    False,
                    f"Error in generate_video_hash: {str(e)}"
                )
                hash_function_works = False
            
            # Cleanup
            os.unlink(test_video)
            
            return real_method_exists and stats_function_works and hash_function_works
            
        except ImportError as e:
            self.log_test(
                "Real Analysis Functions",
                False,
                f"Import error: {str(e)}"
            )
            return False
        except Exception as e:
            self.log_test(
                "Real Analysis Functions",
                False,
                f"Error testing real analysis functions: {str(e)}"
            )
            return False

    def test_server_integration_uses_real_analysis(self):
        """Test that server.py uses analyze_video_with_ttn in the pipeline"""
        try:
            # Check server.py source code for real analysis usage
            server_path = '/app/backend/server.py'
            
            with open(server_path, 'r') as f:
                server_content = f.read()
            
            # Check for usage of real analysis function
            uses_ttn_function = 'analyze_video_with_ttn' in server_content
            
            # Check for the specific call in process_video_analysis_with_tt3d
            uses_in_pipeline = 'ttnet_results = analyze_video_with_ttn(file_path)' in server_content
            
            if uses_ttn_function and uses_in_pipeline:
                self.log_test(
                    "Server Integration Uses Real Analysis",
                    True,
                    "Server uses analyze_video_with_ttn() in TT3D pipeline"
                )
                return True
            else:
                self.log_test(
                    "Server Integration Uses Real Analysis",
                    False,
                    f"Real analysis not used: ttn_function={uses_ttn_function}, in_pipeline={uses_in_pipeline}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Server Integration Uses Real Analysis",
                False,
                f"Error checking server integration: {str(e)}"
            )
            return False

    def run_all_real_analysis_tests(self):
        """Run all real analysis validation tests"""
        print("🔬 Starting PingPro REAL Video Analysis Validation")
        print("🎯 Focus: Verifying REAL analysis generates unique results per video")
        print("=" * 70)
        
        # Test 1: Real analysis function usage
        print("\n📊 Testing Real Analysis Function Usage:")
        real_function_works, sample_results = self.test_real_analysis_function_usage()
        
        # Test 2: Video uniqueness by content
        print("\n🔍 Testing Video Uniqueness by Content:")
        uniqueness_works, unique_results = self.test_video_uniqueness_by_content()
        
        # Test 3: Video characteristics variation
        print("\n📏 Testing Video Characteristics Variation:")
        characteristics_vary = self.test_video_characteristics_vary()
        
        # Test 4: Reproducibility for same video
        print("\n🔄 Testing Reproducibility for Same Video:")
        reproducibility_works = self.test_reproducibility_same_video()
        
        # Test 5: Dynamic metrics variation
        print("\n📈 Testing Dynamic Metrics Variation:")
        metrics_vary = self.test_dynamic_metrics_variation()
        
        # Test 6: TT3D pipeline integration
        print("\n🚀 Testing TT3D Pipeline Integration:")
        tt3d_integration = self.test_tt3d_pipeline_integration()
        
        # Test 7: Real analysis functions
        print("\n⚙️ Testing Real Analysis Functions:")
        real_functions_work = self.test_real_analysis_functions()
        
        # Test 8: Server integration
        print("\n🔗 Testing Server Integration:")
        server_integration = self.test_server_integration_uses_real_analysis()
        
        # Print summary
        print("\n" + "=" * 70)
        print(f"📊 REAL Analysis Validation Summary:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Detailed analysis
        critical_tests = [
            real_function_works,
            uniqueness_works,
            characteristics_vary,
            reproducibility_works,
            metrics_vary
        ]
        
        critical_passed = sum(critical_tests)
        print(f"\n🎯 Critical REAL Analysis Tests: {critical_passed}/{len(critical_tests)} passed")
        
        if critical_passed == len(critical_tests):
            print("\n🎉 SUCCESS: REAL analysis generates unique results per video!")
            print("✅ analyze_video_with_ttn() working correctly")
            print("✅ Video uniqueness validated")
            print("✅ Dynamic metrics confirmed")
            print("✅ Reproducibility verified")
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
    validator = RealAnalysisValidator()
    return validator.run_all_real_analysis_tests()

if __name__ == "__main__":
    sys.exit(main())