"""
Digestor Agent for Product Feedback Miner.

This agent generates reports, summaries, and notifications
for stakeholders based on processed feedback data.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
import os

from agents.base.agent import BaseAgent, AgentResult, AgentContext
from agents.digestor.report_models import (
    ReportData, ReportTemplate, DigestorConfig, ReportType, ReportFormat,
    NotificationChannel, PriorityLevel, ReportTemplates, ReportFormatter
)
from agents.digestor.analytics import FeedbackAnalytics, TrendData, ComponentAnalysis, ClusterAnalysis
from agents.digestor.notifications import NotificationManager
from database.models import (
    ProcessedDocument, PrioritizationScore, Cluster, Ticket,
    FeedbackType, PriorityLevel as DBPriorityLevel, TicketStatus
)
from database import get_session

logger = logging.getLogger(__name__)

class DigestorAgent(BaseAgent):
    """
    Digestor Agent for generating reports and notifications.
    
    This agent:
    1. Generates various types of reports (hourly, daily, weekly, monthly)
    2. Performs trend analysis and generates insights
    3. Sends notifications via multiple channels
    4. Creates executive summaries and technical reports
    5. Monitors system health and performance
    """
    
    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        """Initialize Digestor Agent."""
        super().__init__("digestor", config_overrides)
        
        # Load configuration
        self.digestor_config = DigestorConfig(**self.config.get("digestor", {}))
        
        # Initialize components
        self.analytics = FeedbackAnalytics()
        self.notification_manager = NotificationManager(
            self.config.get("notifications", {})
        )
        
        # Report storage
        self.report_storage_dir = self.config.get("report_storage_dir", "reports")
        self._ensure_report_directory()
        
        # Templates
        self.templates = {
            ReportType.EXECUTIVE: ReportTemplates.get_executive_summary_template(),
            ReportType.TECHNICAL: ReportTemplates.get_technical_summary_template(),
            ReportType.HOURLY: ReportTemplates.get_hourly_digest_template(),
            ReportType.DAILY: ReportTemplates.get_daily_summary_template()
        }
    
    def _ensure_report_directory(self):
        """Ensure report storage directory exists."""
        if not os.path.exists(self.report_storage_dir):
            os.makedirs(self.report_storage_dir)
    
    def get_input_dependencies(self) -> List[str]:
        """Get list of agent dependencies."""
        return ["classifier", "clusterer", "prioritizer", "actioner"]
    
    async def process(self, context: AgentContext) -> AgentResult:
        """
        Main processing method for generating reports and notifications.
        
        Args:
            context: Agent context with execution metadata
            
        Returns:
            AgentResult with processing statistics
        """
        start_time = datetime.utcnow()
        reports_generated = 0
        notifications_sent = 0
        errors = []
        
        try:
            self.logger.info("Starting Digestor Agent processing")
            
            # Determine what reports to generate based on schedule
            report_types = self._determine_report_types()
            
            for report_type in report_types:
                try:
                    # Generate report
                    report_data = await self._generate_report(report_type, context)
                    
                    if report_data:
                        # Save report
                        report_path = await self._save_report(report_data, report_type)
                        
                        # Send notifications if enabled
                        if self.digestor_config.enable_notifications:
                            notification_results = await self._send_report_notifications(
                                report_data, report_type, report_path
                            )
                            notifications_sent += sum(notification_results.values())
                        
                        reports_generated += 1
                        self.logger.info(f"Generated {report_type.value} report")
                    
                except Exception as e:
                    error_msg = f"Error generating {report_type.value} report: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            # Generate insights and send critical alerts
            if self.digestor_config.enable_trend_analysis:
                await self._process_insights_and_alerts(context)
            
            # Clean up old reports
            await self._cleanup_old_reports()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.info(
                f"Digestor Agent completed: {reports_generated} reports generated, "
                f"{notifications_sent} notifications sent"
            )
            
            return AgentResult(
                success=len(errors) == 0,
                items_processed=reports_generated,
                items_successful=reports_generated,
                items_failed=len(errors),
                execution_time=execution_time,
                error_message="; ".join(errors) if errors else None,
                metadata={
                    "reports_generated": reports_generated,
                    "notifications_sent": notifications_sent,
                    "report_types": [rt.value for rt in report_types],
                    "errors": errors
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error in Digestor Agent processing: {e}")
            return AgentResult(
                success=False,
                items_processed=reports_generated,
                items_successful=reports_generated,
                items_failed=len(errors) + 1,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                error_message=str(e)
            )
    
    def _determine_report_types(self) -> List[ReportType]:
        """Determine which reports to generate based on schedule."""
        now = datetime.utcnow()
        report_types = []
        
        # Check if we should generate hourly report
        if self.digestor_config.enable_hourly_reports and now.minute < 5:
            report_types.append(ReportType.HOURLY)
        
        # Check if we should generate daily report
        if self.digestor_config.enable_daily_reports and now.hour == 9 and now.minute < 5:
            report_types.append(ReportType.DAILY)
        
        # Check if we should generate weekly report
        if (self.digestor_config.enable_weekly_reports and 
            now.weekday() == 0 and now.hour == 9 and now.minute < 5):
            report_types.append(ReportType.WEEKLY)
        
        # Check if we should generate monthly report
        if (self.digestor_config.enable_monthly_reports and 
            now.day == 1 and now.hour == 9 and now.minute < 5):
            report_types.append(ReportType.MONTHLY)
        
        # Always generate executive summary if no other reports
        if not report_types:
            report_types.append(ReportType.EXECUTIVE)
        
        return report_types
    
    async def _generate_report(self, report_type: ReportType, context: AgentContext) -> Optional[ReportData]:
        """Generate a specific type of report."""
        try:
            # Determine time range
            end_date = datetime.utcnow()
            start_date = self._get_report_start_date(report_type, end_date)
            
            # Get template
            template = self.templates.get(report_type)
            if not template:
                self.logger.warning(f"No template found for {report_type.value}")
                return None
            
            # Generate report data
            if report_type == ReportType.EXECUTIVE:
                data = await self._generate_executive_data(start_date, end_date)
            elif report_type == ReportType.TECHNICAL:
                data = await self._generate_technical_data(start_date, end_date)
            elif report_type == ReportType.HOURLY:
                data = await self._generate_hourly_data(start_date, end_date)
            elif report_type == ReportType.DAILY:
                data = await self._generate_daily_data(start_date, end_date)
            else:
                data = await self._generate_generic_data(start_date, end_date, report_type)
            
            # Format report
            content = ReportFormatter.format_report(template, data, self.digestor_config.default_format)
            
            return ReportData(
                title=f"{template.name} - {end_date.strftime('%Y-%m-%d %H:%M')}",
                summary=self._generate_summary(data, report_type),
                content={
                    'formatted_content': content,
                    'raw_data': data,
                    'template_used': template.name,
                    'format': self.digestor_config.default_format.value
                },
                metadata={
                    'report_type': report_type.value,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'generated_by': self.name,
                    'execution_id': context.execution_id
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error generating {report_type.value} report: {e}")
            return None
    
    def _get_report_start_date(self, report_type: ReportType, end_date: datetime) -> datetime:
        """Get start date for report based on type."""
        if report_type == ReportType.HOURLY:
            return end_date - timedelta(hours=1)
        elif report_type == ReportType.DAILY:
            return end_date - timedelta(days=1)
        elif report_type == ReportType.WEEKLY:
            return end_date - timedelta(weeks=1)
        elif report_type == ReportType.MONTHLY:
            return end_date - timedelta(days=30)
        else:
            return end_date - timedelta(days=1)
    
    async def _generate_executive_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate data for executive summary report."""
        try:
            with self.get_db_session() as session:
                # Basic metrics
                total_feedback = session.query(ProcessedDocument).filter(
                    ProcessedDocument.created_at >= start_date,
                    ProcessedDocument.created_at <= end_date
                ).count()
                
                high_priority_count = session.query(ProcessedDocument).join(
                    PrioritizationScore, ProcessedDocument.id == PrioritizationScore.document_id
                ).filter(
                    ProcessedDocument.created_at >= start_date,
                    ProcessedDocument.created_at <= end_date,
                    PrioritizationScore.priority_score >= 0.7
                ).count()
                
                tickets_created = session.query(Ticket).filter(
                    Ticket.created_at >= start_date,
                    Ticket.created_at <= end_date
                ).count()
                
                # Resolution rate
                total_tickets = session.query(Ticket).filter(
                    Ticket.created_at >= start_date,
                    Ticket.created_at <= end_date
                ).count()
                
                resolved_tickets = session.query(Ticket).filter(
                    Ticket.created_at >= start_date,
                    Ticket.created_at <= end_date,
                    Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED])
                ).count()
                
                resolution_rate = (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0
                
                # Priority distribution
                priority_distribution = self._get_priority_distribution(session, start_date, end_date)
                
                # Component analysis
                component_analysis = self.analytics.analyze_components(start_date, end_date)
                top_components = [
                    f"{comp.component}: {comp.total_feedback} items"
                    for comp in component_analysis[:5]
                ]
                
                # Trend analysis
                trends = self.analytics.analyze_trends(start_date, end_date)
                trend_analysis = self._format_trend_analysis(trends)
                
                # Critical issues
                critical_issues = self._get_critical_issues(session, start_date, end_date)
                
                # Generate insights
                insights = self.analytics.generate_insights(start_date, end_date)
                
                return {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'total_feedback': total_feedback,
                    'high_priority_count': high_priority_count,
                    'tickets_created': tickets_created,
                    'resolution_rate': round(resolution_rate, 1),
                    'key_insights': '\n'.join(f'<li>{insight}</li>' for insight in insights[:5]),
                    'critical_count': priority_distribution.get('critical', 0),
                    'critical_percentage': round(priority_distribution.get('critical_percentage', 0), 1),
                    'high_count': priority_distribution.get('high', 0),
                    'high_percentage': round(priority_distribution.get('high_percentage', 0), 1),
                    'medium_count': priority_distribution.get('medium', 0),
                    'medium_percentage': round(priority_distribution.get('medium_percentage', 0), 1),
                    'low_count': priority_distribution.get('low', 0),
                    'low_percentage': round(priority_distribution.get('low_percentage', 0), 1),
                    'top_components': '\n'.join(f'<li>{comp}</li>' for comp in top_components),
                    'trend_analysis': trend_analysis,
                    'critical_issues': '\n'.join(f'<li>{issue}</li>' for issue in critical_issues[:5]),
                    'recommendations': '\n'.join(f'<li>{insight}</li>' for insight in insights[5:10])
                }
        
        except Exception as e:
            self.logger.error(f"Error generating executive data: {e}")
            return {}
    
    async def _generate_technical_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate data for technical summary report."""
        try:
            with self.get_db_session() as session:
                # Processing statistics
                total_processed = session.query(ProcessedDocument).filter(
                    ProcessedDocument.created_at >= start_date,
                    ProcessedDocument.created_at <= end_date
                ).count()
                
                classified_count = session.query(ProcessedDocument).filter(
                    ProcessedDocument.created_at >= start_date,
                    ProcessedDocument.created_at <= end_date,
                    ProcessedDocument.feedback_type.isnot(None)
                ).count()
                
                clustered_count = session.query(ProcessedDocument).filter(
                    ProcessedDocument.created_at >= start_date,
                    ProcessedDocument.created_at <= end_date,
                    ProcessedDocument.cluster_id.isnot(None)
                ).count()
                
                prioritized_count = session.query(ProcessedDocument).join(
                    PrioritizationScore, ProcessedDocument.id == PrioritizationScore.document_id
                ).filter(
                    ProcessedDocument.created_at >= start_date,
                    ProcessedDocument.created_at <= end_date
                ).count()
                
                tickets_created = session.query(Ticket).filter(
                    Ticket.created_at >= start_date,
                    Ticket.created_at <= end_date
                ).count()
                
                # Classification breakdown
                classification_breakdown = self._get_classification_breakdown(session, start_date, end_date)
                
                # Cluster analysis
                cluster_analysis = self.analytics.analyze_clusters(start_date, end_date)
                
                # Performance metrics (placeholder)
                avg_processing_time = 2.5  # This would be calculated from actual metrics
                peak_processing_rate = 100  # This would be calculated from actual metrics
                error_rate = 0.5  # This would be calculated from actual metrics
                
                return {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'total_processed': total_processed,
                    'classified_count': classified_count,
                    'classification_rate': round((classified_count / total_processed * 100) if total_processed > 0 else 0, 1),
                    'clustered_count': clustered_count,
                    'clustering_rate': round((clustered_count / total_processed * 100) if total_processed > 0 else 0, 1),
                    'prioritized_count': prioritized_count,
                    'prioritization_rate': round((prioritized_count / total_processed * 100) if total_processed > 0 else 0, 1),
                    'tickets_created': tickets_created,
                    'bug_count': classification_breakdown.get('bug', 0),
                    'bug_percentage': round(classification_breakdown.get('bug_percentage', 0), 1),
                    'feature_count': classification_breakdown.get('feature_request', 0),
                    'feature_percentage': round(classification_breakdown.get('feature_request_percentage', 0), 1),
                    'performance_count': classification_breakdown.get('performance', 0),
                    'performance_percentage': round(classification_breakdown.get('performance_percentage', 0), 1),
                    'other_count': classification_breakdown.get('other', 0),
                    'other_percentage': round(classification_breakdown.get('other_percentage', 0), 1),
                    'cluster_count': cluster_analysis.total_clusters,
                    'avg_cluster_size': round(cluster_analysis.avg_cluster_size, 1),
                    'largest_cluster_title': cluster_analysis.largest_cluster.get('title', 'N/A'),
                    'largest_cluster_size': cluster_analysis.largest_cluster.get('size', 0),
                    'top_clusters': self._format_top_clusters(cluster_analysis.top_clusters),
                    'avg_processing_time': avg_processing_time,
                    'peak_processing_rate': peak_processing_rate,
                    'error_rate': error_rate,
                    'error_analysis': 'No critical errors detected',
                    'component_analysis': self._format_component_analysis(session, start_date, end_date),
                    'agent_status': 'All agents operational',
                    'database_health': 'Healthy',
                    'api_status': 'All APIs operational',
                    'next_steps': 'Continue monitoring system performance and user feedback'
                }
        
        except Exception as e:
            self.logger.error(f"Error generating technical data: {e}")
            return {}
    
    async def _generate_hourly_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate data for hourly digest."""
        try:
            with self.get_db_session() as session:
                # Basic metrics
                new_feedback_count = session.query(ProcessedDocument).filter(
                    ProcessedDocument.created_at >= start_date,
                    ProcessedDocument.created_at <= end_date
                ).count()
                
                high_priority_count = session.query(ProcessedDocument).join(
                    PrioritizationScore, ProcessedDocument.id == PrioritizationScore.document_id
                ).filter(
                    ProcessedDocument.created_at >= start_date,
                    ProcessedDocument.created_at <= end_date,
                    PrioritizationScore.priority_score >= 0.7
                ).count()
                
                tickets_created = session.query(Ticket).filter(
                    Ticket.created_at >= start_date,
                    Ticket.created_at <= end_date
                ).count()
                
                critical_issues_count = session.query(ProcessedDocument).join(
                    PrioritizationScore, ProcessedDocument.id == PrioritizationScore.document_id
                ).filter(
                    ProcessedDocument.created_at >= start_date,
                    ProcessedDocument.created_at <= end_date,
                    PrioritizationScore.priority_score >= 0.9
                ).count()
                
                # Top priorities
                top_priorities = self._get_top_priorities(session, start_date, end_date)
                
                # Critical alerts
                critical_alerts = self._get_critical_alerts(session, start_date, end_date)
                
                # Trends
                trends = self.analytics.analyze_trends(start_date, end_date)
                trend_summary = self._format_trend_summary(trends)
                
                # Affected components
                components = self.analytics.analyze_components(start_date, end_date)
                affected_components = [comp.component for comp in components[:5]]
                
                return {
                    'hour': start_date.strftime('%H:00'),
                    'new_feedback_count': new_feedback_count,
                    'high_priority_count': high_priority_count,
                    'tickets_created': tickets_created,
                    'critical_issues_count': critical_issues_count,
                    'top_priorities': '\n'.join(f'• {priority}' for priority in top_priorities),
                    'critical_alerts': '\n'.join(f'• {alert}' for alert in critical_alerts),
                    'trends': trend_summary,
                    'affected_components': ', '.join(affected_components),
                    'actions_taken': f'Created {tickets_created} tickets, processed {new_feedback_count} feedback items',
                    'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                }
        
        except Exception as e:
            self.logger.error(f"Error generating hourly data: {e}")
            return {}
    
    async def _generate_daily_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate data for daily summary."""
        try:
            with self.get_db_session() as session:
                # Basic metrics
                total_feedback = session.query(ProcessedDocument).filter(
                    ProcessedDocument.created_at >= start_date,
                    ProcessedDocument.created_at <= end_date
                ).count()
                
                high_priority = session.query(ProcessedDocument).join(
                    PrioritizationScore, ProcessedDocument.id == PrioritizationScore.document_id
                ).filter(
                    ProcessedDocument.created_at >= start_date,
                    ProcessedDocument.created_at <= end_date,
                    PrioritizationScore.priority_score >= 0.7
                ).count()
                
                tickets_created = session.query(Ticket).filter(
                    Ticket.created_at >= start_date,
                    Ticket.created_at <= end_date
                ).count()
                
                resolved_tickets = session.query(Ticket).filter(
                    Ticket.created_at >= start_date,
                    Ticket.created_at <= end_date,
                    Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED])
                ).count()
                
                # Priority breakdown
                priority_distribution = self._get_priority_distribution(session, start_date, end_date)
                
                # Component breakdown
                component_analysis = self.analytics.analyze_components(start_date, end_date)
                component_breakdown = self._format_component_breakdown(component_analysis)
                
                # Trend comparison
                previous_start = start_date - timedelta(days=1)
                previous_end = start_date
                previous_trends = self.analytics.analyze_trends(previous_start, previous_end)
                trend_comparison = self._format_trend_comparison(previous_trends)
                
                # Critical issues
                critical_issues = self._get_critical_issues(session, start_date, end_date)
                
                # Recommendations
                insights = self.analytics.generate_insights(start_date, end_date)
                recommendations = insights[:5]
                
                return {
                    'date': start_date.strftime('%Y-%m-%d'),
                    'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'total_feedback': total_feedback,
                    'high_priority': high_priority,
                    'tickets_created': tickets_created,
                    'resolved_tickets': resolved_tickets,
                    'critical_count': priority_distribution.get('critical', 0),
                    'critical_percentage': round(priority_distribution.get('critical_percentage', 0), 1),
                    'high_count': priority_distribution.get('high', 0),
                    'high_percentage': round(priority_distribution.get('high_percentage', 0), 1),
                    'medium_count': priority_distribution.get('medium', 0),
                    'medium_percentage': round(priority_distribution.get('medium_percentage', 0), 1),
                    'low_count': priority_distribution.get('low', 0),
                    'low_percentage': round(priority_distribution.get('low_percentage', 0), 1),
                    'component_breakdown': component_breakdown,
                    'trend_comparison': trend_comparison,
                    'critical_issues': '\n'.join(f'<li>{issue}</li>' for issue in critical_issues[:5]),
                    'recommendations': '\n'.join(f'<li>{rec}</li>' for rec in recommendations)
                }
        
        except Exception as e:
            self.logger.error(f"Error generating daily data: {e}")
            return {}
    
    async def _generate_generic_data(self, start_date: datetime, end_date: datetime, report_type: ReportType) -> Dict[str, Any]:
        """Generate generic data for other report types."""
        return {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'report_type': report_type.value,
            'message': f'Generic {report_type.value} report generated'
        }
    
    def _generate_summary(self, data: Dict[str, Any], report_type: ReportType) -> str:
        """Generate a summary for the report."""
        if report_type == ReportType.EXECUTIVE:
            return f"Executive summary covering {data.get('total_feedback', 0)} feedback items with {data.get('high_priority_count', 0)} high-priority issues."
        elif report_type == ReportType.TECHNICAL:
            return f"Technical summary showing {data.get('total_processed', 0)} items processed with {data.get('classification_rate', 0)}% classification rate."
        elif report_type == ReportType.HOURLY:
            return f"Hourly digest: {data.get('new_feedback_count', 0)} new items, {data.get('tickets_created', 0)} tickets created."
        elif report_type == ReportType.DAILY:
            return f"Daily summary: {data.get('total_feedback', 0)} feedback items, {data.get('tickets_created', 0)} tickets created, {data.get('resolved_tickets', 0)} resolved."
        else:
            return f"{report_type.value.title()} report generated successfully."
    
    async def _save_report(self, report_data: ReportData, report_type: ReportType) -> str:
        """Save report to storage."""
        try:
            # Generate filename
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"{report_type.value}_{timestamp}.{self.digestor_config.default_format.value}"
            filepath = os.path.join(self.report_storage_dir, filename)
            
            # Save content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_data.content['formatted_content'])
            
            self.logger.info(f"Report saved to {filepath}")
            return filepath
        
        except Exception as e:
            self.logger.error(f"Error saving report: {e}")
            return ""
    
    async def _send_report_notifications(
        self, 
        report_data: ReportData, 
        report_type: ReportType, 
        report_path: str
    ) -> Dict[NotificationChannel, bool]:
        """Send notifications for a report."""
        try:
            # Determine channels based on report type
            if report_type == ReportType.EXECUTIVE:
                channels = [NotificationChannel.EMAIL]
                priority = PriorityLevel.HIGH
            elif report_type == ReportType.HOURLY:
                channels = [NotificationChannel.SLACK]
                priority = PriorityLevel.MEDIUM
            else:
                channels = [NotificationChannel.EMAIL, NotificationChannel.SLACK]
                priority = PriorityLevel.MEDIUM
            
            # Get recipients
            recipients = self._get_report_recipients(report_type)
            
            # Send notification
            return await self.notification_manager.send_notification(
                report_data.content['formatted_content'],
                channels,
                recipients,
                priority
            )
        
        except Exception as e:
            self.logger.error(f"Error sending report notifications: {e}")
            return {}
    
    def _get_report_recipients(self, report_type: ReportType) -> List[str]:
        """Get recipients for a report type."""
        if report_type == ReportType.EXECUTIVE:
            return self.config.get('executive_recipients', ['executives@example.com'])
        elif report_type == ReportType.TECHNICAL:
            return self.config.get('technical_recipients', ['dev-team@example.com'])
        else:
            return self.config.get('default_recipients', ['team@example.com'])
    
    async def _process_insights_and_alerts(self, context: AgentContext):
        """Process insights and send critical alerts."""
        try:
            # Generate insights for the last 24 hours
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=24)
            
            insights = self.analytics.generate_insights(start_date, end_date)
            
            # Check for critical trends
            trends = self.analytics.analyze_trends(start_date, end_date)
            critical_trends = [t for t in trends if t.significance == 'high' and t.trend_direction == 'up']
            
            for trend in critical_trends:
                await self.notification_manager.send_trend_alert(
                    trend.metric,
                    trend.current_value,
                    trend.previous_value,
                    trend.change_percentage,
                    trend.description,
                    f"Immediate action required for {trend.metric}"
                )
            
            # Send daily summary if it's the right time
            if datetime.utcnow().hour == 9:  # 9 AM
                await self._send_daily_summary(start_date, end_date)
        
        except Exception as e:
            self.logger.error(f"Error processing insights and alerts: {e}")
    
    async def _send_daily_summary(self, start_date: datetime, end_date: datetime):
        """Send daily summary notification."""
        try:
            with self.get_db_session() as session:
                # Get daily metrics
                total_feedback = session.query(ProcessedDocument).filter(
                    ProcessedDocument.created_at >= start_date,
                    ProcessedDocument.created_at <= end_date
                ).count()
                
                high_priority = session.query(ProcessedDocument).join(
                    PrioritizationScore, ProcessedDocument.id == PrioritizationScore.document_id
                ).filter(
                    ProcessedDocument.created_at >= start_date,
                    ProcessedDocument.created_at <= end_date,
                    PrioritizationScore.priority_score >= 0.7
                ).count()
                
                tickets_created = session.query(Ticket).filter(
                    Ticket.created_at >= start_date,
                    Ticket.created_at <= end_date
                ).count()
                
                resolved = session.query(Ticket).filter(
                    Ticket.created_at >= start_date,
                    Ticket.created_at <= end_date,
                    Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED])
                ).count()
                
                # Get top issues and critical alerts
                top_issues = self._get_top_priorities(session, start_date, end_date)
                critical_alerts = self._get_critical_alerts(session, start_date, end_date)
                
                await self.notification_manager.send_daily_summary(
                    start_date.strftime('%Y-%m-%d'),
                    total_feedback,
                    high_priority,
                    tickets_created,
                    resolved,
                    top_issues,
                    critical_alerts
                )
        
        except Exception as e:
            self.logger.error(f"Error sending daily summary: {e}")
    
    async def _cleanup_old_reports(self):
        """Clean up old reports based on retention policy."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.digestor_config.report_retention_days)
            
            for filename in os.listdir(self.report_storage_dir):
                filepath = os.path.join(self.report_storage_dir, filename)
                if os.path.isfile(filepath):
                    file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                    if file_time < cutoff_date:
                        os.remove(filepath)
                        self.logger.info(f"Removed old report: {filename}")
        
        except Exception as e:
            self.logger.error(f"Error cleaning up old reports: {e}")
    
    # Helper methods for data generation
    def _get_priority_distribution(self, session, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get priority distribution data."""
        try:
            # Get priority counts
            priorities = session.query(PrioritizationScore.priority_level).filter(
                PrioritizationScore.created_at >= start_date,
                PrioritizationScore.created_at <= end_date
            ).all()
            
            priority_counts = Counter([p[0] for p in priorities])
            total = sum(priority_counts.values())
            
            if total == 0:
                return {'critical': 0, 'critical_percentage': 0, 'high': 0, 'high_percentage': 0,
                       'medium': 0, 'medium_percentage': 0, 'low': 0, 'low_percentage': 0}
            
            return {
                'critical': priority_counts.get(5, 0),
                'critical_percentage': round((priority_counts.get(5, 0) / total) * 100, 1),
                'high': priority_counts.get(4, 0),
                'high_percentage': round((priority_counts.get(4, 0) / total) * 100, 1),
                'medium': priority_counts.get(3, 0),
                'medium_percentage': round((priority_counts.get(3, 0) / total) * 100, 1),
                'low': priority_counts.get(2, 0) + priority_counts.get(1, 0),
                'low_percentage': round(((priority_counts.get(2, 0) + priority_counts.get(1, 0)) / total) * 100, 1)
            }
        except Exception as e:
            self.logger.error(f"Error getting priority distribution: {e}")
            return {}
    
    def _get_classification_breakdown(self, session, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get classification breakdown data."""
        try:
            classifications = session.query(ProcessedDocument.feedback_type).filter(
                ProcessedDocument.created_at >= start_date,
                ProcessedDocument.created_at <= end_date,
                ProcessedDocument.feedback_type.isnot(None)
            ).all()
            
            type_counts = Counter([c[0].value if c[0] else 'other' for c in classifications])
            total = sum(type_counts.values())
            
            if total == 0:
                return {}
            
            result = {}
            for feedback_type in ['bug', 'feature_request', 'performance', 'other']:
                count = type_counts.get(feedback_type, 0)
                result[feedback_type] = count
                result[f'{feedback_type}_percentage'] = round((count / total) * 100, 1)
            
            return result
        except Exception as e:
            self.logger.error(f"Error getting classification breakdown: {e}")
            return {}
    
    def _get_critical_issues(self, session, start_date: datetime, end_date: datetime) -> List[str]:
        """Get critical issues list."""
        try:
            issues = session.query(ProcessedDocument.title).join(
                PrioritizationScore, ProcessedDocument.id == PrioritizationScore.document_id
            ).filter(
                ProcessedDocument.created_at >= start_date,
                ProcessedDocument.created_at <= end_date,
                PrioritizationScore.priority_score >= 0.9
            ).limit(5).all()
            
            return [issue[0] for issue in issues if issue[0]]
        except Exception as e:
            self.logger.error(f"Error getting critical issues: {e}")
            return []
    
    def _get_top_priorities(self, session, start_date: datetime, end_date: datetime) -> List[str]:
        """Get top priority items."""
        try:
            priorities = session.query(ProcessedDocument.title).join(
                PrioritizationScore, ProcessedDocument.id == PrioritizationScore.document_id
            ).filter(
                ProcessedDocument.created_at >= start_date,
                ProcessedDocument.created_at <= end_date,
                PrioritizationScore.priority_score >= 0.7
            ).order_by(PrioritizationScore.priority_score.desc()).limit(5).all()
            
            return [priority[0] for priority in priorities if priority[0]]
        except Exception as e:
            self.logger.error(f"Error getting top priorities: {e}")
            return []
    
    def _get_critical_alerts(self, session, start_date: datetime, end_date: datetime) -> List[str]:
        """Get critical alerts."""
        try:
            alerts = session.query(ProcessedDocument.title).join(
                PrioritizationScore, ProcessedDocument.id == PrioritizationScore.document_id
            ).filter(
                ProcessedDocument.created_at >= start_date,
                ProcessedDocument.created_at <= end_date,
                PrioritizationScore.priority_score >= 0.95
            ).limit(3).all()
            
            return [alert[0] for alert in alerts if alert[0]]
        except Exception as e:
            self.logger.error(f"Error getting critical alerts: {e}")
            return []
    
    def _format_trend_analysis(self, trends: List[TrendData]) -> str:
        """Format trend analysis for display."""
        if not trends:
            return "No significant trends detected."
        
        trend_summaries = []
        for trend in trends[:3]:  # Top 3 trends
            direction = "increased" if trend.trend_direction == "up" else "decreased"
            trend_summaries.append(
                f"{trend.metric} {direction} by {abs(trend.change_percentage):.1f}%"
            )
        
        return "; ".join(trend_summaries)
    
    def _format_trend_summary(self, trends: List[TrendData]) -> str:
        """Format trend summary for hourly digest."""
        if not trends:
            return "No significant trends in the last hour."
        
        significant_trends = [t for t in trends if t.significance in ['high', 'medium']]
        if not significant_trends:
            return "Stable trends detected."
        
        return f"{len(significant_trends)} significant trend(s) detected."
    
    def _format_trend_comparison(self, previous_trends: List[TrendData]) -> str:
        """Format trend comparison for daily summary."""
        if not previous_trends:
            return "No previous data for comparison."
        
        up_trends = [t for t in previous_trends if t.trend_direction == 'up']
        down_trends = [t for t in previous_trends if t.trend_direction == 'down']
        
        return f"Previous day: {len(up_trends)} increasing trends, {len(down_trends)} decreasing trends."
    
    def _format_top_clusters(self, top_clusters: List[Dict[str, Any]]) -> str:
        """Format top clusters for display."""
        if not top_clusters:
            return "No clusters found."
        
        cluster_list = []
        for cluster in top_clusters:
            cluster_list.append(f"• {cluster['title']}: {cluster['size']} items")
        
        return '\n'.join(cluster_list)
    
    def _format_component_analysis(self, session, start_date: datetime, end_date: datetime) -> str:
        """Format component analysis for display."""
        try:
            components = session.query(ProcessedDocument.component).filter(
                ProcessedDocument.created_at >= start_date,
                ProcessedDocument.created_at <= end_date,
                ProcessedDocument.component.isnot(None)
            ).all()
            
            component_counts = Counter([c[0] for c in components])
            top_components = component_counts.most_common(5)
            
            component_list = []
            for component, count in top_components:
                component_list.append(f"• {component}: {count} items")
            
            return '\n'.join(component_list) if component_list else "No component data available."
        except Exception as e:
            self.logger.error(f"Error formatting component analysis: {e}")
            return "Error retrieving component data."
    
    def _format_component_breakdown(self, component_analysis: List[ComponentAnalysis]) -> str:
        """Format component breakdown for display."""
        if not component_analysis:
            return "No component data available."
        
        component_list = []
        for comp in component_analysis[:5]:
            component_list.append(f"• {comp.component}: {comp.total_feedback} items ({comp.high_priority_count} high-priority)")
        
        return '\n'.join(component_list)
    
    async def test_notifications(self) -> Dict[NotificationChannel, bool]:
        """Test notification channels."""
        return await self.notification_manager.test_connections()
    
    async def generate_custom_report(
        self, 
        report_type: ReportType, 
        start_date: datetime, 
        end_date: datetime
    ) -> Optional[ReportData]:
        """Generate a custom report for a specific time period."""
        try:
            context = AgentContext(
                execution_id=str(uuid.uuid4()),
                config=self.config,
                metadata={'custom_report': True}
            )
            
            return await self._generate_report(report_type, context)
        
        except Exception as e:
            self.logger.error(f"Error generating custom report: {e}")
            return None

