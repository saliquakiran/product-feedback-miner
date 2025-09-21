"""
Scoring algorithms and business rules for the Prioritizer Agent.

This module provides various scoring methods, business rules, and
learning mechanisms for prioritizing feedback items.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math
import numpy as np

logger = logging.getLogger(__name__)

class PriorityLevel(str, Enum):
    """Priority levels for feedback items."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"

class UserSegment(str, Enum):
    """User segments for persona scoring."""
    ENTERPRISE = "enterprise"
    PROFESSIONAL = "professional"
    INDIVIDUAL = "individual"
    TRIAL = "trial"
    UNKNOWN = "unknown"

@dataclass
class ScoringWeights:
    """Configuration for scoring weights."""
    severity: float = 0.35
    reach: float = 0.25
    recency: float = 0.20
    persona: float = 0.20
    
    def normalize(self):
        """Normalize weights to sum to 1.0."""
        total = self.severity + self.reach + self.recency + self.persona
        if total > 0:
            self.severity /= total
            self.reach /= total
            self.recency /= total
            self.persona /= total

@dataclass
class BusinessRules:
    """Business rules for priority adjustments."""
    cluster_amplification_factor: float = 0.1
    urgency_boost_factor: float = 1.2
    revenue_critical_boost: float = 1.15
    max_priority_score: float = 1.0
    min_cluster_size_for_amplification: int = 2
    
    # Revenue-critical components
    revenue_critical_components: List[str] = None
    
    def __post_init__(self):
        if self.revenue_critical_components is None:
            self.revenue_critical_components = [
                "authentication", "payment", "api", "database", 
                "security", "core", "checkout", "billing"
            ]

@dataclass
class PriorityScore:
    """Priority score breakdown for a feedback item."""
    overall_score: float
    severity_score: float
    reach_score: float
    recency_score: float
    persona_score: float
    cluster_amplification: float = 1.0
    urgency_boost: float = 1.0
    revenue_boost: float = 1.0
    max_priority_score: float = 1.0
    final_score: float = 0.0
    priority_level: PriorityLevel = PriorityLevel.MINIMAL
    reasoning: List[str] = None
    
    def __post_init__(self):
        if self.reasoning is None:
            self.reasoning = []
        
        # Calculate final score
        self.final_score = min(
            self.overall_score * self.cluster_amplification * self.urgency_boost * self.revenue_boost,
            self.max_priority_score
        )
        
        # Determine priority level
        self.priority_level = self._determine_priority_level()
    
    def _determine_priority_level(self) -> PriorityLevel:
        """Determine priority level based on final score."""
        if self.final_score >= 0.9:
            return PriorityLevel.CRITICAL
        elif self.final_score >= 0.7:
            return PriorityLevel.HIGH
        elif self.final_score >= 0.5:
            return PriorityLevel.MEDIUM
        elif self.final_score >= 0.3:
            return PriorityLevel.LOW
        else:
            return PriorityLevel.MINIMAL

class SeverityScorer:
    """Scores feedback based on severity level."""
    
    SEVERITY_SCORES = {
        "critical": 1.0,
        "high": 0.8,
        "medium": 0.6,
        "low": 0.4,
        "minimal": 0.2
    }
    
    @classmethod
    def score(cls, severity: str) -> float:
        """Calculate severity score."""
        return cls.SEVERITY_SCORES.get(severity.lower(), 0.2)
    
    @classmethod
    def get_severity_boost(cls, feedback_type: str, component: str) -> float:
        """Get additional severity boost based on context."""
        # Security issues get higher priority
        if component == "security":
            return 1.2
        
        # Bug reports get higher priority than feature requests
        if feedback_type == "bug":
            return 1.1
        elif feedback_type == "feature_request":
            return 0.9
        
        return 1.0

class ReachScorer:
    """Scores feedback based on user reach and impact."""
    
    @classmethod
    def score(cls, user_count: int, user_segment: str, component: str) -> float:
        """Calculate reach score based on user metrics."""
        # Base score from user count (logarithmic scale)
        if user_count <= 0:
            base_score = 0.0
        elif user_count == 1:
            base_score = 0.1
        elif user_count <= 10:
            base_score = 0.3
        elif user_count <= 50:
            base_score = 0.5
        elif user_count <= 100:
            base_score = 0.7
        elif user_count <= 500:
            base_score = 0.8
        else:
            base_score = 0.9
        
        # Apply user segment multiplier
        segment_multiplier = cls._get_segment_multiplier(user_segment)
        
        # Apply component multiplier
        component_multiplier = cls._get_component_multiplier(component)
        
        return min(base_score * segment_multiplier * component_multiplier, 1.0)
    
    @classmethod
    def _get_segment_multiplier(cls, user_segment: str) -> float:
        """Get multiplier based on user segment."""
        multipliers = {
            UserSegment.ENTERPRISE: 1.5,
            UserSegment.PROFESSIONAL: 1.2,
            UserSegment.INDIVIDUAL: 1.0,
            UserSegment.TRIAL: 0.8,
            UserSegment.UNKNOWN: 0.9
        }
        return multipliers.get(UserSegment(user_segment), 1.0)
    
    @classmethod
    def _get_component_multiplier(cls, component: str) -> float:
        """Get multiplier based on component criticality."""
        critical_components = ["authentication", "payment", "api", "core"]
        if component in critical_components:
            return 1.3
        return 1.0

class RecencyScorer:
    """Scores feedback based on recency and trend analysis."""
    
    @classmethod
    def score(cls, timestamp: datetime, trend_data: Optional[Dict] = None) -> float:
        """Calculate recency score."""
        now = datetime.utcnow()
        age_hours = (now - timestamp).total_seconds() / 3600
        
        # Exponential decay based on age
        if age_hours <= 1:
            return 1.0
        elif age_hours <= 24:
            return 0.9
        elif age_hours <= 72:
            return 0.7
        elif age_hours <= 168:  # 1 week
            return 0.5
        elif age_hours <= 720:  # 1 month
            return 0.3
        else:
            return 0.1
    
    @classmethod
    def get_trend_boost(cls, trend_data: Optional[Dict]) -> float:
        """Get boost based on trend analysis."""
        if not trend_data:
            return 1.0
        
        # If frequency is increasing, boost the score
        frequency_trend = trend_data.get("frequency_trend", 0)
        if frequency_trend > 0.5:
            return 1.2
        elif frequency_trend > 0.2:
            return 1.1
        else:
            return 1.0

class PersonaScorer:
    """Scores feedback based on user persona and business value."""
    
    @classmethod
    def score(cls, user_segment: str, user_value: Optional[float] = None, 
              feedback_quality: Optional[str] = None) -> float:
        """Calculate persona score."""
        # Base score from user segment
        base_score = cls._get_segment_base_score(user_segment)
        
        # Apply user value multiplier
        value_multiplier = cls._get_value_multiplier(user_value)
        
        # Apply feedback quality multiplier
        quality_multiplier = cls._get_quality_multiplier(feedback_quality)
        
        return min(base_score * value_multiplier * quality_multiplier, 1.0)
    
    @classmethod
    def _get_segment_base_score(cls, user_segment: str) -> float:
        """Get base score for user segment."""
        scores = {
            UserSegment.ENTERPRISE: 0.9,
            UserSegment.PROFESSIONAL: 0.7,
            UserSegment.INDIVIDUAL: 0.5,
            UserSegment.TRIAL: 0.3,
            UserSegment.UNKNOWN: 0.4
        }
        return scores.get(UserSegment(user_segment), 0.4)
    
    @classmethod
    def _get_value_multiplier(cls, user_value: Optional[float]) -> float:
        """Get multiplier based on user value."""
        if user_value is None:
            return 1.0
        
        if user_value >= 10000:  # High-value customer
            return 1.3
        elif user_value >= 1000:
            return 1.2
        elif user_value >= 100:
            return 1.1
        else:
            return 1.0
    
    @classmethod
    def _get_quality_multiplier(cls, feedback_quality: Optional[str]) -> float:
        """Get multiplier based on feedback quality."""
        if not feedback_quality:
            return 1.0
        
        multipliers = {
            "high": 1.2,    # Detailed, actionable feedback
            "medium": 1.0,  # Standard feedback
            "low": 0.8      # Vague, unhelpful feedback
        }
        return multipliers.get(feedback_quality.lower(), 1.0)

class ClusterAmplifier:
    """Amplifies priority scores based on cluster data."""
    
    @classmethod
    def calculate_amplification(cls, cluster_size: int, cluster_quality: float = 1.0,
                               min_size: int = 2) -> float:
        """Calculate cluster amplification factor."""
        if cluster_size < min_size:
            return 1.0
        
        # Base amplification from cluster size
        size_amplification = 1 + (cluster_size - 1) * 0.1
        
        # Apply cluster quality multiplier
        quality_multiplier = min(cluster_quality, 1.0)
        
        return size_amplification * quality_multiplier
    
    @classmethod
    def get_cluster_quality(cls, cluster_data: Dict) -> float:
        """Calculate cluster quality score."""
        if not cluster_data:
            return 0.5
        
        # Factors that improve cluster quality
        factors = []
        
        # Similarity within cluster
        avg_similarity = cluster_data.get("avg_similarity", 0.5)
        factors.append(avg_similarity)
        
        # Temporal clustering (reports close in time)
        temporal_coherence = cluster_data.get("temporal_coherence", 0.5)
        factors.append(temporal_coherence)
        
        # User diversity (different users reporting same issue)
        user_diversity = cluster_data.get("user_diversity", 0.5)
        factors.append(user_diversity)
        
        return np.mean(factors) if factors else 0.5

class UrgencyDetector:
    """Detects urgency indicators in feedback."""
    
    URGENCY_KEYWORDS = [
        "urgent", "critical", "emergency", "asap", "immediately",
        "blocking", "can't work", "broken", "down", "failing",
        "crash", "error", "bug", "issue", "problem"
    ]
    
    URGENCY_PATTERNS = [
        r"can't.*work", r"not.*working", r"broken", r"failing",
        r"urgent.*need", r"critical.*issue", r"emergency.*fix"
    ]
    
    @classmethod
    def detect_urgency(cls, title: str, body: str) -> Tuple[bool, List[str]]:
        """Detect urgency indicators in feedback text."""
        text = f"{title} {body}".lower()
        urgency_indicators = []
        
        # Check for urgency keywords
        for keyword in cls.URGENCY_KEYWORDS:
            if keyword in text:
                urgency_indicators.append(keyword)
        
        # Check for urgency patterns
        import re
        for pattern in cls.URGENCY_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                urgency_indicators.append(f"pattern: {pattern}")
        
        is_urgent = len(urgency_indicators) > 0
        return is_urgent, urgency_indicators
    
    @classmethod
    def get_urgency_boost(cls, urgency_indicators: List[str]) -> float:
        """Calculate urgency boost based on indicators."""
        if not urgency_indicators:
            return 1.0
        
        # More indicators = higher boost
        base_boost = 1.0 + (len(urgency_indicators) * 0.1)
        
        # Specific high-impact keywords get extra boost
        high_impact_keywords = ["critical", "emergency", "blocking", "can't work"]
        high_impact_count = sum(1 for indicator in urgency_indicators 
                               if any(keyword in indicator for keyword in high_impact_keywords))
        
        if high_impact_count > 0:
            base_boost += 0.2
        
        return min(base_boost, 1.5)  # Cap at 50% boost

class BusinessRuleEngine:
    """Applies business rules to priority scores."""
    
    def __init__(self, rules: BusinessRules):
        self.rules = rules
    
    def apply_revenue_boost(self, component: str) -> float:
        """Apply revenue boost for critical components."""
        if component in self.rules.revenue_critical_components:
            return self.rules.revenue_critical_boost
        return 1.0
    
    def apply_cluster_amplification(self, cluster_data: Optional[Dict]) -> float:
        """Apply cluster amplification."""
        if not cluster_data:
            return 1.0
        
        cluster_size = cluster_data.get("size", 1)
        cluster_quality = ClusterAmplifier.get_cluster_quality(cluster_data)
        
        return ClusterAmplifier.calculate_amplification(
            cluster_size, cluster_quality, self.rules.min_cluster_size_for_amplification
        )
    
    def apply_urgency_boost(self, urgency_indicators: List[str]) -> float:
        """Apply urgency boost."""
        if not urgency_indicators:
            return 1.0
        
        return UrgencyDetector.get_urgency_boost(urgency_indicators)
    
    def generate_reasoning(self, score: PriorityScore, feedback_data: Dict) -> List[str]:
        """Generate human-readable reasoning for the priority score."""
        reasoning = []
        
        # Severity reasoning
        if score.severity_score >= 0.8:
            reasoning.append(f"High severity ({feedback_data.get('severity', 'unknown')})")
        
        # Reach reasoning
        user_count = feedback_data.get('user_count', 0)
        if user_count > 50:
            reasoning.append(f"Affects {user_count} users")
        elif user_count > 10:
            reasoning.append(f"Affects {user_count} users")
        
        # Cluster reasoning
        if score.cluster_amplification > 1.1:
            cluster_size = feedback_data.get('cluster_size', 0)
            reasoning.append(f"Multiple reports ({cluster_size} similar issues)")
        
        # Urgency reasoning
        if score.urgency_boost > 1.1:
            reasoning.append("Contains urgency indicators")
        
        # Revenue reasoning
        if score.revenue_boost > 1.1:
            component = feedback_data.get('component', 'unknown')
            reasoning.append(f"Revenue-critical component ({component})")
        
        return reasoning

class PriorityCalculator:
    """Main calculator for priority scores."""
    
    def __init__(self, weights: ScoringWeights, rules: BusinessRules):
        self.weights = weights
        self.rules = rules
        self.rule_engine = BusinessRuleEngine(rules)
    
    def calculate_priority(self, feedback_data: Dict, cluster_data: Optional[Dict] = None) -> PriorityScore:
        """Calculate priority score for a feedback item."""
        try:
            # Calculate base scores
            severity_score = SeverityScorer.score(feedback_data.get('severity', 'low'))
            reach_score = ReachScorer.score(
                feedback_data.get('user_count', 1),
                feedback_data.get('user_segment', 'unknown'),
                feedback_data.get('component', 'other')
            )
            recency_score = RecencyScorer.score(feedback_data.get('timestamp', datetime.utcnow()))
            persona_score = PersonaScorer.score(
                feedback_data.get('user_segment', 'unknown'),
                feedback_data.get('user_value'),
                feedback_data.get('feedback_quality')
            )
            
            # Calculate weighted overall score
            overall_score = (
                severity_score * self.weights.severity +
                reach_score * self.weights.reach +
                recency_score * self.weights.recency +
                persona_score * self.weights.persona
            )
            
            # Apply business rules
            cluster_amplification = self.rule_engine.apply_cluster_amplification(cluster_data)
            urgency_indicators = UrgencyDetector.detect_urgency(
                feedback_data.get('title', ''),
                feedback_data.get('body', '')
            )[1]
            urgency_boost = self.rule_engine.apply_urgency_boost(urgency_indicators)
            revenue_boost = self.rule_engine.apply_revenue_boost(
                feedback_data.get('component', 'other')
            )
            
            # Create priority score object
            priority_score = PriorityScore(
                overall_score=overall_score,
                severity_score=severity_score,
                reach_score=reach_score,
                recency_score=recency_score,
                persona_score=persona_score,
                cluster_amplification=cluster_amplification,
                urgency_boost=urgency_boost,
                revenue_boost=revenue_boost,
                max_priority_score=self.rules.max_priority_score
            )
            
            # Generate reasoning
            priority_score.reasoning = self.rule_engine.generate_reasoning(priority_score, feedback_data)
            
            return priority_score
            
        except Exception as e:
            logger.error(f"Error calculating priority score: {e}")
            # Return minimal priority on error
            return PriorityScore(
                overall_score=0.1,
                severity_score=0.1,
                reach_score=0.1,
                recency_score=0.1,
                persona_score=0.1,
                reasoning=["Error in calculation"]
            )
