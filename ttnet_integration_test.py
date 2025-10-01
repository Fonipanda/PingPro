#!/usr/bin/env python3
"""
TTNet Integration Specific Testing
Tests the enhanced TTNet analysis functions directly
"""

import sys
import os
sys.path.append('/app/backend')

from ttnet_analysis import (
    TTNetAnalyzer, 
    assess_skill_level, 
    assess_video_quality, 
    generate_personalized_recommendations,
    generate_technical_insights,
    calculate_rally_consistency
)
import numpy as np

def test_ttnet_skill_assessment():
    """Test the enhanced skill assessment function"""
    print("🧠 Testing TTNet Skill Assessment...")
    
    # Test case 1: Beginner level indicators
    events_beginner = {'ball_bounce': 5, 'serve': 5, 'net_hit': 3}
    stats_beginner = {'ball_detection_rate': 0.4}
    
    result = assess_skill_level(events_beginner, stats_beginner, 0.4)
    
    print(f"   Beginner test: Level={result['estimated_level']}, Consistency={result['technical_consistency']}")
    print(f"   Full result: {result}")
    assert result['estimated_level'] in ['beginner', 'intermediate', 'advanced'], f"Unexpected skill level: {result['estimated_level']}"
    assert 'evidence_points' in result, "Missing evidence points"
    
    # Test case 2: Advanced level indicators
    events_advanced = {'ball_bounce': 25, 'serve': 5, 'net_hit': 1, 'rally_end': 5}
    stats_advanced = {'ball_detection_rate': 0.85}
    
    result = assess_skill_level(events_advanced, stats_advanced, 0.85)
    
    print(f"   Advanced test: Level={result['estimated_level']}, Consistency={result['technical_consistency']}")
    assert result['technical_consistency'] > 70, "Advanced player should have high consistency"
    
    print("   ✅ Skill assessment working correctly")

def test_video_quality_assessment():
    """Test the enhanced video quality assessment"""
    print("🎥 Testing Video Quality Assessment...")
    
    # Test case 1: High quality video
    frame_analyses_good = [
        {'analysis_quality': 0.9},
        {'analysis_quality': 0.85},
        {'analysis_quality': 0.8}
    ]
    stats_good = {'ball_trajectory_analysis': {'trajectory_smoothness': 10}}
    
    result = assess_video_quality(frame_analyses_good, stats_good)
    
    print(f"   High quality test: Overall={result['overall_quality']}, Lighting={result['lighting_quality']}")
    assert result['overall_quality'] in ['good', 'excellent'], "High quality video not detected"
    
    # Test case 2: Poor quality video
    frame_analyses_poor = [
        {'analysis_quality': 0.3},
        {'analysis_quality': 0.2},
        {'analysis_quality': 0.1}
    ]
    stats_poor = {'ball_trajectory_analysis': {'trajectory_smoothness': 35}}
    
    result = assess_video_quality(frame_analyses_poor, stats_poor)
    
    print(f"   Poor quality test: Overall={result['overall_quality']}, Recommendations={len(result['recommendations'])}")
    assert result['overall_quality'] in ['poor', 'fair'], "Poor quality video not detected"
    assert len(result['recommendations']) > 0, "Should provide recommendations for poor quality"
    
    print("   ✅ Video quality assessment working correctly")

def test_personalized_recommendations():
    """Test the enhanced personalized recommendations"""
    print("🎯 Testing Personalized Recommendations...")
    
    # Test data
    ball_detection_rate = 0.7
    events = {'ball_bounce': 15, 'serve': 5, 'net_hit': 2}
    stats = {'ball_detection_rate': 0.7}
    skill_metrics = {
        'estimated_level': 'intermediate',
        'technical_consistency': 75,
        'tactical_awareness': 70
    }
    video_quality = {
        'recommendations': ['Improve lighting'],
        'overall_quality': 'good'
    }
    
    recommendations = generate_personalized_recommendations(
        ball_detection_rate, events, stats, skill_metrics, video_quality
    )
    
    print(f"   Generated {len(recommendations)} recommendations")
    assert isinstance(recommendations, list), "Recommendations should be a list"
    assert len(recommendations) > 0, "Should generate at least one recommendation"
    
    # Check for skill-level appropriate recommendations
    intermediate_keywords = ['variété', 'tactique', 'améliorer', 'développer']
    has_appropriate_rec = any(
        any(keyword in rec.lower() for keyword in intermediate_keywords)
        for rec in recommendations
    )
    assert has_appropriate_rec, "Should have intermediate-level appropriate recommendations"
    
    print("   ✅ Personalized recommendations working correctly")

def test_technical_insights_generation():
    """Test the enhanced technical insights generation"""
    print("🔬 Testing Technical Insights Generation...")
    
    # Mock analysis results
    analysis_results = {
        'match_statistics': {
            'ball_detection_rate': 0.75,
            'total_frames_analyzed': 100,
            'event_summary': {
                'ball_bounce': 20,
                'serve': 5,
                'net_hit': 2,
                'rally_end': 5
            },
            'ball_trajectory_analysis': {
                'average_speed_pixels_per_frame': 15.5,
                'trajectory_smoothness': 12.3
            }
        },
        'frame_analyses': [
            {'analysis_quality': 0.8, 'ball_position': (100, 200, 0.9)},
            {'analysis_quality': 0.7, 'ball_position': (105, 195, 0.8)},
            {'analysis_quality': 0.75, 'ball_position': None}
        ]
    }
    
    insights = generate_technical_insights(analysis_results)
    
    print(f"   Ball tracking quality: {insights['ball_tracking_quality']}")
    print(f"   Game flow assessment: {insights['game_flow_assessment']}")
    
    # Verify required fields
    required_fields = [
        'ball_tracking_quality',
        'game_flow_assessment', 
        'technical_recommendations',
        'match_characteristics',
        'skill_assessment',
        'video_quality_metrics'
    ]
    
    for field in required_fields:
        assert field in insights, f"Missing required field: {field}"
    
    # Verify realistic assessments
    assert insights['ball_tracking_quality'] in ['Poor', 'Fair', 'Good', 'Excellent'], "Invalid tracking quality"
    assert isinstance(insights['technical_recommendations'], list), "Recommendations should be a list"
    assert len(insights['technical_recommendations']) > 0, "Should have recommendations"
    
    # Check match characteristics
    match_chars = insights['match_characteristics']
    assert 'average_rally_length' in match_chars, "Missing rally length"
    assert match_chars['average_rally_length'] == 4.0, "Rally length calculation incorrect"  # 20 bounces / 5 serves
    
    print("   ✅ Technical insights generation working correctly")

def test_rally_consistency_calculation():
    """Test rally consistency calculation"""
    print("📊 Testing Rally Consistency Calculation...")
    
    # Test with good ball detection
    frame_analyses_good = [
        {'ball_position': (100, 200, 0.9)},
        {'ball_position': (105, 195, 0.8)},
        {'ball_position': (110, 190, 0.85)},
        {'ball_position': None}
    ]
    
    consistency = calculate_rally_consistency(frame_analyses_good)
    expected_consistency = 3/4  # 3 out of 4 frames have ball detection
    
    print(f"   Consistency with good detection: {consistency:.2f}")
    assert abs(consistency - expected_consistency) < 0.01, "Rally consistency calculation incorrect"
    
    # Test with no ball detection
    frame_analyses_none = [
        {'ball_position': None},
        {'ball_position': None}
    ]
    
    consistency = calculate_rally_consistency(frame_analyses_none)
    print(f"   Consistency with no detection: {consistency:.2f}")
    assert consistency == 0.0, "Should be 0 when no balls detected"
    
    print("   ✅ Rally consistency calculation working correctly")

def run_all_ttnet_tests():
    """Run all TTNet specific tests"""
    print("🏓 TTNet Integration Direct Testing")
    print("=" * 50)
    
    try:
        test_ttnet_skill_assessment()
        test_video_quality_assessment()
        test_personalized_recommendations()
        test_technical_insights_generation()
        test_rally_consistency_calculation()
        
        print("\n" + "=" * 50)
        print("🎉 All TTNet integration tests passed!")
        print("✅ Enhanced skill assessment functions working")
        print("✅ Personalized recommendations generation working")
        print("✅ Video quality evaluation working")
        print("✅ Realistic technical insights calculation working")
        return 0
        
    except Exception as e:
        print(f"\n❌ TTNet integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_all_ttnet_tests())