"""
Data models and templates for ticket creation in the Actioner Agent.

This module defines the data structures, templates, and formatting
for creating tickets in Jira and GitHub from high-priority feedback.
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

class TicketStatus(str, Enum):
    """Ticket status values."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"

class TicketPriority(str, Enum):
    """Ticket priority levels."""
    LOWEST = "lowest"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    HIGHEST = "highest"
    CRITICAL = "critical"
    BLOCKER = "blocker"

class TicketType(str, Enum):
    """Ticket types for different platforms."""
    BUG = "bug"
    TASK = "task"
    STORY = "story"
    EPIC = "epic"
    SUBTASK = "subtask"
    ISSUE = "issue"
    ENHANCEMENT = "enhancement"

class PlatformType(str, Enum):
    """Supported ticket platforms."""
    JIRA = "jira"
    GITHUB = "github"
    LINEAR = "linear"
    ASANA = "asana"

@dataclass
class TicketTemplate:
    """Template for creating tickets."""
    platform: PlatformType
    ticket_type: TicketType
    title_template: str
    description_template: str
    labels: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)
    assignee_rules: Dict[str, Any] = field(default_factory=dict)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TicketData:
    """Data structure for ticket creation."""
    title: str
    description: str
    priority: TicketPriority
    ticket_type: TicketType
    platform: PlatformType
    labels: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    due_date: Optional[datetime] = None
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TicketResult:
    """Result of ticket creation."""
    success: bool
    ticket_id: Optional[str] = None
    ticket_url: Optional[str] = None
    platform: Optional[PlatformType] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ActionerConfig:
    """Configuration for the Actioner Agent."""
    priority_threshold: float = 0.7
    max_tickets_per_hour: int = 10
    max_tickets_per_day: int = 50
    enable_jira: bool = True
    enable_github: bool = True
    enable_linear: bool = False
    enable_asana: bool = False
    auto_assign: bool = True
    require_approval: bool = False
    escalation_rules: Dict[str, Any] = field(default_factory=dict)
    notification_channels: List[str] = field(default_factory=list)

class TicketTemplates:
    """Predefined ticket templates for different scenarios."""
    
    @staticmethod
    def get_bug_template(platform: PlatformType) -> TicketTemplate:
        """Get bug ticket template for platform."""
        if platform == PlatformType.JIRA:
            return TicketTemplate(
                platform=platform,
                ticket_type=TicketType.BUG,
                title_template="[BUG] {title}",
                description_template="""
**Description:**
{description}

**Steps to Reproduce:**
{steps_to_reproduce}

**Expected Behavior:**
{expected_behavior}

**Actual Behavior:**
{actual_behavior}

**Environment:**
- Component: {component}
- Priority Score: {priority_score}
- Feedback Type: {feedback_type}
- User Count: {user_count}
- Cluster Size: {cluster_size}

**Original Feedback:**
- Title: {original_title}
- Author: {author}
- URL: {url}
- Timestamp: {timestamp}

**Priority Reasoning:**
{priority_reasoning}
""",
                labels=["bug", "feedback", "high-priority"],
                components=["{component}"],
                custom_fields={
                    "priority": "{priority}",
                    "severity": "{severity}",
                    "affects_version": "{version}"
                }
            )
        elif platform == PlatformType.GITHUB:
            return TicketTemplate(
                platform=platform,
                ticket_type=TicketType.ISSUE,
                title_template="🐛 {title}",
                description_template="""
## Description
{description}

## Steps to Reproduce
{steps_to_reproduce}

## Expected Behavior
{expected_behavior}

## Actual Behavior
{actual_behavior}

## Environment
- **Component:** {component}
- **Priority Score:** {priority_score}
- **Feedback Type:** {feedback_type}
- **User Count:** {user_count}
- **Cluster Size:** {cluster_size}

## Original Feedback
- **Title:** {original_title}
- **Author:** {author}
- **URL:** {url}
- **Timestamp:** {timestamp}

## Priority Reasoning
{priority_reasoning}

---
*This issue was automatically created from high-priority feedback.*
""",
                labels=["bug", "feedback", "high-priority", "{component}"],
                custom_fields={}
            )
        else:
            raise ValueError(f"Unsupported platform: {platform}")
    
    @staticmethod
    def get_feature_request_template(platform: PlatformType) -> TicketTemplate:
        """Get feature request template for platform."""
        if platform == PlatformType.JIRA:
            return TicketTemplate(
                platform=platform,
                ticket_type=TicketType.STORY,
                title_template="[FEATURE] {title}",
                description_template="""
**Description:**
{description}

**Business Value:**
{business_value}

**Acceptance Criteria:**
{acceptance_criteria}

**Environment:**
- Component: {component}
- Priority Score: {priority_score}
- Feedback Type: {feedback_type}
- User Count: {user_count}
- Cluster Size: {cluster_size}

**Original Feedback:**
- Title: {original_title}
- Author: {author}
- URL: {url}
- Timestamp: {timestamp}

**Priority Reasoning:**
{priority_reasoning}
""",
                labels=["feature", "feedback", "enhancement"],
                components=["{component}"],
                custom_fields={
                    "priority": "{priority}",
                    "story_points": "{story_points}"
                }
            )
        elif platform == PlatformType.GITHUB:
            return TicketTemplate(
                platform=platform,
                ticket_type=TicketType.ENHANCEMENT,
                title_template="✨ {title}",
                description_template="""
## Description
{description}

## Business Value
{business_value}

## Acceptance Criteria
{acceptance_criteria}

## Environment
- **Component:** {component}
- **Priority Score:** {priority_score}
- **Feedback Type:** {feedback_type}
- **User Count:** {user_count}
- **Cluster Size:** {cluster_size}

## Original Feedback
- **Title:** {original_title}
- **Author:** {author}
- **URL:** {url}
- **Timestamp:** {timestamp}

## Priority Reasoning
{priority_reasoning}

---
*This enhancement was automatically created from high-priority feedback.*
""",
                labels=["enhancement", "feedback", "feature-request", "{component}"],
                custom_fields={}
            )
        else:
            raise ValueError(f"Unsupported platform: {platform}")
    
    @staticmethod
    def get_performance_template(platform: PlatformType) -> TicketTemplate:
        """Get performance issue template for platform."""
        if platform == PlatformType.JIRA:
            return TicketTemplate(
                platform=platform,
                ticket_type=TicketType.TASK,
                title_template="[PERFORMANCE] {title}",
                description_template="""
**Description:**
{description}

**Performance Impact:**
{performance_impact}

**Metrics:**
{metrics}

**Environment:**
- Component: {component}
- Priority Score: {priority_score}
- Feedback Type: {feedback_type}
- User Count: {user_count}
- Cluster Size: {cluster_size}

**Original Feedback:**
- Title: {original_title}
- Author: {author}
- URL: {url}
- Timestamp: {timestamp}

**Priority Reasoning:**
{priority_reasoning}
""",
                labels=["performance", "feedback", "optimization"],
                components=["{component}"],
                custom_fields={
                    "priority": "{priority}",
                    "severity": "{severity}"
                }
            )
        elif platform == PlatformType.GITHUB:
            return TicketTemplate(
                platform=platform,
                ticket_type=TicketType.ISSUE,
                title_template="⚡ {title}",
                description_template="""
## Description
{description}

## Performance Impact
{performance_impact}

## Metrics
{metrics}

## Environment
- **Component:** {component}
- **Priority Score:** {priority_score}
- **Feedback Type:** {feedback_type}
- **User Count:** {user_count}
- **Cluster Size:** {cluster_size}

## Original Feedback
- **Title:** {original_title}
- **Author:** {author}
- **URL:** {url}
- **Timestamp:** {timestamp}

## Priority Reasoning
{priority_reasoning}

---
*This performance issue was automatically created from high-priority feedback.*
""",
                labels=["performance", "feedback", "optimization", "{component}"],
                custom_fields={}
            )
        else:
            raise ValueError(f"Unsupported platform: {platform}")

class PriorityMapper:
    """Maps priority scores to ticket priorities."""
    
    @staticmethod
    def map_priority_score(score: float, platform: PlatformType) -> TicketPriority:
        """Map priority score to platform-specific priority."""
        if platform == PlatformType.JIRA:
            if score >= 0.95:
                return TicketPriority.BLOCKER
            elif score >= 0.85:
                return TicketPriority.CRITICAL
            elif score >= 0.75:
                return TicketPriority.HIGH
            elif score >= 0.65:
                return TicketPriority.MEDIUM
            elif score >= 0.55:
                return TicketPriority.LOW
            else:
                return TicketPriority.LOWEST
        elif platform == PlatformType.GITHUB:
            if score >= 0.9:
                return TicketPriority.HIGHEST
            elif score >= 0.8:
                return TicketPriority.HIGH
            elif score >= 0.7:
                return TicketPriority.MEDIUM
            elif score >= 0.6:
                return TicketPriority.LOW
            else:
                return TicketPriority.LOWEST
        else:
            # Default mapping
            if score >= 0.9:
                return TicketPriority.HIGHEST
            elif score >= 0.8:
                return TicketPriority.HIGH
            elif score >= 0.7:
                return TicketPriority.MEDIUM
            elif score >= 0.6:
                return TicketPriority.LOW
            else:
                return TicketPriority.LOWEST
    
    @staticmethod
    def get_priority_emoji(priority: TicketPriority) -> str:
        """Get emoji for priority level."""
        emoji_map = {
            TicketPriority.LOWEST: "🔵",
            TicketPriority.LOW: "🟢",
            TicketPriority.MEDIUM: "🟡",
            TicketPriority.HIGH: "🟠",
            TicketPriority.HIGHEST: "🔴",
            TicketPriority.CRITICAL: "🚨",
            TicketPriority.BLOCKER: "💥"
        }
        return emoji_map.get(priority, "⚪")

class TicketFormatter:
    """Formats ticket data using templates."""
    
    @staticmethod
    def format_ticket_data(
        feedback_data: Dict[str, Any],
        priority_data: Dict[str, Any],
        cluster_data: Optional[Dict[str, Any]] = None,
        template: TicketTemplate = None
    ) -> TicketData:
        """Format feedback data into ticket data."""
        if template is None:
            # Determine template based on feedback type
            feedback_type = feedback_data.get("feedback_type", "bug")
            platform = PlatformType.JIRA  # Default platform
            
            if feedback_type == "bug":
                template = TicketTemplates.get_bug_template(platform)
            elif feedback_type == "feature_request":
                template = TicketTemplates.get_feature_request_template(platform)
            elif feedback_type == "performance":
                template = TicketTemplates.get_performance_template(platform)
            else:
                template = TicketTemplates.get_bug_template(platform)
        
        # Map priority score to ticket priority
        priority_score = priority_data.get("overall_score", 0.0)
        ticket_priority = PriorityMapper.map_priority_score(priority_score, template.platform)
        
        # Format title
        title = template.title_template.format(
            title=feedback_data.get("title", "Untitled")
        )
        
        # Format description
        description = template.description_template.format(
            description=feedback_data.get("body", ""),
            steps_to_reproduce=feedback_data.get("steps_to_reproduce", "Not provided"),
            expected_behavior=feedback_data.get("expected_behavior", "Not specified"),
            actual_behavior=feedback_data.get("actual_behavior", "Not specified"),
            business_value=feedback_data.get("business_value", "Not specified"),
            acceptance_criteria=feedback_data.get("acceptance_criteria", "Not specified"),
            performance_impact=feedback_data.get("performance_impact", "Not specified"),
            metrics=feedback_data.get("metrics", "Not available"),
            component=feedback_data.get("component", "unknown"),
            priority_score=priority_score,
            feedback_type=feedback_data.get("feedback_type", "unknown"),
            user_count=cluster_data.get("size", 1) if cluster_data else 1,
            cluster_size=cluster_data.get("size", 1) if cluster_data else 1,
            original_title=feedback_data.get("title", ""),
            author=feedback_data.get("author", "unknown"),
            url=feedback_data.get("url", ""),
            timestamp=feedback_data.get("timestamp", ""),
            priority_reasoning=", ".join(priority_data.get("reasoning", [])),
            priority=ticket_priority.value,
            severity=feedback_data.get("severity", "medium"),
            version=feedback_data.get("version", "latest"),
            story_points=TicketFormatter._estimate_story_points(priority_score)
        )
        
        # Format labels
        labels = []
        for label in template.labels:
            formatted_label = label.format(
                component=feedback_data.get("component", "unknown"),
                feedback_type=feedback_data.get("feedback_type", "unknown")
            )
            labels.append(formatted_label)
        
        # Format components
        components = []
        for component in template.components:
            formatted_component = component.format(
                component=feedback_data.get("component", "unknown")
            )
            components.append(formatted_component)
        
        return TicketData(
            title=title,
            description=description,
            priority=ticket_priority,
            ticket_type=template.ticket_type,
            platform=template.platform,
            labels=labels,
            components=components,
            custom_fields=template.custom_fields,
            metadata={
                "original_feedback_id": feedback_data.get("id"),
                "priority_score": priority_score,
                "cluster_id": cluster_data.get("id") if cluster_data else None,
                "template_used": template.platform.value
            }
        )
    
    @staticmethod
    def _estimate_story_points(priority_score: float) -> int:
        """Estimate story points based on priority score."""
        if priority_score >= 0.9:
            return 8
        elif priority_score >= 0.8:
            return 5
        elif priority_score >= 0.7:
            return 3
        elif priority_score >= 0.6:
            return 2
        else:
            return 1
