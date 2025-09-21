"""
Feedback Loop Agent for Product Feedback Miner.

This agent learns from resolution outcomes to continuously improve
the system's accuracy, effectiveness, and performance.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
import json

from agents.base.agent import BaseAgent, AgentResult, AgentContext
from agents.feedback_loop.learning import LearningEngine, LearningOutcome, PerformanceMetrics, WeightAdjustment
from agents.feedback_loop.metrics import MetricsCollector, SystemMetrics, ABTestManager, ABTestConfig, ABTestResult
from database.models import (
    ProcessedDocument, PrioritizationScore, Ticket, Cluster,
    FeedbackType, PriorityLevel, TicketStatus, ProcessingStatus
)
from database import get_session

logger = logging.getLogger(__name__)

class FeedbackLoopAgent(BaseAgent):
    """
    Feedback Loop Agent for continuous learning and improvement.
    
    This agent:
    1. Analyzes resolution outcomes and user satisfaction
    2. Learns from prediction accuracy and business impact
    3. Adjusts prioritization weights and algorithms
    4. Conducts A/B tests for system improvements
    5. Tracks performance metrics and trends
    6. Provides recommendations for system optimization
    """
    
    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        """Initialize Feedback Loop Agent."""
        super().__init__("feedback_loop", config_overrides)
        
        # Load configuration
        self.learning_config = self.config.get("feedback_loop", {})
        self.learning_rate = self.learning_config.get("learning_rate", 0.1)
        self.min_samples = self.learning_config.get("min_samples", 10)
        self.analysis_window_days = self.learning_config.get("analysis_window_days", 30)
        self.enable_ab_testing = self.learning_config.get("enable_ab_testing", True)
        self.enable_weight_adjustment = self.learning_config.get("enable_weight_adjustment", True)
        
        # Initialize components
        self.learning_engine = LearningEngine()
        self.metrics_collector = MetricsCollector()
        self.ab_test_manager = ABTestManager()
        
        # Current weights (would be loaded from database in production)
        self.current_weights = {
            "severity": 0.3,
            "reach": 0.25,
            "recency": 0.2,
            "persona": 0.15,
            "cluster_amplification": 0.1
        }
        
        # Performance tracking
        self.performance_history = []
        self.last_analysis_date = None
    
    def get_input_dependencies(self) -> List[str]:
        """Get list of agent dependencies."""
        return ["classifier", "clusterer", "prioritizer", "actioner", "digestor"]
    
    async def process(self, context: AgentContext) -> AgentResult:
        """
        Main processing method for learning and improvement.
        
        Args:
            context: Agent context with execution metadata
            
        Returns:
            AgentResult with processing statistics
        """
        start_time = datetime.utcnow()
        analyses_completed = 0
        improvements_made = 0
        errors = []
        
        try:
            self.logger.info("Starting Feedback Loop Agent processing")
            
            # Determine analysis period
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=self.analysis_window_days)
            
            # 1. Analyze resolution outcomes
            try:
                outcomes = await self._analyze_resolution_outcomes(start_date, end_date)
                analyses_completed += 1
                self.logger.info(f"Analyzed {len(outcomes)} resolution outcomes")
            except Exception as e:
                error_msg = f"Error analyzing resolution outcomes: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                outcomes = []
            
            # 2. Calculate performance metrics
            try:
                performance_metrics = await self._calculate_performance_metrics(start_date, end_date)
                analyses_completed += 1
                self.logger.info(f"Calculated performance metrics: {performance_metrics.overall_accuracy:.3f} accuracy")
            except Exception as e:
                error_msg = f"Error calculating performance metrics: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                performance_metrics = None
            
            # 3. Generate weight adjustments
            if self.enable_weight_adjustment and outcomes:
                try:
                    weight_adjustments = await self._generate_weight_adjustments(outcomes)
                    if weight_adjustments:
                        improvements_made += len(weight_adjustments)
                        self.logger.info(f"Generated {len(weight_adjustments)} weight adjustments")
                except Exception as e:
                    error_msg = f"Error generating weight adjustments: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            # 4. Conduct A/B tests
            if self.enable_ab_testing:
                try:
                    ab_test_results = await self._conduct_ab_tests()
                    analyses_completed += 1
                    self.logger.info(f"Conducted {len(ab_test_results)} A/B tests")
                except Exception as e:
                    error_msg = f"Error conducting A/B tests: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            # 5. Update system configuration
            try:
                config_updates = await self._update_system_configuration(outcomes, performance_metrics)
                if config_updates:
                    improvements_made += len(config_updates)
                    self.logger.info(f"Applied {len(config_updates)} configuration updates")
            except Exception as e:
                error_msg = f"Error updating system configuration: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
            
            # 6. Generate improvement recommendations
            try:
                recommendations = await self._generate_recommendations(outcomes, performance_metrics)
                analyses_completed += 1
                self.logger.info(f"Generated {len(recommendations)} improvement recommendations")
            except Exception as e:
                error_msg = f"Error generating recommendations: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                recommendations = []
            
            # 7. Store learning results
            try:
                await self._store_learning_results(outcomes, performance_metrics, recommendations)
            except Exception as e:
                error_msg = f"Error storing learning results: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.info(
                f"Feedback Loop Agent completed: {analyses_completed} analyses, "
                f"{improvements_made} improvements made"
            )
            
            return AgentResult(
                success=len(errors) == 0,
                items_processed=analyses_completed,
                items_successful=analyses_completed - len(errors),
                items_failed=len(errors),
                execution_time=execution_time,
                error_message="; ".join(errors) if errors else None,
                metadata={
                    "outcomes_analyzed": len(outcomes),
                    "improvements_made": improvements_made,
                    "recommendations_generated": len(recommendations),
                    "performance_accuracy": performance_metrics.overall_accuracy if performance_metrics else 0.0,
                    "learning_rate": self.learning_rate,
                    "analysis_window_days": self.analysis_window_days
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error in Feedback Loop Agent processing: {e}")
            return AgentResult(
                success=False,
                items_processed=analyses_completed,
                items_successful=analyses_completed,
                items_failed=len(errors) + 1,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                error_message=str(e)
            )
    
    async def _analyze_resolution_outcomes(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[LearningOutcome]:
        """Analyze resolution outcomes for learning."""
        try:
            outcomes = self.learning_engine.analyze_outcomes(start_date, end_date)
            
            # Store outcomes for later analysis
            self.last_analysis_date = end_date
            
            return outcomes
        
        except Exception as e:
            self.logger.error(f"Error analyzing resolution outcomes: {e}")
            return []
    
    async def _calculate_performance_metrics(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Optional[SystemMetrics]:
        """Calculate comprehensive performance metrics."""
        try:
            metrics = self.metrics_collector.collect_system_metrics(start_date, end_date)
            
            # Store metrics in history
            self.performance_history.append(metrics)
            
            # Keep only last 30 days of history
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            self.performance_history = [
                m for m in self.performance_history 
                if m.last_updated >= cutoff_date
            ]
            
            return metrics
        
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return None
    
    async def _generate_weight_adjustments(
        self, 
        outcomes: List[LearningOutcome]
    ) -> List[WeightAdjustment]:
        """Generate weight adjustments based on learning outcomes."""
        try:
            if not outcomes:
                return []
            
            adjustments = self.learning_engine.generate_weight_adjustments(
                outcomes, self.current_weights
            )
            
            return adjustments
        
        except Exception as e:
            self.logger.error(f"Error generating weight adjustments: {e}")
            return []
    
    async def _conduct_ab_tests(self) -> List[ABTestResult]:
        """Conduct A/B tests for system improvements."""
        try:
            results = []
            
            # Get active A/B tests
            active_tests = [
                test for test in self.ab_test_manager.active_tests.values()
                if test.is_active
            ]
            
            for test in active_tests:
                # Check if test has run long enough
                if (datetime.utcnow() - test.created_at).days >= test.max_duration_days:
                    # Analyze test results
                    result = self.ab_test_manager.analyze_ab_test(test.test_name)
                    if result:
                        results.append(result)
                        
                        # Stop test if significant result found
                        if result.is_significant:
                            self.ab_test_manager.stop_ab_test(test.test_name)
            
            return results
        
        except Exception as e:
            self.logger.error(f"Error conducting A/B tests: {e}")
            return []
    
    async def _update_system_configuration(
        self, 
        outcomes: List[LearningOutcome], 
        performance_metrics: Optional[SystemMetrics]
    ) -> List[Dict[str, Any]]:
        """Update system configuration based on learning."""
        try:
            updates = []
            
            # Update prioritization weights
            if outcomes:
                weight_adjustments = self.learning_engine.generate_weight_adjustments(
                    outcomes, self.current_weights
                )
                
                for adjustment in weight_adjustments:
                    if adjustment.confidence >= 0.7:  # High confidence threshold
                        old_weight = self.current_weights.get(adjustment.component, 1.0)
                        self.current_weights[adjustment.component] = adjustment.new_weight
                        
                        updates.append({
                            "type": "weight_adjustment",
                            "component": adjustment.component,
                            "old_value": old_weight,
                            "new_value": adjustment.new_weight,
                            "reason": adjustment.adjustment_reason,
                            "confidence": adjustment.confidence
                        })
            
            # Update learning rate based on performance
            if performance_metrics:
                if performance_metrics.overall_accuracy < 0.7:
                    # Increase learning rate if accuracy is low
                    new_learning_rate = min(0.2, self.learning_rate * 1.1)
                    if new_learning_rate != self.learning_rate:
                        self.learning_rate = new_learning_rate
                        updates.append({
                            "type": "learning_rate_adjustment",
                            "old_value": self.learning_rate / 1.1,
                            "new_value": self.learning_rate,
                            "reason": "Low accuracy detected"
                        })
                elif performance_metrics.overall_accuracy > 0.9:
                    # Decrease learning rate if accuracy is high
                    new_learning_rate = max(0.05, self.learning_rate * 0.9)
                    if new_learning_rate != self.learning_rate:
                        self.learning_rate = new_learning_rate
                        updates.append({
                            "type": "learning_rate_adjustment",
                            "old_value": self.learning_rate / 0.9,
                            "new_value": self.learning_rate,
                            "reason": "High accuracy achieved"
                        })
            
            return updates
        
        except Exception as e:
            self.logger.error(f"Error updating system configuration: {e}")
            return []
    
    async def _generate_recommendations(
        self, 
        outcomes: List[LearningOutcome], 
        performance_metrics: Optional[SystemMetrics]
    ) -> List[Dict[str, Any]]:
        """Generate improvement recommendations."""
        try:
            recommendations = []
            
            if not performance_metrics:
                return recommendations
            
            # Accuracy-based recommendations
            if performance_metrics.overall_accuracy < 0.7:
                recommendations.append({
                    "type": "accuracy_improvement",
                    "priority": "high",
                    "title": "Improve Overall Accuracy",
                    "description": f"Current accuracy is {performance_metrics.overall_accuracy:.3f}. Consider adjusting classification parameters or increasing training data.",
                    "action": "Review classification algorithms and training data quality"
                })
            
            # Classification accuracy recommendations
            if performance_metrics.classification_accuracy < 0.8:
                recommendations.append({
                    "type": "classification_improvement",
                    "priority": "medium",
                    "title": "Improve Classification Accuracy",
                    "description": f"Classification accuracy is {performance_metrics.classification_accuracy:.3f}. Review feedback preprocessing and classification rules.",
                    "action": "Update classification templates and rules"
                })
            
            # Clustering accuracy recommendations
            if performance_metrics.clustering_accuracy < 0.7:
                recommendations.append({
                    "type": "clustering_improvement",
                    "priority": "medium",
                    "title": "Improve Clustering Accuracy",
                    "description": f"Clustering accuracy is {performance_metrics.clustering_accuracy:.3f}. Consider adjusting similarity thresholds or embedding models.",
                    "action": "Review clustering parameters and similarity calculations"
                })
            
            # Resolution time recommendations
            if performance_metrics.resolution_time_improvement < 0.6:
                recommendations.append({
                    "type": "resolution_time_improvement",
                    "priority": "high",
                    "title": "Improve Resolution Times",
                    "description": f"Resolution time improvement is {performance_metrics.resolution_time_improvement:.3f}. Focus on faster ticket routing and prioritization.",
                    "action": "Optimize ticket routing and escalation procedures"
                })
            
            # User satisfaction recommendations
            if performance_metrics.user_satisfaction < 0.7:
                recommendations.append({
                    "type": "user_satisfaction_improvement",
                    "priority": "high",
                    "title": "Improve User Satisfaction",
                    "description": f"User satisfaction is {performance_metrics.user_satisfaction:.3f}. Focus on faster responses and better communication.",
                    "action": "Implement user satisfaction tracking and feedback collection"
                })
            
            # Processing speed recommendations
            if performance_metrics.processing_speed < 0.5:
                recommendations.append({
                    "type": "processing_speed_improvement",
                    "priority": "medium",
                    "title": "Improve Processing Speed",
                    "description": f"Processing speed is {performance_metrics.processing_speed:.3f}. Consider optimizing algorithms or increasing resources.",
                    "action": "Review processing algorithms and system resources"
                })
            
            # Learning rate recommendations
            if performance_metrics.learning_rate < 0.1:
                recommendations.append({
                    "type": "learning_rate_improvement",
                    "priority": "low",
                    "title": "Increase Learning Rate",
                    "description": f"Learning rate is {performance_metrics.learning_rate:.3f}. The system may be learning too slowly.",
                    "action": "Increase learning rate or provide more diverse training data"
                })
            
            return recommendations
        
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return []
    
    async def _store_learning_results(
        self, 
        outcomes: List[LearningOutcome], 
        performance_metrics: Optional[SystemMetrics],
        recommendations: List[Dict[str, Any]]
    ):
        """Store learning results in the database."""
        try:
            with self.get_db_session() as session:
                # Store performance metrics
                if performance_metrics:
                    # This would typically store in a dedicated metrics table
                    # For now, just log the metrics
                    self.logger.info(f"Stored performance metrics: accuracy={performance_metrics.overall_accuracy:.3f}")
                
                # Store recommendations
                if recommendations:
                    # This would typically store in a recommendations table
                    # For now, just log the recommendations
                    self.logger.info(f"Stored {len(recommendations)} recommendations")
                
                # Store learning outcomes
                if outcomes:
                    # This would typically store in a learning outcomes table
                    # For now, just log the outcomes
                    self.logger.info(f"Stored {len(outcomes)} learning outcomes")
        
        except Exception as e:
            self.logger.error(f"Error storing learning results: {e}")
    
    async def create_ab_test(
        self, 
        test_name: str, 
        description: str, 
        control_group: str, 
        treatment_group: str,
        traffic_split: float = 0.5,
        success_metric: str = "accuracy",
        minimum_effect_size: float = 0.05,
        confidence_level: float = 0.95,
        max_duration_days: int = 30
    ) -> bool:
        """Create a new A/B test."""
        try:
            config = ABTestConfig(
                test_name=test_name,
                description=description,
                control_group=control_group,
                treatment_group=treatment_group,
                traffic_split=traffic_split,
                success_metric=success_metric,
                minimum_effect_size=minimum_effect_size,
                confidence_level=confidence_level,
                max_duration_days=max_duration_days
            )
            
            return self.ab_test_manager.create_ab_test(config)
        
        except Exception as e:
            self.logger.error(f"Error creating A/B test: {e}")
            return False
    
    async def get_ab_test_results(self, test_name: str) -> Optional[ABTestResult]:
        """Get A/B test results."""
        try:
            return self.ab_test_manager.analyze_ab_test(test_name)
        
        except Exception as e:
            self.logger.error(f"Error getting A/B test results: {e}")
            return None
    
    async def get_performance_metrics(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> Optional[SystemMetrics]:
        """Get performance metrics for a time period."""
        try:
            return self.metrics_collector.collect_system_metrics(start_date, end_date)
        
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {e}")
            return None
    
    async def get_learning_outcomes(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[LearningOutcome]:
        """Get learning outcomes for a time period."""
        try:
            return self.learning_engine.analyze_outcomes(start_date, end_date)
        
        except Exception as e:
            self.logger.error(f"Error getting learning outcomes: {e}")
            return []
    
    async def get_current_weights(self) -> Dict[str, float]:
        """Get current prioritization weights."""
        return self.current_weights.copy()
    
    async def update_weights(self, new_weights: Dict[str, float]) -> bool:
        """Update prioritization weights."""
        try:
            # Validate weights
            for component, weight in new_weights.items():
                if not isinstance(weight, (int, float)) or weight < 0 or weight > 2:
                    self.logger.error(f"Invalid weight for {component}: {weight}")
                    return False
            
            # Update weights
            self.current_weights.update(new_weights)
            
            self.logger.info(f"Updated weights: {new_weights}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error updating weights: {e}")
            return False
    
    async def get_improvement_recommendations(self) -> List[Dict[str, Any]]:
        """Get current improvement recommendations."""
        try:
            # Get recent performance metrics
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
            
            performance_metrics = await self.get_performance_metrics(start_date, end_date)
            outcomes = await self.get_learning_outcomes(start_date, end_date)
            
            return await self._generate_recommendations(outcomes, performance_metrics)
        
        except Exception as e:
            self.logger.error(f"Error getting improvement recommendations: {e}")
            return []
    
    async def get_performance_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get performance trends over time."""
        try:
            if len(self.performance_history) < 2:
                return {"trends": "Insufficient data for trend analysis"}
            
            # Calculate trends for key metrics
            recent_metrics = self.performance_history[-1]
            older_metrics = self.performance_history[0] if len(self.performance_history) > 1 else recent_metrics
            
            trends = {
                "accuracy_trend": recent_metrics.overall_accuracy - older_metrics.overall_accuracy,
                "precision_trend": recent_metrics.precision - older_metrics.precision,
                "recall_trend": recent_metrics.recall - older_metrics.recall,
                "f1_trend": recent_metrics.f1_score - older_metrics.f1_score,
                "classification_trend": recent_metrics.classification_accuracy - older_metrics.classification_accuracy,
                "clustering_trend": recent_metrics.clustering_accuracy - older_metrics.clustering_accuracy,
                "resolution_time_trend": recent_metrics.resolution_time_improvement - older_metrics.resolution_time_improvement,
                "user_satisfaction_trend": recent_metrics.user_satisfaction - older_metrics.user_satisfaction,
                "business_impact_trend": recent_metrics.business_impact - older_metrics.business_impact,
                "processing_speed_trend": recent_metrics.processing_speed - older_metrics.processing_speed,
                "error_rate_trend": recent_metrics.error_rate - older_metrics.error_rate,
                "learning_rate_trend": recent_metrics.learning_rate - older_metrics.learning_rate,
                "adaptation_speed_trend": recent_metrics.adaptation_speed - older_metrics.adaptation_speed,
                "weight_stability_trend": recent_metrics.weight_stability - older_metrics.weight_stability
            }
            
            return trends
        
        except Exception as e:
            self.logger.error(f"Error getting performance trends: {e}")
            return {"error": str(e)}

