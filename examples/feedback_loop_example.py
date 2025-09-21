#!/usr/bin/env python3
"""
Example script demonstrating the Feedback Loop Agent functionality.

This script shows how to:
1. Initialize the Feedback Loop Agent
2. Analyze resolution outcomes and learn from them
3. Calculate performance metrics and trends
4. Conduct A/B tests for system improvements
5. Generate improvement recommendations
6. Update system weights and configuration

Run this script to see the Feedback Loop Agent in action.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import uuid

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.feedback_loop.agent import FeedbackLoopAgent
from agents.feedback_loop.learning import LearningOutcome, PerformanceMetrics, WeightAdjustment
from agents.feedback_loop.metrics import SystemMetrics, ABTestConfig, ABTestResult
from agents.base.agent import AgentContext

async def main():
    """Main example function."""
    print("🔄 Feedback Loop Agent Example")
    print("=" * 50)
    
    # Configuration for the Feedback Loop Agent
    config = {
        "feedback_loop": {
            "learning_rate": 0.1,
            "min_samples": 10,
            "analysis_window_days": 30,
            "enable_ab_testing": True,
            "enable_weight_adjustment": True,
            "confidence_threshold": 0.7,
            "weight_update_frequency": "daily",
            "performance_tracking": True,
            "recommendation_generation": True
        }
    }
    
    # Initialize the Feedback Loop Agent
    print("🔄 Initializing Feedback Loop Agent...")
    feedback_loop = FeedbackLoopAgent(config)
    
    print(f"✅ Agent initialized: {feedback_loop.name}")
    print(f"📊 Learning rate: {feedback_loop.learning_rate}")
    print(f"📈 Analysis window: {feedback_loop.analysis_window_days} days")
    print(f"🧪 A/B testing enabled: {feedback_loop.enable_ab_testing}")
    print(f"⚖️ Weight adjustment enabled: {feedback_loop.enable_weight_adjustment}")
    print()
    
    # Demonstrate learning outcome analysis
    print("📊 Demonstrating learning outcome analysis...")
    
    # Create mock learning outcomes
    mock_outcomes = [
        LearningOutcome(
            feedback_id="1",
            predicted_priority=0.8,
            actual_priority=0.7,
            resolution_time=24.0,
            resolution_quality=0.8,
            user_satisfaction=0.7,
            business_impact=0.6,
            classification_accuracy=0.9,
            clustering_accuracy=0.8,
            outcome_timestamp=datetime.utcnow()
        ),
        LearningOutcome(
            feedback_id="2",
            predicted_priority=0.6,
            actual_priority=0.8,
            resolution_time=48.0,
            resolution_quality=0.6,
            user_satisfaction=0.5,
            business_impact=0.7,
            classification_accuracy=0.8,
            clustering_accuracy=0.7,
            outcome_timestamp=datetime.utcnow()
        ),
        LearningOutcome(
            feedback_id="3",
            predicted_priority=0.9,
            actual_priority=0.85,
            resolution_time=12.0,
            resolution_quality=0.9,
            user_satisfaction=0.8,
            business_impact=0.8,
            classification_accuracy=0.95,
            clustering_accuracy=0.9,
            outcome_timestamp=datetime.utcnow()
        )
    ]
    
    print(f"📈 Analyzed {len(mock_outcomes)} learning outcomes:")
    for i, outcome in enumerate(mock_outcomes, 1):
        print(f"  {i}. Feedback {outcome.feedback_id}:")
        print(f"     • Predicted priority: {outcome.predicted_priority:.2f}")
        print(f"     • Actual priority: {outcome.actual_priority:.2f}")
        print(f"     • Resolution time: {outcome.resolution_time:.1f} hours")
        print(f"     • Resolution quality: {outcome.resolution_quality:.2f}")
        print(f"     • User satisfaction: {outcome.user_satisfaction:.2f}")
        print(f"     • Business impact: {outcome.business_impact:.2f}")
        print(f"     • Classification accuracy: {outcome.classification_accuracy:.2f}")
        print(f"     • Clustering accuracy: {outcome.clustering_accuracy:.2f}")
    print()
    
    # Demonstrate performance metrics calculation
    print("📊 Demonstrating performance metrics calculation...")
    
    # Create mock performance metrics
    mock_metrics = SystemMetrics(
        overall_accuracy=0.75,
        precision=0.8,
        recall=0.7,
        f1_score=0.75,
        classification_accuracy=0.85,
        clustering_accuracy=0.7,
        prioritization_accuracy=0.8,
        resolution_time_improvement=0.6,
        user_satisfaction=0.7,
        business_impact=0.65,
        processing_speed=0.8,
        error_rate=0.95,
        uptime=0.999,
        learning_rate=0.1,
        adaptation_speed=0.6,
        weight_stability=0.8,
        measurement_period=(datetime.utcnow() - timedelta(days=30), datetime.utcnow()),
        last_updated=datetime.utcnow()
    )
    
    print("📈 Performance Metrics:")
    print(f"  🎯 Overall Accuracy: {mock_metrics.overall_accuracy:.3f}")
    print(f"  📊 Precision: {mock_metrics.precision:.3f}")
    print(f"  📊 Recall: {mock_metrics.recall:.3f}")
    print(f"  📊 F1 Score: {mock_metrics.f1_score:.3f}")
    print()
    print(f"  🔧 Classification Accuracy: {mock_metrics.classification_accuracy:.3f}")
    print(f"  🔍 Clustering Accuracy: {mock_metrics.clustering_accuracy:.3f}")
    print(f"  ⚖️ Prioritization Accuracy: {mock_metrics.prioritization_accuracy:.3f}")
    print()
    print(f"  ⏱️ Resolution Time Improvement: {mock_metrics.resolution_time_improvement:.3f}")
    print(f"  😊 User Satisfaction: {mock_metrics.user_satisfaction:.3f}")
    print(f"  💼 Business Impact: {mock_metrics.business_impact:.3f}")
    print()
    print(f"  🚀 Processing Speed: {mock_metrics.processing_speed:.3f}")
    print(f"  ❌ Error Rate: {mock_metrics.error_rate:.3f}")
    print(f"  🔄 Uptime: {mock_metrics.uptime:.3f}")
    print()
    print(f"  🧠 Learning Rate: {mock_metrics.learning_rate:.3f}")
    print(f"  🔄 Adaptation Speed: {mock_metrics.adaptation_speed:.3f}")
    print(f"  ⚖️ Weight Stability: {mock_metrics.weight_stability:.3f}")
    print()
    
    # Demonstrate weight adjustment generation
    print("⚖️ Demonstrating weight adjustment generation...")
    
    # Create mock weight adjustments
    mock_adjustments = [
        WeightAdjustment(
            component="severity",
            old_weight=0.3,
            new_weight=0.35,
            adjustment_reason="Bias correction: 0.1",
            confidence=0.8,
            impact_score=0.5
        ),
        WeightAdjustment(
            component="reach",
            old_weight=0.25,
            new_weight=0.22,
            adjustment_reason="Error reduction: 0.15",
            confidence=0.7,
            impact_score=0.3
        ),
        WeightAdjustment(
            component="recency",
            old_weight=0.2,
            new_weight=0.18,
            adjustment_reason="Bias correction: -0.05",
            confidence=0.6,
            impact_score=0.2
        )
    ]
    
    print(f"⚖️ Generated {len(mock_adjustments)} weight adjustments:")
    for i, adjustment in enumerate(mock_adjustments, 1):
        print(f"  {i}. {adjustment.component}:")
        print(f"     • Old weight: {adjustment.old_weight:.3f}")
        print(f"     • New weight: {adjustment.new_weight:.3f}")
        print(f"     • Change: {adjustment.new_weight - adjustment.old_weight:+.3f}")
        print(f"     • Reason: {adjustment.adjustment_reason}")
        print(f"     • Confidence: {adjustment.confidence:.3f}")
        print(f"     • Impact score: {adjustment.impact_score:.3f}")
    print()
    
    # Demonstrate A/B testing
    print("🧪 Demonstrating A/B testing...")
    
    # Create mock A/B test
    ab_test_config = ABTestConfig(
        test_name="prioritization_algorithm_v2",
        description="Test new prioritization algorithm with improved accuracy",
        control_group="current_algorithm",
        treatment_group="new_algorithm",
        traffic_split=0.5,
        success_metric="accuracy",
        minimum_effect_size=0.05,
        confidence_level=0.95,
        max_duration_days=30
    )
    
    print(f"🧪 A/B Test Configuration:")
    print(f"  • Test name: {ab_test_config.test_name}")
    print(f"  • Description: {ab_test_config.description}")
    print(f"  • Control group: {ab_test_config.control_group}")
    print(f"  • Treatment group: {ab_test_config.treatment_group}")
    print(f"  • Traffic split: {ab_test_config.traffic_split:.1%}")
    print(f"  • Success metric: {ab_test_config.success_metric}")
    print(f"  • Minimum effect size: {ab_test_config.minimum_effect_size:.3f}")
    print(f"  • Confidence level: {ab_test_config.confidence_level:.1%}")
    print(f"  • Max duration: {ab_test_config.max_duration_days} days")
    print()
    
    # Create mock A/B test results
    ab_test_result = ABTestResult(
        test_name="prioritization_algorithm_v2",
        control_metric=0.75,
        treatment_metric=0.82,
        effect_size=0.07,
        confidence_interval=(0.70, 0.90),
        p_value=0.05,
        is_significant=True,
        recommendation="Implement treatment",
        sample_size=1000,
        duration_days=30
    )
    
    print(f"📊 A/B Test Results:")
    print(f"  • Control metric: {ab_test_result.control_metric:.3f}")
    print(f"  • Treatment metric: {ab_test_result.treatment_metric:.3f}")
    print(f"  • Effect size: {ab_test_result.effect_size:.3f}")
    print(f"  • Confidence interval: ({ab_test_result.confidence_interval[0]:.3f}, {ab_test_result.confidence_interval[1]:.3f})")
    print(f"  • P-value: {ab_test_result.p_value:.3f}")
    print(f"  • Significant: {ab_test_result.is_significant}")
    print(f"  • Recommendation: {ab_test_result.recommendation}")
    print(f"  • Sample size: {ab_test_result.sample_size}")
    print(f"  • Duration: {ab_test_result.duration_days} days")
    print()
    
    # Demonstrate improvement recommendations
    print("💡 Demonstrating improvement recommendations...")
    
    # Create mock recommendations
    mock_recommendations = [
        {
            "type": "accuracy_improvement",
            "priority": "high",
            "title": "Improve Overall Accuracy",
            "description": "Current accuracy is 0.750. Consider adjusting classification parameters or increasing training data.",
            "action": "Review classification algorithms and training data quality"
        },
        {
            "type": "classification_improvement",
            "priority": "medium",
            "title": "Improve Classification Accuracy",
            "description": "Classification accuracy is 0.850. Review feedback preprocessing and classification rules.",
            "action": "Update classification templates and rules"
        },
        {
            "type": "clustering_improvement",
            "priority": "medium",
            "title": "Improve Clustering Accuracy",
            "description": "Clustering accuracy is 0.700. Consider adjusting similarity thresholds or embedding models.",
            "action": "Review clustering parameters and similarity calculations"
        },
        {
            "type": "resolution_time_improvement",
            "priority": "high",
            "title": "Improve Resolution Times",
            "description": "Resolution time improvement is 0.600. Focus on faster ticket routing and prioritization.",
            "action": "Optimize ticket routing and escalation procedures"
        },
        {
            "type": "user_satisfaction_improvement",
            "priority": "high",
            "title": "Improve User Satisfaction",
            "description": "User satisfaction is 0.700. Focus on faster responses and better communication.",
            "action": "Implement user satisfaction tracking and feedback collection"
        }
    ]
    
    print(f"💡 Generated {len(mock_recommendations)} improvement recommendations:")
    for i, rec in enumerate(mock_recommendations, 1):
        priority_emoji = {"high": "🚨", "medium": "⚠️", "low": "ℹ️"}.get(rec["priority"], "📋")
        print(f"  {i}. {priority_emoji} {rec['title']} ({rec['priority'].upper()})")
        print(f"     • Description: {rec['description']}")
        print(f"     • Action: {rec['action']}")
    print()
    
    # Demonstrate current weights
    print("⚖️ Current prioritization weights:")
    current_weights = feedback_loop.current_weights
    for component, weight in current_weights.items():
        print(f"  • {component}: {weight:.3f}")
    print()
    
    # Demonstrate weight updates
    print("⚖️ Demonstrating weight updates...")
    
    new_weights = {
        "severity": 0.35,
        "reach": 0.25,
        "recency": 0.2,
        "persona": 0.15,
        "cluster_amplification": 0.05
    }
    
    print("📝 Updating weights:")
    for component, new_weight in new_weights.items():
        old_weight = current_weights[component]
        change = new_weight - old_weight
        print(f"  • {component}: {old_weight:.3f} → {new_weight:.3f} ({change:+.3f})")
    
    # Update weights
    feedback_loop.current_weights.update(new_weights)
    print("✅ Weights updated successfully!")
    print()
    
    # Demonstrate performance trends
    print("📈 Demonstrating performance trends...")
    
    # Create mock performance history
    feedback_loop.performance_history = [
        SystemMetrics(
            overall_accuracy=0.7,
            precision=0.75,
            recall=0.65,
            f1_score=0.7,
            classification_accuracy=0.8,
            clustering_accuracy=0.65,
            prioritization_accuracy=0.75,
            resolution_time_improvement=0.55,
            user_satisfaction=0.65,
            business_impact=0.6,
            processing_speed=0.75,
            error_rate=0.9,
            uptime=0.999,
            learning_rate=0.08,
            adaptation_speed=0.55,
            weight_stability=0.75,
            measurement_period=(datetime.utcnow() - timedelta(days=30), datetime.utcnow() - timedelta(days=15)),
            last_updated=datetime.utcnow() - timedelta(days=15)
        ),
        SystemMetrics(
            overall_accuracy=0.75,
            precision=0.8,
            recall=0.7,
            f1_score=0.75,
            classification_accuracy=0.85,
            clustering_accuracy=0.7,
            prioritization_accuracy=0.8,
            resolution_time_improvement=0.6,
            user_satisfaction=0.7,
            business_impact=0.65,
            processing_speed=0.8,
            error_rate=0.95,
            uptime=0.999,
            learning_rate=0.1,
            adaptation_speed=0.6,
            weight_stability=0.8,
            measurement_period=(datetime.utcnow() - timedelta(days=15), datetime.utcnow()),
            last_updated=datetime.utcnow()
        )
    ]
    
    trends = await feedback_loop.get_performance_trends()
    
    print("📈 Performance Trends (Last 30 days):")
    print(f"  🎯 Accuracy: {trends['accuracy_trend']:+.3f}")
    print(f"  📊 Precision: {trends['precision_trend']:+.3f}")
    print(f"  📊 Recall: {trends['recall_trend']:+.3f}")
    print(f"  📊 F1 Score: {trends['f1_trend']:+.3f}")
    print()
    print(f"  🔧 Classification: {trends['classification_trend']:+.3f}")
    print(f"  🔍 Clustering: {trends['clustering_trend']:+.3f}")
    print(f"  ⚖️ Prioritization: {trends.get('prioritization_trend', 0.0):+.3f}")
    print()
    print(f"  ⏱️ Resolution Time: {trends.get('resolution_time_trend', 0.0):+.3f}")
    print(f"  😊 User Satisfaction: {trends.get('user_satisfaction_trend', 0.0):+.3f}")
    print(f"  💼 Business Impact: {trends.get('business_impact_trend', 0.0):+.3f}")
    print()
    print(f"  🚀 Processing Speed: {trends.get('processing_speed_trend', 0.0):+.3f}")
    print(f"  ❌ Error Rate: {trends.get('error_rate_trend', 0.0):+.3f}")
    print(f"  🧠 Learning Rate: {trends.get('learning_rate_trend', 0.0):+.3f}")
    print(f"  🔄 Adaptation Speed: {trends.get('adaptation_speed_trend', 0.0):+.3f}")
    print(f"  ⚖️ Weight Stability: {trends.get('weight_stability_trend', 0.0):+.3f}")
    print()
    
    # Demonstrate learning engine capabilities
    print("🧠 Demonstrating learning engine capabilities...")
    
    print("📊 Learning Engine Features:")
    print(f"  • Learning rate: {feedback_loop.learning_engine.learning_rate}")
    print(f"  • Minimum samples: {feedback_loop.learning_engine.min_samples}")
    print(f"  • Confidence threshold: {feedback_loop.learning_engine.confidence_threshold}")
    print()
    
    print("📈 Metrics Collector Features:")
    print(f"  • Cache duration: {feedback_loop.metrics_collector.cache_duration}")
    print(f"  • Cache size: {len(feedback_loop.metrics_collector.metrics_cache)}")
    print()
    
    print("🧪 A/B Test Manager Features:")
    print(f"  • Active tests: {len(feedback_loop.ab_test_manager.active_tests)}")
    print(f"  • Test capabilities: Create, analyze, stop tests")
    print()
    
    # Demonstrate configuration options
    print("⚙️ Configuration options:")
    print(f"  📊 Learning:")
    print(f"    • Learning rate: {feedback_loop.learning_rate}")
    print(f"    • Min samples: {feedback_loop.min_samples}")
    print(f"    • Analysis window: {feedback_loop.analysis_window_days} days")
    print()
    
    print(f"  🧪 A/B Testing:")
    print(f"    • Enabled: {feedback_loop.enable_ab_testing}")
    print(f"    • Active tests: {len(feedback_loop.ab_test_manager.active_tests)}")
    print()
    
    print(f"  ⚖️ Weight Adjustment:")
    print(f"    • Enabled: {feedback_loop.enable_weight_adjustment}")
    print(f"    • Current weights: {len(feedback_loop.current_weights)} components")
    print()
    
    # Show input dependencies
    print("🔗 Input dependencies:")
    dependencies = feedback_loop.get_input_dependencies()
    for dep in dependencies:
        print(f"  • {dep}")
    print()
    
    print("✅ Feedback Loop Agent example completed!")
    print()
    print("💡 Key benefits:")
    print("  1. 🧠 Continuous learning from resolution outcomes")
    print("  2. 📊 Comprehensive performance tracking and metrics")
    print("  3. ⚖️ Dynamic weight adjustment based on accuracy")
    print("  4. 🧪 A/B testing for system improvements")
    print("  5. 💡 Intelligent recommendations for optimization")
    print("  6. 📈 Trend analysis and performance monitoring")
    print("  7. 🔄 Adaptive system that improves over time")
    print()
    print("🚀 Next steps:")
    print("  1. Set up the database with resolution outcome data")
    print("  2. Configure learning parameters for your use case")
    print("  3. Enable A/B testing for algorithm improvements")
    print("  4. Monitor performance trends and recommendations")
    print("  5. Implement suggested improvements")
    print("  6. Track system improvement over time")

if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
