"""
Classification models and data structures for the Classifier Agent.

This module defines the data structures and models used for feedback classification,
including feedback types, severity levels, and classification results.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import json
from datetime import datetime

class FeedbackType(str, Enum):
    """Types of feedback that can be classified."""
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    UX = "ux"
    PRICING = "pricing"
    DOCS = "docs"
    PERFORMANCE = "performance"
    SECURITY = "security"
    INTEGRATION = "integration"
    OTHER = "other"

class SeverityLevel(str, Enum):
    """Severity levels for feedback classification."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"

class ComponentType(str, Enum):
    """Common product components for classification."""
    AUTHENTICATION = "authentication"
    UI = "ui"
    API = "api"
    DATABASE = "database"
    PAYMENT = "payment"
    NOTIFICATIONS = "notifications"
    SEARCH = "search"
    DASHBOARD = "dashboard"
    SETTINGS = "settings"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    INTEGRATION = "integration"
    SECURITY = "security"
    PERFORMANCE = "performance"
    OTHER = "other"

@dataclass
class ClassificationResult:
    """Result of feedback classification."""
    
    # Document association
    document_id: str
    
    # Primary classification
    feedback_type: FeedbackType
    severity_level: SeverityLevel
    component: ComponentType
    
    # Confidence scores (0-1)
    type_confidence: float
    severity_confidence: float
    component_confidence: float
    overall_confidence: float
    
    # Additional metadata
    version: Optional[str] = None
    keywords: List[str] = None
    sentiment: Optional[str] = None  # positive, negative, neutral
    urgency_indicators: List[str] = None
    
    # Classification metadata
    classification_timestamp: datetime = None
    model_version: str = "1.0"
    processing_time_ms: Optional[float] = None
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.keywords is None:
            self.keywords = []
        if self.urgency_indicators is None:
            self.urgency_indicators = []
        if self.classification_timestamp is None:
            self.classification_timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'feedback_type': self.feedback_type.value,
            'severity_level': self.severity_level.value,
            'component': self.component.value,
            'type_confidence': self.type_confidence,
            'severity_confidence': self.severity_confidence,
            'component_confidence': self.component_confidence,
            'overall_confidence': self.overall_confidence,
            'version': self.version,
            'keywords': self.keywords,
            'sentiment': self.sentiment,
            'urgency_indicators': self.urgency_indicators,
            'classification_timestamp': self.classification_timestamp.isoformat(),
            'model_version': self.model_version,
            'processing_time_ms': self.processing_time_ms
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClassificationResult':
        """Create from dictionary."""
        return cls(
            feedback_type=FeedbackType(data['feedback_type']),
            severity_level=SeverityLevel(data['severity_level']),
            component=ComponentType(data['component']),
            type_confidence=data['type_confidence'],
            severity_confidence=data['severity_confidence'],
            component_confidence=data['component_confidence'],
            overall_confidence=data['overall_confidence'],
            version=data.get('version'),
            keywords=data.get('keywords', []),
            sentiment=data.get('sentiment'),
            urgency_indicators=data.get('urgency_indicators', []),
            classification_timestamp=datetime.fromisoformat(data['classification_timestamp']),
            model_version=data.get('model_version', '1.0'),
            processing_time_ms=data.get('processing_time_ms')
        )

@dataclass
class ClassificationBatch:
    """Batch of feedback items to classify."""
    
    items: List[Dict[str, Any]]
    batch_id: str
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def add_item(self, item: Dict[str, Any]) -> None:
        """Add an item to the batch."""
        self.items.append(item)
    
    def get_item_count(self) -> int:
        """Get number of items in batch."""
        return len(self.items)
    
    def is_empty(self) -> bool:
        """Check if batch is empty."""
        return len(self.items) == 0

@dataclass
class ClassificationMetrics:
    """Metrics for classification performance."""
    
    total_classified: int = 0
    successful_classifications: int = 0
    failed_classifications: int = 0
    average_confidence: float = 0.0
    average_processing_time_ms: float = 0.0
    
    # Type distribution
    type_distribution: Dict[str, int] = None
    
    # Severity distribution
    severity_distribution: Dict[str, int] = None
    
    # Component distribution
    component_distribution: Dict[str, int] = None
    
    def __post_init__(self):
        if self.type_distribution is None:
            self.type_distribution = {}
        if self.severity_distribution is None:
            self.severity_distribution = {}
        if self.component_distribution is None:
            self.component_distribution = {}
    
    def add_classification(self, result: ClassificationResult, processing_time_ms: float) -> None:
        """Add a classification result to metrics."""
        self.total_classified += 1
        
        if result.overall_confidence > 0.5:  # Consider successful if confidence > 50%
            self.successful_classifications += 1
        else:
            self.failed_classifications += 1
        
        # Update averages
        self.average_confidence = (
            (self.average_confidence * (self.total_classified - 1) + result.overall_confidence) 
            / self.total_classified
        )
        self.average_processing_time_ms = (
            (self.average_processing_time_ms * (self.total_classified - 1) + processing_time_ms) 
            / self.total_classified
        )
        
        # Update distributions
        self.type_distribution[result.feedback_type.value] = (
            self.type_distribution.get(result.feedback_type.value, 0) + 1
        )
        self.severity_distribution[result.severity_level.value] = (
            self.severity_distribution.get(result.severity_level.value, 0) + 1
        )
        self.component_distribution[result.component.value] = (
            self.component_distribution.get(result.component.value, 0) + 1
        )
    
    def get_success_rate(self) -> float:
        """Get classification success rate."""
        if self.total_classified == 0:
            return 0.0
        return self.successful_classifications / self.total_classified
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_classified': self.total_classified,
            'successful_classifications': self.successful_classifications,
            'failed_classifications': self.failed_classifications,
            'success_rate': self.get_success_rate(),
            'average_confidence': self.average_confidence,
            'average_processing_time_ms': self.average_processing_time_ms,
            'type_distribution': self.type_distribution,
            'severity_distribution': self.severity_distribution,
            'component_distribution': self.component_distribution
        }

class ClassificationPrompt:
    """Prompt templates for OpenAI classification."""
    
    @staticmethod
    def get_classification_prompt() -> str:
        """Get the main classification prompt."""
        return """
You are an expert product feedback classifier. Analyze the following feedback and classify it according to the specified categories.

Feedback to classify:
Title: {title}
Content: {content}
Author: {author}
Source: {source_type}

Please classify this feedback and provide your analysis in the following JSON format:

{{
    "feedback_type": "one of: bug, feature_request, ux, pricing, docs, performance, security, integration, other",
    "severity_level": "one of: critical, high, medium, low, minimal",
    "component": "one of: authentication, ui, api, database, payment, notifications, search, dashboard, settings, mobile, desktop, integration, security, performance, other",
    "type_confidence": 0.0-1.0,
    "severity_confidence": 0.0-1.0,
    "component_confidence": 0.0-1.0,
    "version": "product version if mentioned, or null",
    "keywords": ["list", "of", "key", "terms"],
    "sentiment": "positive, negative, or neutral",
    "urgency_indicators": ["list", "of", "urgency", "indicators"]
}}

Classification guidelines:
- BUG: Issues, errors, broken functionality
- FEATURE_REQUEST: Requests for new functionality
- UX: User experience issues, usability problems
- PRICING: Cost, billing, pricing concerns
- DOCS: Documentation issues, unclear instructions
- PERFORMANCE: Speed, responsiveness, resource usage
- SECURITY: Security vulnerabilities, privacy concerns
- INTEGRATION: Third-party integrations, API issues
- OTHER: Anything that doesn't fit the above categories

Severity guidelines:
- CRITICAL: System down, data loss, security breach
- HIGH: Major functionality broken, significant impact
- MEDIUM: Moderate impact, workaround available
- LOW: Minor issues, cosmetic problems
- MINIMAL: Enhancement suggestions, nice-to-have

Be precise and confident in your classifications. Provide detailed reasoning for your choices.
"""

    @staticmethod
    def get_batch_classification_prompt() -> str:
        """Get prompt for batch classification."""
        return """
You are an expert product feedback classifier. Analyze the following batch of feedback items and classify each one.

Feedback items to classify:
{feedback_items}

For each item, provide classification in this JSON format:
[
    {{
        "item_id": "unique_identifier",
        "feedback_type": "one of: bug, feature_request, ux, pricing, docs, performance, security, integration, other",
        "severity_level": "one of: critical, high, medium, low, minimal",
        "component": "one of: authentication, ui, api, database, payment, notifications, search, dashboard, settings, mobile, desktop, integration, security, performance, other",
        "type_confidence": 0.0-1.0,
        "severity_confidence": 0.0-1.0,
        "component_confidence": 0.0-1.0,
        "version": "product version if mentioned, or null",
        "keywords": ["list", "of", "key", "terms"],
        "sentiment": "positive, negative, or neutral",
        "urgency_indicators": ["list", "of", "urgency", "indicators"]
    }}
]

Follow the same classification guidelines as the single-item prompt. Be consistent and accurate.
"""

class ClassificationRules:
    """Business rules for classification validation and adjustment."""
    
    @staticmethod
    def validate_classification(result: ClassificationResult) -> Tuple[bool, List[str]]:
        """Validate a classification result."""
        errors = []
        
        # Check confidence scores
        if not 0.0 <= result.type_confidence <= 1.0:
            errors.append("Type confidence must be between 0.0 and 1.0")
        
        if not 0.0 <= result.severity_confidence <= 1.0:
            errors.append("Severity confidence must be between 0.0 and 1.0")
        
        if not 0.0 <= result.component_confidence <= 1.0:
            errors.append("Component confidence must be between 0.0 and 1.0")
        
        if not 0.0 <= result.overall_confidence <= 1.0:
            errors.append("Overall confidence must be between 0.0 and 1.0")
        
        # Check for reasonable confidence levels
        if result.overall_confidence < 0.3:
            errors.append("Overall confidence is very low, consider manual review")
        
        # Check for consistency
        if result.feedback_type == FeedbackType.BUG and result.severity_level == SeverityLevel.MINIMAL:
            errors.append("Bug reports should not be minimal severity")
        
        if result.feedback_type == FeedbackType.FEATURE_REQUEST and result.severity_level == SeverityLevel.CRITICAL:
            errors.append("Feature requests should not be critical severity")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def adjust_classification(result: ClassificationResult) -> ClassificationResult:
        """Apply business rules to adjust classification if needed."""
        # Adjust severity for feature requests
        if (result.feedback_type == FeedbackType.FEATURE_REQUEST and 
            result.severity_level in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]):
            result.severity_level = SeverityLevel.MEDIUM
            result.severity_confidence = min(result.severity_confidence, 0.7)
        
        # Adjust severity for bugs
        if (result.feedback_type == FeedbackType.BUG and 
            result.severity_level == SeverityLevel.MINIMAL):
            result.severity_level = SeverityLevel.LOW
            result.severity_confidence = min(result.severity_confidence, 0.6)
        
        # Recalculate overall confidence
        result.overall_confidence = (
            result.type_confidence + result.severity_confidence + result.component_confidence
        ) / 3.0
        
        return result

