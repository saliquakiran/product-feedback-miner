"""
Analytics engine for the Digestor Agent.

This module provides trend analysis, statistical calculations,
and insights generation for feedback data.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics
from collections import Counter, defaultdict

from database.models import (
    ProcessedDocument, PrioritizationScore, Cluster, Ticket,
    FeedbackType, PriorityLevel, TicketStatus
)
from database import get_session

logger = logging.getLogger(__name__)

@dataclass
class TrendData:
    """Data structure for trend analysis."""
    metric: str
    current_value: float
    previous_value: float
    change_percentage: float
    trend_direction: str  # 'up', 'down', 'stable'
    significance: str  # 'high', 'medium', 'low'
    description: str

@dataclass
class ComponentAnalysis:
    """Analysis data for a specific component."""
    component: str
    total_feedback: int
    high_priority_count: int
    avg_priority_score: float
    trend: TrendData
    top_issues: List[str]
    resolution_rate: float

@dataclass
class ClusterAnalysis:
    """Analysis data for clusters."""
    total_clusters: int
    avg_cluster_size: float
    largest_cluster: Dict[str, Any]
    top_clusters: List[Dict[str, Any]]
    clustering_efficiency: float

class FeedbackAnalytics:
    """Analytics engine for feedback data."""
    
    def __init__(self):
        """Initialize analytics engine."""
        self.logger = logging.getLogger(__name__)
    
    def analyze_trends(
        self, 
        start_date: datetime, 
        end_date: datetime,
        comparison_period_days: int = 7
    ) -> List[TrendData]:
        """
        Analyze trends in feedback data.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            comparison_period_days: Days to compare against
            
        Returns:
            List of trend data
        """
        try:
            trends = []
            
            # Calculate comparison period
            comparison_start = start_date - timedelta(days=comparison_period_days)
            comparison_end = start_date
            
            with get_session() as session:
                # Total feedback trend
                current_count = self._get_feedback_count(session, start_date, end_date)
                previous_count = self._get_feedback_count(session, comparison_start, comparison_end)
                
                trends.append(self._calculate_trend(
                    "Total Feedback",
                    current_count,
                    previous_count,
                    "Number of feedback items received"
                ))
                
                # High priority trend
                current_high = self._get_high_priority_count(session, start_date, end_date)
                previous_high = self._get_high_priority_count(session, comparison_start, comparison_end)
                
                trends.append(self._calculate_trend(
                    "High Priority Feedback",
                    current_high,
                    previous_high,
                    "Number of high-priority feedback items"
                ))
                
                # Ticket creation trend
                current_tickets = self._get_ticket_count(session, start_date, end_date)
                previous_tickets = self._get_ticket_count(session, comparison_start, comparison_end)
                
                trends.append(self._calculate_trend(
                    "Tickets Created",
                    current_tickets,
                    previous_tickets,
                    "Number of tickets created from feedback"
                ))
                
                # Resolution rate trend
                current_resolution = self._get_resolution_rate(session, start_date, end_date)
                previous_resolution = self._get_resolution_rate(session, comparison_start, comparison_end)
                
                trends.append(self._calculate_trend(
                    "Resolution Rate",
                    current_resolution,
                    previous_resolution,
                    "Percentage of tickets resolved"
                ))
                
                # Component trend analysis
                component_trends = self._analyze_component_trends(
                    session, start_date, end_date, comparison_start, comparison_end
                )
                trends.extend(component_trends)
            
            return trends
        
        except Exception as e:
            self.logger.error(f"Error analyzing trends: {e}")
            return []
    
    def analyze_components(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[ComponentAnalysis]:
        """
        Analyze feedback by component.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            List of component analysis data
        """
        try:
            components = []
            
            with get_session() as session:
                # Get component data
                component_data = self._get_component_data(session, start_date, end_date)
                
                for component, data in component_data.items():
                    # Calculate trend for this component
                    comparison_start = start_date - timedelta(days=7)
                    comparison_end = start_date
                    comparison_data = self._get_component_data(
                        session, comparison_start, comparison_end
                    )
                    
                    previous_count = comparison_data.get(component, {}).get('count', 0)
                    current_count = data['count']
                    
                    trend = self._calculate_trend(
                        f"{component} Feedback",
                        current_count,
                        previous_count,
                        f"Number of feedback items for {component}"
                    )
                    
                    # Get top issues for this component
                    top_issues = self._get_component_top_issues(session, component, start_date, end_date)
                    
                    # Calculate resolution rate
                    resolution_rate = self._get_component_resolution_rate(
                        session, component, start_date, end_date
                    )
                    
                    analysis = ComponentAnalysis(
                        component=component,
                        total_feedback=data['count'],
                        high_priority_count=data['high_priority'],
                        avg_priority_score=data['avg_priority'],
                        trend=trend,
                        top_issues=top_issues,
                        resolution_rate=resolution_rate
                    )
                    
                    components.append(analysis)
            
            # Sort by total feedback count
            components.sort(key=lambda x: x.total_feedback, reverse=True)
            
            return components
        
        except Exception as e:
            self.logger.error(f"Error analyzing components: {e}")
            return []
    
    def analyze_clusters(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> ClusterAnalysis:
        """
        Analyze clustering effectiveness.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            Cluster analysis data
        """
        try:
            with get_session() as session:
                # Get cluster data
                clusters = session.query(Cluster).filter(
                    Cluster.created_at >= start_date,
                    Cluster.created_at <= end_date
                ).all()
                
                if not clusters:
                    return ClusterAnalysis(
                        total_clusters=0,
                        avg_cluster_size=0,
                        largest_cluster={},
                        top_clusters=[],
                        clustering_efficiency=0
                    )
                
                # Calculate metrics
                cluster_sizes = [cluster.member_count for cluster in clusters]
                avg_cluster_size = statistics.mean(cluster_sizes)
                
                # Find largest cluster
                largest_cluster = max(clusters, key=lambda x: x.member_count)
                largest_cluster_data = {
                    'id': str(largest_cluster.id),
                    'title': largest_cluster.title,
                    'size': largest_cluster.member_count,
                    'avg_severity': largest_cluster.avg_severity
                }
                
                # Get top clusters by size
                top_clusters = sorted(
                    clusters, 
                    key=lambda x: x.member_count, 
                    reverse=True
                )[:5]
                
                top_clusters_data = [
                    {
                        'id': str(cluster.id),
                        'title': cluster.title,
                        'size': cluster.member_count,
                        'avg_severity': cluster.avg_severity,
                        'component': cluster.component
                    }
                    for cluster in top_clusters
                ]
                
                # Calculate clustering efficiency
                total_feedback = sum(cluster_sizes)
                clustering_efficiency = (len(clusters) / total_feedback) * 100 if total_feedback > 0 else 0
                
                return ClusterAnalysis(
                    total_clusters=len(clusters),
                    avg_cluster_size=avg_cluster_size,
                    largest_cluster=largest_cluster_data,
                    top_clusters=top_clusters_data,
                    clustering_efficiency=clustering_efficiency
                )
        
        except Exception as e:
            self.logger.error(f"Error analyzing clusters: {e}")
            return ClusterAnalysis(
                total_clusters=0,
                avg_cluster_size=0,
                largest_cluster={},
                top_clusters=[],
                clustering_efficiency=0
            )
    
    def generate_insights(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[str]:
        """
        Generate actionable insights from feedback data.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            
        Returns:
            List of insight strings
        """
        try:
            insights = []
            
            # Analyze trends
            trends = self.analyze_trends(start_date, end_date)
            
            # Generate insights from trends
            for trend in trends:
                if trend.significance == 'high':
                    if trend.trend_direction == 'up':
                        insights.append(
                            f"🚨 {trend.metric} has increased significantly by "
                            f"{abs(trend.change_percentage):.1f}% - requires immediate attention"
                        )
                    elif trend.trend_direction == 'down':
                        insights.append(
                            f"✅ {trend.metric} has decreased by "
                            f"{abs(trend.change_percentage):.1f}% - positive trend"
                        )
            
            # Analyze components
            components = self.analyze_components(start_date, end_date)
            
            # Generate component insights
            if components:
                top_component = components[0]
                if top_component.total_feedback > 10:  # Threshold for significance
                    insights.append(
                        f"🔧 {top_component.component} is the most affected component "
                        f"with {top_component.total_feedback} feedback items"
                    )
                
                # Check for components with high priority issues
                high_priority_components = [
                    c for c in components 
                    if c.high_priority_count > 5 and c.total_feedback > 10
                ]
                
                if high_priority_components:
                    insights.append(
                        f"⚠️ {len(high_priority_components)} components have high priority issues "
                        f"requiring immediate attention"
                    )
            
            # Analyze clusters
            cluster_analysis = self.analyze_clusters(start_date, end_date)
            
            if cluster_analysis.total_clusters > 0:
                if cluster_analysis.avg_cluster_size > 5:
                    insights.append(
                        f"📊 Average cluster size is {cluster_analysis.avg_cluster_size:.1f} - "
                        f"good clustering efficiency"
                    )
                
                if cluster_analysis.largest_cluster['size'] > 10:
                    insights.append(
                        f"🔍 Large cluster detected: {cluster_analysis.largest_cluster['title']} "
                        f"with {cluster_analysis.largest_cluster['size']} items - "
                        f"consider breaking down into sub-issues"
                    )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(trends, components, cluster_analysis)
            insights.extend(recommendations)
            
            return insights
        
        except Exception as e:
            self.logger.error(f"Error generating insights: {e}")
            return ["Error generating insights - check system logs"]
    
    def _get_feedback_count(self, session, start_date: datetime, end_date: datetime) -> int:
        """Get total feedback count for period."""
        return session.query(ProcessedDocument).filter(
            ProcessedDocument.created_at >= start_date,
            ProcessedDocument.created_at <= end_date
        ).count()
    
    def _get_high_priority_count(self, session, start_date: datetime, end_date: datetime) -> int:
        """Get high priority feedback count for period."""
        return session.query(ProcessedDocument).join(
            PrioritizationScore, ProcessedDocument.id == PrioritizationScore.document_id
        ).filter(
            ProcessedDocument.created_at >= start_date,
            ProcessedDocument.created_at <= end_date,
            PrioritizationScore.priority_score >= 0.7
        ).count()
    
    def _get_ticket_count(self, session, start_date: datetime, end_date: datetime) -> int:
        """Get ticket count for period."""
        return session.query(Ticket).filter(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date
        ).count()
    
    def _get_resolution_rate(self, session, start_date: datetime, end_date: datetime) -> float:
        """Get resolution rate for period."""
        total_tickets = session.query(Ticket).filter(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date
        ).count()
        
        if total_tickets == 0:
            return 0.0
        
        resolved_tickets = session.query(Ticket).filter(
            Ticket.created_at >= start_date,
            Ticket.created_at <= end_date,
            Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED])
        ).count()
        
        return (resolved_tickets / total_tickets) * 100
    
    def _get_component_data(self, session, start_date: datetime, end_date: datetime) -> Dict[str, Dict[str, Any]]:
        """Get component analysis data."""
        components = {}
        
        # Get feedback by component
        feedback_by_component = session.query(
            ProcessedDocument.component,
            ProcessedDocument.id
        ).filter(
            ProcessedDocument.created_at >= start_date,
            ProcessedDocument.created_at <= end_date,
            ProcessedDocument.component.isnot(None)
        ).all()
        
        for component, doc_id in feedback_by_component:
            if component not in components:
                components[component] = {
                    'count': 0,
                    'high_priority': 0,
                    'priority_scores': []
                }
            
            components[component]['count'] += 1
            
            # Get priority score
            priority_score = session.query(PrioritizationScore).filter(
                PrioritizationScore.document_id == doc_id
            ).first()
            
            if priority_score:
                components[component]['priority_scores'].append(priority_score.priority_score)
                if priority_score.priority_score >= 0.7:
                    components[component]['high_priority'] += 1
        
        # Calculate averages
        for component in components:
            scores = components[component]['priority_scores']
            components[component]['avg_priority'] = statistics.mean(scores) if scores else 0
        
        return components
    
    def _get_component_top_issues(self, session, component: str, start_date: datetime, end_date: datetime) -> List[str]:
        """Get top issues for a component."""
        issues = session.query(ProcessedDocument.title).filter(
            ProcessedDocument.component == component,
            ProcessedDocument.created_at >= start_date,
            ProcessedDocument.created_at <= end_date
        ).limit(5).all()
        
        return [issue[0] for issue in issues if issue[0]]
    
    def _get_component_resolution_rate(self, session, component: str, start_date: datetime, end_date: datetime) -> float:
        """Get resolution rate for a component."""
        # This would need to be implemented based on how tickets are linked to components
        # For now, return a placeholder
        return 0.0
    
    def _analyze_component_trends(
        self, 
        session, 
        start_date: datetime, 
        end_date: datetime,
        comparison_start: datetime,
        comparison_end: datetime
    ) -> List[TrendData]:
        """Analyze trends for individual components."""
        trends = []
        
        current_components = self._get_component_data(session, start_date, end_date)
        previous_components = self._get_component_data(session, comparison_start, comparison_end)
        
        for component in current_components:
            current_count = current_components[component]['count']
            previous_count = previous_components.get(component, {}).get('count', 0)
            
            if previous_count > 0:  # Only analyze components with previous data
                trend = self._calculate_trend(
                    f"{component} Feedback",
                    current_count,
                    previous_count,
                    f"Number of feedback items for {component}"
                )
                trends.append(trend)
        
        return trends
    
    def _calculate_trend(
        self, 
        metric: str, 
        current: float, 
        previous: float, 
        description: str
    ) -> TrendData:
        """Calculate trend data for a metric."""
        if previous == 0:
            change_percentage = 100.0 if current > 0 else 0.0
        else:
            change_percentage = ((current - previous) / previous) * 100
        
        # Determine trend direction
        if abs(change_percentage) < 5:
            trend_direction = 'stable'
        elif change_percentage > 0:
            trend_direction = 'up'
        else:
            trend_direction = 'down'
        
        # Determine significance
        if abs(change_percentage) >= 50:
            significance = 'high'
        elif abs(change_percentage) >= 20:
            significance = 'medium'
        else:
            significance = 'low'
        
        return TrendData(
            metric=metric,
            current_value=current,
            previous_value=previous,
            change_percentage=change_percentage,
            trend_direction=trend_direction,
            significance=significance,
            description=description
        )
    
    def _generate_recommendations(
        self, 
        trends: List[TrendData], 
        components: List[ComponentAnalysis],
        cluster_analysis: ClusterAnalysis
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Trend-based recommendations
        high_priority_trends = [t for t in trends if t.significance == 'high' and t.trend_direction == 'up']
        if high_priority_trends:
            recommendations.append(
                "🚨 High priority feedback is increasing - consider increasing development resources"
            )
        
        # Component-based recommendations
        if components:
            top_component = components[0]
            if top_component.high_priority_count > 10:
                recommendations.append(
                    f"🔧 Focus on {top_component.component} - has {top_component.high_priority_count} "
                    f"high-priority issues"
                )
        
        # Cluster-based recommendations
        if cluster_analysis.avg_cluster_size > 8:
            recommendations.append(
                "🔍 Large clusters detected - consider breaking down into smaller, more specific issues"
            )
        
        if cluster_analysis.clustering_efficiency < 10:
            recommendations.append(
                "📊 Low clustering efficiency - review clustering parameters and feedback quality"
            )
        
        return recommendations

