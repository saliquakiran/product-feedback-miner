"""
Learning engine for the Feedback Loop Agent.

This module provides functionality for learning from resolution outcomes,
adjusting weights, and improving system performance over time.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics
import math
from collections import defaultdict, Counter

from database.models import (
    ProcessedDocument, PrioritizationScore, Ticket, Cluster,
    FeedbackType, PriorityLevel, TicketStatus
)
from database import get_session

logger = logging.getLogger(__name__)

@dataclass
class LearningOutcome:
    """Data structure for learning outcomes."""
    feedback_id: str
    predicted_priority: float
    actual_priority: float
    resolution_time: Optional[float]  # Hours to resolve
    resolution_quality: float  # 0-1 scale
    user_satisfaction: Optional[float]  # 0-1 scale
    business_impact: float  # 0-1 scale
    classification_accuracy: float  # 0-1 scale
    clustering_accuracy: float  # 0-1 scale
    outcome_timestamp: datetime

@dataclass
class PerformanceMetrics:
    """Performance metrics for the system."""
    accuracy_score: float
    precision_score: float
    recall_score: float
    f1_score: float
    mean_absolute_error: float
    root_mean_square_error: float
    resolution_time_accuracy: float
    user_satisfaction_score: float
    business_impact_score: float
    total_predictions: int
    successful_predictions: int

@dataclass
class WeightAdjustment:
    """Weight adjustment for prioritization scoring."""
    component: str
    old_weight: float
    new_weight: float
    adjustment_reason: str
    confidence: float
    impact_score: float

class LearningEngine:
    """Engine for learning from feedback outcomes and improving the system."""
    
    def __init__(self):
        """Initialize learning engine."""
        self.logger = logging.getLogger(__name__)
        self.learning_rate = 0.1  # How quickly to adapt
        self.min_samples = 10  # Minimum samples for learning
        self.confidence_threshold = 0.7  # Minimum confidence for adjustments
    
    def analyze_outcomes(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[LearningOutcome]:
        """
        Analyze resolution outcomes for learning.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            List of learning outcomes
        """
        try:
            outcomes = []
            
            with get_session() as session:
                # Get resolved tickets with their feedback
                resolved_tickets = session.query(Ticket).join(
                    ProcessedDocument, Ticket.source_document_id == ProcessedDocument.id
                ).join(
                    PrioritizationScore, ProcessedDocument.id == PrioritizationScore.document_id
                ).filter(
                    Ticket.created_at >= start_date,
                    Ticket.created_at <= end_date,
                    Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED])
                ).all()
                
                for ticket in resolved_tickets:
                    try:
                        # Get the associated feedback and priority score
                        feedback = session.query(ProcessedDocument).filter(
                            ProcessedDocument.id == ticket.source_document_id
                        ).first()
                        
                        priority_score = session.query(PrioritizationScore).filter(
                            PrioritizationScore.document_id == ticket.source_document_id
                        ).first()
                        
                        if not feedback or not priority_score:
                            continue
                        
                        # Calculate actual priority based on resolution time and impact
                        actual_priority = self._calculate_actual_priority(ticket, feedback)
                        
                        # Calculate resolution time
                        resolution_time = self._calculate_resolution_time(ticket)
                        
                        # Calculate resolution quality
                        resolution_quality = self._calculate_resolution_quality(ticket, feedback)
                        
                        # Calculate user satisfaction (placeholder - would come from surveys)
                        user_satisfaction = self._estimate_user_satisfaction(ticket, feedback)
                        
                        # Calculate business impact
                        business_impact = self._calculate_business_impact(ticket, feedback)
                        
                        # Calculate classification accuracy
                        classification_accuracy = self._calculate_classification_accuracy(feedback)
                        
                        # Calculate clustering accuracy
                        clustering_accuracy = self._calculate_clustering_accuracy(feedback, session)
                        
                        outcome = LearningOutcome(
                            feedback_id=str(feedback.id),
                            predicted_priority=priority_score.priority_score,
                            actual_priority=actual_priority,
                            resolution_time=resolution_time,
                            resolution_quality=resolution_quality,
                            user_satisfaction=user_satisfaction,
                            business_impact=business_impact,
                            classification_accuracy=classification_accuracy,
                            clustering_accuracy=clustering_accuracy,
                            outcome_timestamp=ticket.updated_at or ticket.created_at
                        )
                        
                        outcomes.append(outcome)
                    
                    except Exception as e:
                        self.logger.error(f"Error processing ticket {ticket.id}: {e}")
                        continue
            
            self.logger.info(f"Analyzed {len(outcomes)} outcomes for learning")
            return outcomes
        
        except Exception as e:
            self.logger.error(f"Error analyzing outcomes: {e}")
            return []
    
    def calculate_performance_metrics(
        self, 
        outcomes: List[LearningOutcome]
    ) -> PerformanceMetrics:
        """
        Calculate performance metrics from learning outcomes.
        
        Args:
            outcomes: List of learning outcomes
            
        Returns:
            Performance metrics
        """
        try:
            if not outcomes:
                return PerformanceMetrics(
                    accuracy_score=0.0, precision_score=0.0, recall_score=0.0,
                    f1_score=0.0, mean_absolute_error=0.0, root_mean_square_error=0.0,
                    resolution_time_accuracy=0.0, user_satisfaction_score=0.0,
                    business_impact_score=0.0, total_predictions=0, successful_predictions=0
                )
            
            # Calculate prediction accuracy
            predicted = [o.predicted_priority for o in outcomes]
            actual = [o.actual_priority for o in outcomes]
            
            # Mean Absolute Error
            mae = sum(abs(p - a) for p, a in zip(predicted, actual)) / len(outcomes)
            
            # Root Mean Square Error
            rmse = math.sqrt(sum((p - a) ** 2 for p, a in zip(predicted, actual)) / len(outcomes))
            
            # Accuracy score (1 - normalized MAE)
            accuracy_score = max(0, 1 - (mae / 1.0))  # Normalize by max possible error
            
            # Precision and Recall (simplified for priority prediction)
            threshold = 0.7
            true_positives = sum(1 for p, a in zip(predicted, actual) 
                               if p >= threshold and a >= threshold)
            false_positives = sum(1 for p, a in zip(predicted, actual) 
                                if p >= threshold and a < threshold)
            false_negatives = sum(1 for p, a in zip(predicted, actual) 
                                if p < threshold and a >= threshold)
            
            precision_score = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall_score = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
            f1_score = 2 * (precision_score * recall_score) / (precision_score + recall_score) if (precision_score + recall_score) > 0 else 0
            
            # Resolution time accuracy
            resolution_times = [o.resolution_time for o in outcomes if o.resolution_time is not None]
            resolution_time_accuracy = self._calculate_resolution_time_accuracy(resolution_times)
            
            # User satisfaction score
            satisfaction_scores = [o.user_satisfaction for o in outcomes if o.user_satisfaction is not None]
            user_satisfaction_score = statistics.mean(satisfaction_scores) if satisfaction_scores else 0.0
            
            # Business impact score
            business_impacts = [o.business_impact for o in outcomes]
            business_impact_score = statistics.mean(business_impacts) if business_impacts else 0.0
            
            # Classification and clustering accuracy
            classification_scores = [o.classification_accuracy for o in outcomes]
            clustering_scores = [o.clustering_accuracy for o in outcomes]
            
            avg_classification_accuracy = statistics.mean(classification_scores) if classification_scores else 0.0
            avg_clustering_accuracy = statistics.mean(clustering_scores) if clustering_scores else 0.0
            
            # Overall accuracy (weighted average)
            overall_accuracy = (
                accuracy_score * 0.3 +
                avg_classification_accuracy * 0.2 +
                avg_clustering_accuracy * 0.2 +
                resolution_time_accuracy * 0.15 +
                user_satisfaction_score * 0.1 +
                business_impact_score * 0.05
            )
            
            return PerformanceMetrics(
                accuracy_score=overall_accuracy,
                precision_score=precision_score,
                recall_score=recall_score,
                f1_score=f1_score,
                mean_absolute_error=mae,
                root_mean_square_error=rmse,
                resolution_time_accuracy=resolution_time_accuracy,
                user_satisfaction_score=user_satisfaction_score,
                business_impact_score=business_impact_score,
                total_predictions=len(outcomes),
                successful_predictions=sum(1 for o in outcomes if abs(o.predicted_priority - o.actual_priority) < 0.2)
            )
        
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return PerformanceMetrics(
                accuracy_score=0.0, precision_score=0.0, recall_score=0.0,
                f1_score=0.0, mean_absolute_error=0.0, root_mean_square_error=0.0,
                resolution_time_accuracy=0.0, user_satisfaction_score=0.0,
                business_impact_score=0.0, total_predictions=0, successful_predictions=0
            )
    
    def generate_weight_adjustments(
        self, 
        outcomes: List[LearningOutcome],
        current_weights: Dict[str, float]
    ) -> List[WeightAdjustment]:
        """
        Generate weight adjustments based on learning outcomes.
        
        Args:
            outcomes: List of learning outcomes
            current_weights: Current prioritization weights
            
        Returns:
            List of weight adjustments
        """
        try:
            adjustments = []
            
            if len(outcomes) < self.min_samples:
                self.logger.warning(f"Not enough samples for learning: {len(outcomes)} < {self.min_samples}")
                return adjustments
            
            # Analyze outcomes by component
            component_outcomes = defaultdict(list)
            for outcome in outcomes:
                # Get component from feedback (would need to join with ProcessedDocument)
                component = "general"  # Placeholder - would get from actual data
                component_outcomes[component].append(outcome)
            
            # Analyze each component
            for component, comp_outcomes in component_outcomes.items():
                if len(comp_outcomes) < 5:  # Need minimum samples per component
                    continue
                
                # Calculate component-specific metrics
                predicted_priorities = [o.predicted_priority for o in comp_outcomes]
                actual_priorities = [o.actual_priority for o in comp_outcomes]
                
                # Calculate error patterns
                errors = [abs(p - a) for p, a in zip(predicted_priorities, actual_priorities)]
                avg_error = statistics.mean(errors)
                
                # Calculate bias (systematic over/under prediction)
                bias = statistics.mean([p - a for p, a in zip(predicted_priorities, actual_priorities)])
                
                # Calculate confidence in adjustment
                confidence = min(1.0, len(comp_outcomes) / 20.0)  # More samples = higher confidence
                
                if confidence < self.confidence_threshold:
                    continue
                
                # Determine adjustment
                current_weight = current_weights.get(component, 1.0)
                
                if abs(bias) > 0.1:  # Significant bias detected
                    # Adjust weight based on bias direction
                    adjustment_factor = 1.0 + (bias * self.learning_rate)
                    new_weight = max(0.1, min(2.0, current_weight * adjustment_factor))
                    
                    if abs(new_weight - current_weight) > 0.05:  # Only adjust if significant change
                        adjustment = WeightAdjustment(
                            component=component,
                            old_weight=current_weight,
                            new_weight=new_weight,
                            adjustment_reason=f"Bias correction: {bias:.3f}",
                            confidence=confidence,
                            impact_score=abs(bias) * avg_error
                        )
                        adjustments.append(adjustment)
                
                # Adjust based on error magnitude
                if avg_error > 0.3:  # High error
                    error_adjustment = 1.0 - (avg_error * self.learning_rate * 0.5)
                    new_weight = max(0.1, min(2.0, current_weight * error_adjustment))
                    
                    if abs(new_weight - current_weight) > 0.05:
                        adjustment = WeightAdjustment(
                            component=component,
                            old_weight=current_weight,
                            new_weight=new_weight,
                            adjustment_reason=f"Error reduction: {avg_error:.3f}",
                            confidence=confidence,
                            impact_score=avg_error
                        )
                        adjustments.append(adjustment)
            
            # Sort by impact score
            adjustments.sort(key=lambda x: x.impact_score, reverse=True)
            
            self.logger.info(f"Generated {len(adjustments)} weight adjustments")
            return adjustments
        
        except Exception as e:
            self.logger.error(f"Error generating weight adjustments: {e}")
            return []
    
    def apply_weight_adjustments(
        self, 
        adjustments: List[WeightAdjustment]
    ) -> Dict[str, float]:
        """
        Apply weight adjustments to the system.
        
        Args:
            adjustments: List of weight adjustments to apply
            
        Returns:
            Updated weights dictionary
        """
        try:
            updated_weights = {}
            
            for adjustment in adjustments:
                if adjustment.confidence >= self.confidence_threshold:
                    updated_weights[adjustment.component] = adjustment.new_weight
                    self.logger.info(
                        f"Applied weight adjustment for {adjustment.component}: "
                        f"{adjustment.old_weight:.3f} -> {adjustment.new_weight:.3f} "
                        f"(reason: {adjustment.adjustment_reason})"
                    )
            
            return updated_weights
        
        except Exception as e:
            self.logger.error(f"Error applying weight adjustments: {e}")
            return {}
    
    def _calculate_actual_priority(self, ticket: Ticket, feedback: ProcessedDocument) -> float:
        """Calculate actual priority based on resolution outcome."""
        try:
            # Base priority from resolution time
            resolution_time = self._calculate_resolution_time(ticket)
            if resolution_time is None:
                return 0.5  # Default if no resolution time
            
            # Faster resolution = higher actual priority (more urgent)
            if resolution_time < 1:  # Resolved in < 1 hour
                time_priority = 0.9
            elif resolution_time < 24:  # Resolved in < 1 day
                time_priority = 0.7
            elif resolution_time < 168:  # Resolved in < 1 week
                time_priority = 0.5
            else:
                time_priority = 0.3
            
            # Adjust based on ticket status
            status_multiplier = 1.0
            if ticket.status == TicketStatus.CLOSED:
                status_multiplier = 1.0
            elif ticket.status == TicketStatus.RESOLVED:
                status_multiplier = 0.9
            else:
                status_multiplier = 0.7
            
            # Adjust based on feedback type
            type_multiplier = 1.0
            if feedback.feedback_type == FeedbackType.BUG:
                type_multiplier = 1.2
            elif feedback.feedback_type == FeedbackType.FEATURE_REQUEST:
                type_multiplier = 0.8
            elif feedback.feedback_type == FeedbackType.PERFORMANCE:
                type_multiplier = 1.1
            
            actual_priority = time_priority * status_multiplier * type_multiplier
            return min(1.0, max(0.0, actual_priority))
        
        except Exception as e:
            self.logger.error(f"Error calculating actual priority: {e}")
            return 0.5
    
    def _calculate_resolution_time(self, ticket: Ticket) -> Optional[float]:
        """Calculate resolution time in hours."""
        try:
            if not ticket.updated_at:
                return None
            
            # Calculate time difference
            if ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
                resolution_time = (ticket.updated_at - ticket.created_at).total_seconds() / 3600
                return resolution_time
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error calculating resolution time: {e}")
            return None
    
    def _calculate_resolution_quality(self, ticket: Ticket, feedback: ProcessedDocument) -> float:
        """Calculate resolution quality score."""
        try:
            quality_score = 0.5  # Base score
            
            # Adjust based on ticket status
            if ticket.status == TicketStatus.CLOSED:
                quality_score += 0.3
            elif ticket.status == TicketStatus.RESOLVED:
                quality_score += 0.2
            
            # Adjust based on resolution time
            resolution_time = self._calculate_resolution_time(ticket)
            if resolution_time is not None:
                if resolution_time < 24:  # Resolved quickly
                    quality_score += 0.2
                elif resolution_time > 168:  # Took too long
                    quality_score -= 0.1
            
            # Adjust based on feedback type
            if feedback.feedback_type == FeedbackType.BUG:
                # Bugs should be resolved quickly
                if resolution_time and resolution_time < 48:
                    quality_score += 0.1
                elif resolution_time and resolution_time > 168:
                    quality_score -= 0.1
            
            return min(1.0, max(0.0, quality_score))
        
        except Exception as e:
            self.logger.error(f"Error calculating resolution quality: {e}")
            return 0.5
    
    def _estimate_user_satisfaction(self, ticket: Ticket, feedback: ProcessedDocument) -> Optional[float]:
        """Estimate user satisfaction (placeholder for survey data)."""
        try:
            # This would typically come from user surveys or feedback
            # For now, estimate based on resolution time and quality
            
            resolution_time = self._calculate_resolution_time(ticket)
            if resolution_time is None:
                return None
            
            # Faster resolution = higher satisfaction
            if resolution_time < 24:
                satisfaction = 0.8
            elif resolution_time < 168:
                satisfaction = 0.6
            else:
                satisfaction = 0.4
            
            # Adjust based on ticket status
            if ticket.status == TicketStatus.CLOSED:
                satisfaction += 0.1
            elif ticket.status == TicketStatus.RESOLVED:
                satisfaction += 0.05
            
            return min(1.0, max(0.0, satisfaction))
        
        except Exception as e:
            self.logger.error(f"Error estimating user satisfaction: {e}")
            return None
    
    def _calculate_business_impact(self, ticket: Ticket, feedback: ProcessedDocument) -> float:
        """Calculate business impact score."""
        try:
            impact_score = 0.5  # Base score
            
            # Adjust based on feedback type
            if feedback.feedback_type == FeedbackType.BUG:
                impact_score += 0.2  # Bugs have high business impact
            elif feedback.feedback_type == FeedbackType.PERFORMANCE:
                impact_score += 0.1  # Performance issues have medium impact
            elif feedback.feedback_type == FeedbackType.FEATURE_REQUEST:
                impact_score -= 0.1  # Feature requests have lower immediate impact
            
            # Adjust based on resolution time
            resolution_time = self._calculate_resolution_time(ticket)
            if resolution_time is not None:
                if resolution_time < 24:  # Quick resolution reduces impact
                    impact_score -= 0.1
                elif resolution_time > 168:  # Slow resolution increases impact
                    impact_score += 0.1
            
            # Adjust based on component (if available)
            if hasattr(feedback, 'component') and feedback.component:
                if feedback.component in ['authentication', 'payment', 'core']:
                    impact_score += 0.1  # Critical components
                elif feedback.component in ['ui', 'ux']:
                    impact_score -= 0.05  # Less critical components
            
            return min(1.0, max(0.0, impact_score))
        
        except Exception as e:
            self.logger.error(f"Error calculating business impact: {e}")
            return 0.5
    
    def _calculate_classification_accuracy(self, feedback: ProcessedDocument) -> float:
        """Calculate classification accuracy for this feedback."""
        try:
            # This would typically compare predicted vs actual classification
            # For now, return a placeholder based on feedback quality
            
            if not feedback.feedback_type:
                return 0.0  # No classification
            
            # Simple heuristic: longer, more detailed feedback = better classification
            content_length = len(feedback.content or "")
            if content_length > 200:
                return 0.8
            elif content_length > 100:
                return 0.6
            else:
                return 0.4
        
        except Exception as e:
            self.logger.error(f"Error calculating classification accuracy: {e}")
            return 0.5
    
    def _calculate_clustering_accuracy(self, feedback: ProcessedDocument, session) -> float:
        """Calculate clustering accuracy for this feedback."""
        try:
            if not feedback.cluster_id:
                return 0.0  # Not clustered
            
            # Get cluster information
            cluster = session.query(Cluster).filter(Cluster.id == feedback.cluster_id).first()
            if not cluster:
                return 0.0
            
            # Simple heuristic: larger clusters with similar content = better clustering
            cluster_size = cluster.member_count or 1
            if cluster_size > 5:
                return 0.8
            elif cluster_size > 2:
                return 0.6
            else:
                return 0.4
        
        except Exception as e:
            self.logger.error(f"Error calculating clustering accuracy: {e}")
            return 0.5
    
    def _calculate_resolution_time_accuracy(self, resolution_times: List[float]) -> float:
        """Calculate how well resolution times match expectations."""
        try:
            if not resolution_times:
                return 0.0
            
            # Define expected resolution times (in hours)
            expected_times = {
                'critical': 4,    # 4 hours
                'high': 24,       # 1 day
                'medium': 168,    # 1 week
                'low': 720        # 1 month
            }
            
            # Calculate accuracy based on how close actual times are to expected
            accuracy_scores = []
            for time in resolution_times:
                if time <= expected_times['critical']:
                    accuracy_scores.append(1.0)
                elif time <= expected_times['high']:
                    accuracy_scores.append(0.8)
                elif time <= expected_times['medium']:
                    accuracy_scores.append(0.6)
                elif time <= expected_times['low']:
                    accuracy_scores.append(0.4)
                else:
                    accuracy_scores.append(0.2)
            
            return statistics.mean(accuracy_scores) if accuracy_scores else 0.0
        
        except Exception as e:
            self.logger.error(f"Error calculating resolution time accuracy: {e}")
            return 0.0

