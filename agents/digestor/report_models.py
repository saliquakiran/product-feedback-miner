"""
Data models and templates for report generation in the Digestor Agent.

This module defines the data structures, templates, and formatting
for generating various types of reports and summaries.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

class ReportType(str, Enum):
    """Types of reports that can be generated."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    CUSTOM = "custom"

class ReportFormat(str, Enum):
    """Output formats for reports."""
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"
    PDF = "pdf"
    TEXT = "text"

class NotificationChannel(str, Enum):
    """Channels for sending notifications."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    CONSOLE = "console"

class PriorityLevel(str, Enum):
    """Priority levels for notifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ReportData:
    """Data structure for report content."""
    title: str
    summary: str
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class ReportTemplate:
    """Template for generating reports."""
    name: str
    report_type: ReportType
    format: ReportFormat
    template_content: str
    variables: List[str] = field(default_factory=list)
    channels: List[NotificationChannel] = field(default_factory=list)
    priority: PriorityLevel = PriorityLevel.MEDIUM
    schedule: Optional[str] = None  # Cron expression

@dataclass
class NotificationConfig:
    """Configuration for notifications."""
    channel: NotificationChannel
    enabled: bool = True
    recipients: List[str] = field(default_factory=list)
    template: Optional[str] = None
    priority_threshold: PriorityLevel = PriorityLevel.MEDIUM
    rate_limit: int = 10  # Max notifications per hour

@dataclass
class DigestorConfig:
    """Configuration for the Digestor Agent."""
    # Report generation
    enable_hourly_reports: bool = True
    enable_daily_reports: bool = True
    enable_weekly_reports: bool = True
    enable_monthly_reports: bool = True
    
    # Notification settings
    enable_notifications: bool = True
    notification_channels: List[NotificationConfig] = field(default_factory=list)
    
    # Report settings
    max_reports_per_hour: int = 5
    report_retention_days: int = 30
    
    # Analytics settings
    enable_trend_analysis: bool = True
    enable_cluster_analysis: bool = True
    enable_priority_analysis: bool = True
    
    # Output settings
    default_format: ReportFormat = ReportFormat.HTML
    include_charts: bool = True
    include_raw_data: bool = False

class ReportTemplates:
    """Predefined report templates for different stakeholders."""
    
    @staticmethod
    def get_executive_summary_template() -> ReportTemplate:
        """Get executive summary template."""
        return ReportTemplate(
            name="Executive Summary",
            report_type=ReportType.EXECUTIVE,
            format=ReportFormat.HTML,
            template_content="""
<!DOCTYPE html>
<html>
<head>
    <title>Product Feedback Executive Summary</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #e8f4fd; border-radius: 5px; }}
        .critical {{ color: #d32f2f; font-weight: bold; }}
        .high {{ color: #f57c00; font-weight: bold; }}
        .medium {{ color: #fbc02d; }}
        .low {{ color: #388e3c; }}
        .chart {{ margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Product Feedback Executive Summary</h1>
        <p><strong>Period:</strong> {start_date} to {end_date}</p>
        <p><strong>Generated:</strong> {generated_at}</p>
    </div>
    
    <div class="metrics">
        <div class="metric">
            <h3>Total Feedback</h3>
            <p style="font-size: 24px; margin: 0;">{total_feedback}</p>
        </div>
        <div class="metric">
            <h3>High Priority</h3>
            <p style="font-size: 24px; margin: 0;" class="critical">{high_priority_count}</p>
        </div>
        <div class="metric">
            <h3>Tickets Created</h3>
            <p style="font-size: 24px; margin: 0;">{tickets_created}</p>
        </div>
        <div class="metric">
            <h3>Resolution Rate</h3>
            <p style="font-size: 24px; margin: 0;">{resolution_rate}%</p>
        </div>
    </div>
    
    <h2>🎯 Key Insights</h2>
    <ul>
        {key_insights}
    </ul>
    
    <h2>📈 Priority Distribution</h2>
    <div class="chart">
        <p><span class="critical">Critical:</span> {critical_count} ({critical_percentage}%)</p>
        <p><span class="high">High:</span> {high_count} ({high_percentage}%)</p>
        <p><span class="medium">Medium:</span> {medium_count} ({medium_percentage}%)</p>
        <p><span class="low">Low:</span> {low_count} ({low_percentage}%)</p>
    </div>
    
    <h2>🔧 Top Components</h2>
    <ol>
        {top_components}
    </ol>
    
    <h2>📊 Trend Analysis</h2>
    <p>{trend_analysis}</p>
    
    <h2>🚨 Critical Issues Requiring Attention</h2>
    <ul>
        {critical_issues}
    </ul>
    
    <h2>📋 Recommendations</h2>
    <ol>
        {recommendations}
    </ol>
    
    <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ccc;">
        <p><em>This report was automatically generated by the Product Feedback Miner system.</em></p>
    </footer>
</body>
</html>
            """,
            variables=[
                "start_date", "end_date", "generated_at", "total_feedback",
                "high_priority_count", "tickets_created", "resolution_rate",
                "key_insights", "critical_count", "critical_percentage",
                "high_count", "high_percentage", "medium_count", "medium_percentage",
                "low_count", "low_percentage", "top_components", "trend_analysis",
                "critical_issues", "recommendations"
            ],
            channels=[NotificationChannel.EMAIL],
            priority=PriorityLevel.HIGH
        )
    
    @staticmethod
    def get_technical_summary_template() -> ReportTemplate:
        """Get technical summary template."""
        return ReportTemplate(
            name="Technical Summary",
            report_type=ReportType.TECHNICAL,
            format=ReportFormat.MARKDOWN,
            template_content="""
# 🔧 Technical Feedback Summary

**Period:** {start_date} to {end_date}  
**Generated:** {generated_at}

## 📊 Processing Statistics

- **Total Items Processed:** {total_processed}
- **Successfully Classified:** {classified_count} ({classification_rate}%)
- **Clustered:** {clustered_count} ({clustering_rate}%)
- **Prioritized:** {prioritized_count} ({prioritization_rate}%)
- **Tickets Created:** {tickets_created}

## 🎯 Classification Breakdown

| Type | Count | Percentage |
|------|-------|------------|
| Bug | {bug_count} | {bug_percentage}% |
| Feature Request | {feature_count} | {feature_percentage}% |
| Performance | {performance_count} | {performance_percentage}% |
| Other | {other_count} | {other_percentage}% |

## 🔍 Clustering Analysis

- **Total Clusters:** {cluster_count}
- **Average Cluster Size:** {avg_cluster_size}
- **Largest Cluster:** {largest_cluster_title} ({largest_cluster_size} items)

### Top Clusters by Size
{top_clusters}

## ⚡ Performance Metrics

- **Average Processing Time:** {avg_processing_time}s
- **Peak Processing Rate:** {peak_processing_rate} items/hour
- **Error Rate:** {error_rate}%

## 🐛 Error Analysis

{error_analysis}

## 📈 Component Analysis

{component_analysis}

## 🔄 System Health

- **Agent Status:** {agent_status}
- **Database Health:** {database_health}
- **API Status:** {api_status}

## 📋 Next Steps

{next_steps}
            """,
            variables=[
                "start_date", "end_date", "generated_at", "total_processed",
                "classified_count", "classification_rate", "clustered_count",
                "clustering_rate", "prioritized_count", "prioritization_rate",
                "tickets_created", "bug_count", "bug_percentage", "feature_count",
                "feature_percentage", "performance_count", "performance_percentage",
                "other_count", "other_percentage", "cluster_count", "avg_cluster_size",
                "largest_cluster_title", "largest_cluster_size", "top_clusters",
                "avg_processing_time", "peak_processing_rate", "error_rate",
                "error_analysis", "component_analysis", "agent_status",
                "database_health", "api_status", "next_steps"
            ],
            channels=[NotificationChannel.SLACK],
            priority=PriorityLevel.MEDIUM
        )
    
    @staticmethod
    def get_hourly_digest_template() -> ReportTemplate:
        """Get hourly digest template."""
        return ReportTemplate(
            name="Hourly Digest",
            report_type=ReportType.HOURLY,
            format=ReportFormat.TEXT,
            template_content="""
🚨 HOURLY FEEDBACK DIGEST - {hour}

📊 SUMMARY:
• New feedback: {new_feedback_count}
• High priority: {high_priority_count}
• Tickets created: {tickets_created}
• Critical issues: {critical_issues_count}

🔥 TOP PRIORITIES:
{top_priorities}

⚠️ CRITICAL ALERTS:
{critical_alerts}

📈 TRENDS:
{trends}

🔧 COMPONENTS AFFECTED:
{affected_components}

📋 ACTIONS TAKEN:
{actions_taken}

---
Generated at {generated_at}
            """,
            variables=[
                "hour", "new_feedback_count", "high_priority_count",
                "tickets_created", "critical_issues_count", "top_priorities",
                "critical_alerts", "trends", "affected_components",
                "actions_taken", "generated_at"
            ],
            channels=[NotificationChannel.SLACK, NotificationChannel.EMAIL],
            priority=PriorityLevel.HIGH
        )
    
    @staticmethod
    def get_daily_summary_template() -> ReportTemplate:
        """Get daily summary template."""
        return ReportTemplate(
            name="Daily Summary",
            report_type=ReportType.DAILY,
            format=ReportFormat.HTML,
            template_content="""
<!DOCTYPE html>
<html>
<head>
    <title>Daily Feedback Summary - {date}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f8ff; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007acc; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #f9f9f9; border-radius: 3px; }}
        .critical {{ color: #d32f2f; }}
        .high {{ color: #f57c00; }}
        .medium {{ color: #fbc02d; }}
        .low {{ color: #388e3c; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📅 Daily Feedback Summary</h1>
        <p><strong>Date:</strong> {date}</p>
        <p><strong>Generated:</strong> {generated_at}</p>
    </div>
    
    <div class="section">
        <h2>📊 Daily Metrics</h2>
        <div class="metric">Total Feedback: <strong>{total_feedback}</strong></div>
        <div class="metric">High Priority: <strong class="critical">{high_priority}</strong></div>
        <div class="metric">Tickets Created: <strong>{tickets_created}</strong></div>
        <div class="metric">Resolved: <strong>{resolved_tickets}</strong></div>
    </div>
    
    <div class="section">
        <h2>🎯 Priority Breakdown</h2>
        <p><span class="critical">Critical:</span> {critical_count} ({critical_percentage}%)</p>
        <p><span class="high">High:</span> {high_count} ({high_percentage}%)</p>
        <p><span class="medium">Medium:</span> {medium_count} ({medium_percentage}%)</p>
        <p><span class="low">Low:</span> {low_count} ({low_percentage}%)</p>
    </div>
    
    <div class="section">
        <h2>🔧 Top Issues by Component</h2>
        {component_breakdown}
    </div>
    
    <div class="section">
        <h2>📈 Trends vs Previous Day</h2>
        {trend_comparison}
    </div>
    
    <div class="section">
        <h2>🚨 Critical Issues</h2>
        {critical_issues}
    </div>
    
    <div class="section">
        <h2>📋 Recommendations</h2>
        {recommendations}
    </div>
</body>
</html>
            """,
            variables=[
                "date", "generated_at", "total_feedback", "high_priority",
                "tickets_created", "resolved_tickets", "critical_count",
                "critical_percentage", "high_count", "high_percentage",
                "medium_count", "medium_percentage", "low_count", "low_percentage",
                "component_breakdown", "trend_comparison", "critical_issues",
                "recommendations"
            ],
            channels=[NotificationChannel.EMAIL],
            priority=PriorityLevel.MEDIUM
        )

class ReportFormatter:
    """Formats report data using templates."""
    
    @staticmethod
    def format_report(
        template: ReportTemplate,
        data: Dict[str, Any],
        format_override: Optional[ReportFormat] = None
    ) -> str:
        """Format report data using a template."""
        try:
            # Use format override if provided
            output_format = format_override or template.format
            
            # Format the content
            formatted_content = template.template_content.format(**data)
            
            # Apply format-specific post-processing
            if output_format == ReportFormat.HTML:
                return ReportFormatter._post_process_html(formatted_content)
            elif output_format == ReportFormat.MARKDOWN:
                return ReportFormatter._post_process_markdown(formatted_content)
            elif output_format == ReportFormat.JSON:
                return ReportFormatter._format_as_json(data)
            else:
                return formatted_content
        
        except Exception as e:
            return f"Error formatting report: {str(e)}"
    
    @staticmethod
    def _post_process_html(content: str) -> str:
        """Post-process HTML content."""
        # Add any HTML-specific formatting here
        return content
    
    @staticmethod
    def _post_process_markdown(content: str) -> str:
        """Post-process Markdown content."""
        # Add any Markdown-specific formatting here
        return content
    
    @staticmethod
    def _format_as_json(data: Dict[str, Any]) -> str:
        """Format data as JSON."""
        import json
        return json.dumps(data, indent=2, default=str)

class NotificationTemplates:
    """Templates for different types of notifications."""
    
    @staticmethod
    def get_critical_alert_template() -> str:
        """Get critical alert notification template."""
        return """
🚨 CRITICAL ALERT: {title}

**Priority:** {priority}
**Component:** {component}
**Impact:** {impact}

**Description:**
{description}

**Actions Taken:**
{actions_taken}

**Next Steps:**
{next_steps}

---
Generated at {timestamp}
        """
    
    @staticmethod
    def get_trend_alert_template() -> str:
        """Get trend alert notification template."""
        return """
📈 TREND ALERT: {trend_type}

**Current Value:** {current_value}
**Previous Value:** {previous_value}
**Change:** {change_percentage}%

**Description:**
{description}

**Recommendation:**
{recommendation}

---
Generated at {timestamp}
        """
    
    @staticmethod
    def get_daily_summary_template() -> str:
        """Get daily summary notification template."""
        return """
📅 Daily Feedback Summary - {date}

**Key Metrics:**
• Total Feedback: {total_feedback}
• High Priority: {high_priority}
• Tickets Created: {tickets_created}
• Resolved: {resolved}

**Top Issues:**
{top_issues}

**Critical Alerts:**
{critical_alerts}

---
Generated at {timestamp}
        """
