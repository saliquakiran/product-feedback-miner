"""
Performance metrics and A/B testing for the Feedback Loop Agent.

This module provides functionality for measuring system performance,
conducting A/B tests, and tracking improvement over time.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics
import math
from collections import defaultdict, Counter
import json

from database.models import (
    ProcessedDocument, PrioritizationScore, Ticket, Cluster,
    FeedbackType, PriorityLevel, TicketStatus
)
from database import get_session

logger = logging.getLogger(__name__)

@dataclass
class ABTestConfig:
    """Configuration for A/B testing."""
    test_name: str
    description: str
    control_group: str
    treatment_group: str
    traffic_split: float  # 0.0 to 1.0
    success_metric: str
    minimum_effect_size: float
    confidence_level: float
    max_duration_days: int
    is_active: bool = True
    created_at: datetime = None

@dataclass
class ABTestResult:
    """Result of an A/B test."""
    test_name: str
    control_metric: float
    treatment_metric: float
    effect_size: float
    confidence_interval: Tuple[float, float]
    p_value: float
    is_significant: bool
    recommendation: str
    sample_size: int
    duration_days: int

@dataclass
class SystemMetrics:
    """Comprehensive system performance metrics."""
    # Overall performance
    overall_accuracy: float
    precision: float
    recall: float
    f1_score: float
    
    # Component-specific metrics
    classification_accuracy: float
    clustering_accuracy: float
    prioritization_accuracy: float
    
    # Business metrics
    resolution_time_improvement: float
    user_satisfaction: float
    business_impact: float
    
    # System health
    processing_speed: float
    error_rate: float
    uptime: float
    
    # Learning metrics
    learning_rate: float
    adaptation_speed: float
    weight_stability: float
    
    # Timestamps
    measurement_period: Tuple[datetime, datetime]
    last_updated: datetime

class MetricsCollector:
    """Collects and analyzes system performance metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.logger = logging.getLogger(__name__)
        self.metrics_cache = {}
        self.cache_duration = timedelta(hours=1)
    
    def collect_system_metrics(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> SystemMetrics:
        """
        Collect comprehensive system metrics.
        
        Args:
            start_date: Start of measurement period
            end_date: End of measurement period
            
        Returns:
            System metrics
        """
        try:
            # Check cache first
            cache_key = f"{start_date.isoformat()}_{end_date.isoformat()}"
            if cache_key in self.metrics_cache:
                cached_metrics, cached_time = self.metrics_cache[cache_key]
                if datetime.utcnow() - cached_time < self.cache_duration:
                    return cached_metrics
            
            # Collect metrics from database
            with get_session() as session:
                # Get all processed documents in period
                documents = session.query(ProcessedDocument).filter(
                    ProcessedDocument.created_at >= start_date,
                    ProcessedDocument.created_at <= end_date
                ).all()
                
                # Get all prioritization scores
                priority_scores = session.query(PrioritizationScore).join(
                    ProcessedDocument, PrioritizationScore.document_id == ProcessedDocument.id
                ).filter(
                    ProcessedDocument.created_at >= start_date,
                    ProcessedDocument.created_at <= end_date
                ).all()
                
                # Get all tickets
                tickets = session.query(Ticket).filter(
                    Ticket.created_at >= start_date,
                    Ticket.created_at <= end_date
                ).all()
                
                # Get all clusters
                clusters = session.query(Cluster).filter(
                    Cluster.created_at >= start_date,
                    Cluster.created_at <= end_date
                ).all()
                
                # Calculate metrics
                metrics = self._calculate_metrics(
                    documents, priority_scores, tickets, clusters, start_date, end_date
                )
                
                # Cache results
                self.metrics_cache[cache_key] = (metrics, datetime.utcnow())
                
                return metrics
        
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return self._get_default_metrics(start_date, end_date)
    
    def _calculate_metrics(
        self, 
        documents: List[ProcessedDocument],
        priority_scores: List[PrioritizationScore],
        tickets: List[Ticket],
        clusters: List[Cluster],
        start_date: datetime,
        end_date: datetime
    ) -> SystemMetrics:
        """Calculate all system metrics."""
        try:
            # Overall performance metrics
            overall_accuracy = self._calculate_overall_accuracy(documents, priority_scores)
            precision, recall, f1_score = self._calculate_precision_recall_f1(documents, priority_scores)
            
            # Component-specific metrics
            classification_accuracy = self._calculate_classification_accuracy(documents)
            clustering_accuracy = self._calculate_clustering_accuracy(documents, clusters)
            prioritization_accuracy = self._calculate_prioritization_accuracy(priority_scores)
            
            # Business metrics
            resolution_time_improvement = self._calculate_resolution_time_improvement(tickets)
            user_satisfaction = self._calculate_user_satisfaction(tickets)
            business_impact = self._calculate_business_impact(tickets, documents)
            
            # System health metrics
            processing_speed = self._calculate_processing_speed(documents, start_date, end_date)
            error_rate = self._calculate_error_rate(documents)
            uptime = self._calculate_uptime(start_date, end_date)
            
            # Learning metrics
            learning_rate = self._calculate_learning_rate(priority_scores)
            adaptation_speed = self._calculate_adaptation_speed(priority_scores)
            weight_stability = self._calculate_weight_stability(priority_scores)
            
            return SystemMetrics(
                overall_accuracy=overall_accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1_score,
                classification_accuracy=classification_accuracy,
                clustering_accuracy=clustering_accuracy,
                prioritization_accuracy=prioritization_accuracy,
                resolution_time_improvement=resolution_time_improvement,
                user_satisfaction=user_satisfaction,
                business_impact=business_impact,
                processing_speed=processing_speed,
                error_rate=error_rate,
                uptime=uptime,
                learning_rate=learning_rate,
                adaptation_speed=adaptation_speed,
                weight_stability=weight_stability,
                measurement_period=(start_date, end_date),
                last_updated=datetime.utcnow()
            )
        
        except Exception as e:
            self.logger.error(f"Error calculating metrics: {e}")
            return self._get_default_metrics(start_date, end_date)
    
    def _calculate_overall_accuracy(
        self, 
        documents: List[ProcessedDocument], 
        priority_scores: List[PrioritizationScore]
    ) -> float:
        """Calculate overall system accuracy."""
        try:
            if not priority_scores:
                return 0.0
            
            # Simple accuracy based on priority score distribution
            scores = [ps.priority_score for ps in priority_scores]
            avg_score = statistics.mean(scores)
            
            # Normalize to 0-1 scale
            accuracy = min(1.0, max(0.0, avg_score))
            return accuracy
        
        except Exception as e:
            self.logger.error(f"Error calculating overall accuracy: {e}")
            return 0.0
    
    def _calculate_precision_recall_f1(
        self, 
        documents: List[ProcessedDocument], 
        priority_scores: List[PrioritizationScore]
    ) -> Tuple[float, float, float]:
        """Calculate precision, recall, and F1 score."""
        try:
            if not priority_scores:
                return 0.0, 0.0, 0.0
            
            # Define high priority threshold
            threshold = 0.7
            high_priority_count = sum(1 for ps in priority_scores if ps.priority_score >= threshold)
            total_count = len(priority_scores)
            
            # Simple precision/recall calculation
            precision = high_priority_count / total_count if total_count > 0 else 0.0
            recall = precision  # Simplified for this example
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
            
            return precision, recall, f1_score
        
        except Exception as e:
            self.logger.error(f"Error calculating precision/recall: {e}")
            return 0.0, 0.0, 0.0
    
    def _calculate_classification_accuracy(self, documents: List[ProcessedDocument]) -> float:
        """Calculate classification accuracy."""
        try:
            if not documents:
                return 0.0
            
            # Count documents with valid classifications
            classified_count = sum(1 for doc in documents if doc.feedback_type is not None)
            total_count = len(documents)
            
            return classified_count / total_count if total_count > 0 else 0.0
        
        except Exception as e:
            self.logger.error(f"Error calculating classification accuracy: {e}")
            return 0.0
    
    def _calculate_clustering_accuracy(
        self, 
        documents: List[ProcessedDocument], 
        clusters: List[Cluster]
    ) -> float:
        """Calculate clustering accuracy."""
        try:
            if not documents or not clusters:
                return 0.0
            
            # Count documents that are clustered
            clustered_count = sum(1 for doc in documents if doc.cluster_id is not None)
            total_count = len(documents)
            
            # Calculate cluster efficiency
            cluster_efficiency = len(clusters) / total_count if total_count > 0 else 0.0
            
            # Combine clustering rate and efficiency
            accuracy = (clustered_count / total_count) * (1.0 - min(1.0, cluster_efficiency * 0.1))
            
            return min(1.0, max(0.0, accuracy))
        
        except Exception as e:
            self.logger.error(f"Error calculating clustering accuracy: {e}")
            return 0.0
    
    def _calculate_prioritization_accuracy(self, priority_scores: List[PrioritizationScore]) -> float:
        """Calculate prioritization accuracy."""
        try:
            if not priority_scores:
                return 0.0
            
            # Calculate variance in priority scores (lower variance = more consistent)
            scores = [ps.priority_score for ps in priority_scores]
            if len(scores) < 2:
                return 1.0
            
            variance = statistics.variance(scores)
            # Convert variance to accuracy (lower variance = higher accuracy)
            accuracy = max(0.0, 1.0 - (variance * 2))
            
            return min(1.0, accuracy)
        
        except Exception as e:
            self.logger.error(f"Error calculating prioritization accuracy: {e}")
            return 0.0
    
    def _calculate_resolution_time_improvement(self, tickets: List[Ticket]) -> float:
        """Calculate resolution time improvement."""
        try:
            if not tickets:
                return 0.0
            
            # Calculate average resolution time
            resolution_times = []
            for ticket in tickets:
                if ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED] and ticket.updated_at:
                    resolution_time = (ticket.updated_at - ticket.created_at).total_seconds() / 3600
                    resolution_times.append(resolution_time)
            
            if not resolution_times:
                return 0.0
            
            avg_resolution_time = statistics.mean(resolution_times)
            
            # Convert to improvement score (lower time = higher improvement)
            # Assume ideal resolution time is 24 hours
            ideal_time = 24.0
            improvement = max(0.0, 1.0 - (avg_resolution_time / ideal_time))
            
            return min(1.0, improvement)
        
        except Exception as e:
            self.logger.error(f"Error calculating resolution time improvement: {e}")
            return 0.0
    
    def _calculate_user_satisfaction(self, tickets: List[Ticket]) -> float:
        """Calculate user satisfaction score."""
        try:
            if not tickets:
                return 0.0
            
            # Estimate satisfaction based on resolution patterns
            resolved_tickets = [t for t in tickets if t.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]]
            
            if not resolved_tickets:
                return 0.0
            
            satisfaction_scores = []
            for ticket in resolved_tickets:
                # Base satisfaction score
                score = 0.5
                
                # Adjust based on resolution time
                if ticket.updated_at:
                    resolution_time = (ticket.updated_at - ticket.created_at).total_seconds() / 3600
                    if resolution_time < 24:
                        score += 0.3
                    elif resolution_time < 168:
                        score += 0.1
                    else:
                        score -= 0.1
                
                # Adjust based on status
                if ticket.status == TicketStatus.CLOSED:
                    score += 0.2
                
                satisfaction_scores.append(min(1.0, max(0.0, score)))
            
            return statistics.mean(satisfaction_scores)
        
        except Exception as e:
            self.logger.error(f"Error calculating user satisfaction: {e}")
            return 0.0
    
    def _calculate_business_impact(self, tickets: List[Ticket], documents: List[ProcessedDocument]) -> float:
        """Calculate business impact score."""
        try:
            if not tickets:
                return 0.0
            
            # Create document lookup
            doc_lookup = {doc.id: doc for doc in documents}
            
            impact_scores = []
            for ticket in tickets:
                if ticket.source_document_id in doc_lookup:
                    doc = doc_lookup[ticket.source_document_id]
                    
                    # Base impact score
                    score = 0.5
                    
                    # Adjust based on feedback type
                    if doc.feedback_type == FeedbackType.BUG:
                        score += 0.2
                    elif doc.feedback_type == FeedbackType.PERFORMANCE:
                        score += 0.1
                    elif doc.feedback_type == FeedbackType.FEATURE_REQUEST:
                        score -= 0.1
                    
                    # Adjust based on component
                    if hasattr(doc, 'component') and doc.component:
                        if doc.component in ['authentication', 'payment', 'core']:
                            score += 0.1
                    
                    impact_scores.append(min(1.0, max(0.0, score)))
            
            return statistics.mean(impact_scores) if impact_scores else 0.0
        
        except Exception as e:
            self.logger.error(f"Error calculating business impact: {e}")
            return 0.0
    
    def _calculate_processing_speed(
        self, 
        documents: List[ProcessedDocument], 
        start_date: datetime, 
        end_date: datetime
    ) -> float:
        """Calculate processing speed."""
        try:
            if not documents:
                return 0.0
            
            # Calculate documents per hour
            duration_hours = (end_date - start_date).total_seconds() / 3600
            if duration_hours <= 0:
                return 0.0
            
            docs_per_hour = len(documents) / duration_hours
            
            # Normalize to 0-1 scale (assume 100 docs/hour is excellent)
            speed_score = min(1.0, docs_per_hour / 100.0)
            
            return speed_score
        
        except Exception as e:
            self.logger.error(f"Error calculating processing speed: {e}")
            return 0.0
    
    def _calculate_error_rate(self, documents: List[ProcessedDocument]) -> float:
        """Calculate error rate."""
        try:
            if not documents:
                return 0.0
            
            # Count documents with processing errors
            error_count = sum(1 for doc in documents if doc.status == ProcessingStatus.FAILED)
            total_count = len(documents)
            
            error_rate = error_count / total_count if total_count > 0 else 0.0
            
            # Convert to success rate (1 - error_rate)
            return 1.0 - error_rate
        
        except Exception as e:
            self.logger.error(f"Error calculating error rate: {e}")
            return 1.0
    
    def _calculate_uptime(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate system uptime."""
        try:
            # This would typically check system logs for downtime
            # For now, assume 99.9% uptime
            return 0.999
        
        except Exception as e:
            self.logger.error(f"Error calculating uptime: {e}")
            return 0.999
    
    def _calculate_learning_rate(self, priority_scores: List[PrioritizationScore]) -> float:
        """Calculate learning rate."""
        try:
            if len(priority_scores) < 2:
                return 0.0
            
            # Calculate how much priority scores have changed over time
            scores_by_time = sorted(priority_scores, key=lambda x: x.created_at)
            
            if len(scores_by_time) < 2:
                return 0.0
            
            # Calculate variance in scores over time
            early_scores = [ps.priority_score for ps in scores_by_time[:len(scores_by_time)//2]]
            late_scores = [ps.priority_score for ps in scores_by_time[len(scores_by_time)//2:]]
            
            if not early_scores or not late_scores:
                return 0.0
            
            early_avg = statistics.mean(early_scores)
            late_avg = statistics.mean(late_scores)
            
            # Learning rate is the change in average score
            learning_rate = abs(late_avg - early_avg)
            
            return min(1.0, learning_rate)
        
        except Exception as e:
            self.logger.error(f"Error calculating learning rate: {e}")
            return 0.0
    
    def _calculate_adaptation_speed(self, priority_scores: List[PrioritizationScore]) -> float:
        """Calculate adaptation speed."""
        try:
            if len(priority_scores) < 3:
                return 0.0
            
            # Calculate how quickly the system adapts to new patterns
            scores = [ps.priority_score for ps in priority_scores]
            
            # Calculate rolling variance
            window_size = min(10, len(scores) // 3)
            if window_size < 2:
                return 0.0
            
            variances = []
            for i in range(len(scores) - window_size + 1):
                window_scores = scores[i:i + window_size]
                if len(window_scores) > 1:
                    variances.append(statistics.variance(window_scores))
            
            if not variances:
                return 0.0
            
            # Adaptation speed is inverse of variance (more stable = faster adaptation)
            avg_variance = statistics.mean(variances)
            adaptation_speed = max(0.0, 1.0 - (avg_variance * 2))
            
            return min(1.0, adaptation_speed)
        
        except Exception as e:
            self.logger.error(f"Error calculating adaptation speed: {e}")
            return 0.0
    
    def _calculate_weight_stability(self, priority_scores: List[PrioritizationScore]) -> float:
        """Calculate weight stability."""
        try:
            if len(priority_scores) < 2:
                return 1.0
            
            # Calculate how stable priority scores are over time
            scores = [ps.priority_score for ps in priority_scores]
            
            if len(scores) < 2:
                return 1.0
            
            # Calculate coefficient of variation (lower = more stable)
            mean_score = statistics.mean(scores)
            if mean_score == 0:
                return 1.0
            
            std_dev = statistics.stdev(scores) if len(scores) > 1 else 0
            coefficient_of_variation = std_dev / mean_score
            
            # Convert to stability score (lower CV = higher stability)
            stability = max(0.0, 1.0 - coefficient_of_variation)
            
            return min(1.0, stability)
        
        except Exception as e:
            self.logger.error(f"Error calculating weight stability: {e}")
            return 1.0
    
    def _get_default_metrics(self, start_date: datetime, end_date: datetime) -> SystemMetrics:
        """Get default metrics when calculation fails."""
        return SystemMetrics(
            overall_accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            classification_accuracy=0.0,
            clustering_accuracy=0.0,
            prioritization_accuracy=0.0,
            resolution_time_improvement=0.0,
            user_satisfaction=0.0,
            business_impact=0.0,
            processing_speed=0.0,
            error_rate=1.0,
            uptime=0.999,
            learning_rate=0.0,
            adaptation_speed=0.0,
            weight_stability=1.0,
            measurement_period=(start_date, end_date),
            last_updated=datetime.utcnow()
        )

class ABTestManager:
    """Manages A/B testing for system improvements."""
    
    def __init__(self):
        """Initialize A/B test manager."""
        self.logger = logging.getLogger(__name__)
        self.active_tests = {}
    
    def create_ab_test(self, config: ABTestConfig) -> bool:
        """Create a new A/B test."""
        try:
            if config.test_name in self.active_tests:
                self.logger.warning(f"A/B test {config.test_name} already exists")
                return False
            
            config.created_at = datetime.utcnow()
            self.active_tests[config.test_name] = config
            
            self.logger.info(f"Created A/B test: {config.test_name}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error creating A/B test: {e}")
            return False
    
    def get_test_group(self, test_name: str, user_id: str) -> Optional[str]:
        """Get test group for a user."""
        try:
            if test_name not in self.active_tests:
                return None
            
            config = self.active_tests[test_name]
            if not config.is_active:
                return config.control_group
            
            # Simple hash-based assignment
            hash_value = hash(f"{test_name}_{user_id}") % 100
            if hash_value < (config.traffic_split * 100):
                return config.treatment_group
            else:
                return config.control_group
        
        except Exception as e:
            self.logger.error(f"Error getting test group: {e}")
            return None
    
    def analyze_ab_test(self, test_name: str) -> Optional[ABTestResult]:
        """Analyze an A/B test and return results."""
        try:
            if test_name not in self.active_tests:
                return None
            
            config = self.active_tests[test_name]
            
            # Get test data
            with get_session() as session:
                # This would typically query actual test data
                # For now, generate mock results
                control_metric = 0.75
                treatment_metric = 0.82
                
                effect_size = treatment_metric - control_metric
                confidence_interval = (0.70, 0.90)
                p_value = 0.05
                is_significant = p_value < 0.05
                
                sample_size = 1000
                duration_days = (datetime.utcnow() - config.created_at).days
                
                recommendation = "Implement treatment" if is_significant and effect_size > 0 else "Keep control"
                
                result = ABTestResult(
                    test_name=test_name,
                    control_metric=control_metric,
                    treatment_metric=treatment_metric,
                    effect_size=effect_size,
                    confidence_interval=confidence_interval,
                    p_value=p_value,
                    is_significant=is_significant,
                    recommendation=recommendation,
                    sample_size=sample_size,
                    duration_days=duration_days
                )
                
                return result
        
        except Exception as e:
            self.logger.error(f"Error analyzing A/B test: {e}")
            return None
    
    def stop_ab_test(self, test_name: str) -> bool:
        """Stop an A/B test."""
        try:
            if test_name in self.active_tests:
                self.active_tests[test_name].is_active = False
                self.logger.info(f"Stopped A/B test: {test_name}")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error stopping A/B test: {e}")
            return False

