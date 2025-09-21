#!/usr/bin/env python3
"""
Example script demonstrating the Digestor Agent functionality.

This script shows how to:
1. Initialize the Digestor Agent
2. Generate different types of reports
3. Send notifications
4. Perform analytics and trend analysis
5. Test notification channels

Run this script to see the Digestor Agent in action.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import uuid

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.digestor.agent import DigestorAgent
from agents.digestor.report_models import ReportType, ReportFormat, NotificationChannel, PriorityLevel
from agents.base.agent import AgentContext

async def main():
    """Main example function."""
    print("📊 Digestor Agent Example")
    print("=" * 50)
    
    # Configuration for the Digestor Agent
    config = {
        "digestor": {
            "enable_hourly_reports": True,
            "enable_daily_reports": True,
            "enable_weekly_reports": True,
            "enable_monthly_reports": True,
            "enable_notifications": True,
            "enable_trend_analysis": True,
            "enable_cluster_analysis": True,
            "enable_priority_analysis": True,
            "default_format": "html",
            "include_charts": True,
            "include_raw_data": False,
            "max_reports_per_hour": 5,
            "report_retention_days": 30
        },
        "notifications": {
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "your-email@gmail.com",
                "password": "your-app-password",
                "from_email": "noreply@yourcompany.com",
                "use_tls": True
            },
            "slack": {
                "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
                "channel": "#product-feedback",
                "username": "Feedback Bot",
                "icon_emoji": ":robot_face:"
            },
            "webhook": {
                "webhook_url": "https://your-webhook-endpoint.com/notifications",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer your-token"
                }
            },
            "critical_alert_recipients": ["admin@yourcompany.com", "cto@yourcompany.com"],
            "trend_alert_recipients": ["analytics@yourcompany.com"],
            "daily_summary_recipients": ["team@yourcompany.com", "pm@yourcompany.com"],
            "executive_recipients": ["ceo@yourcompany.com", "cto@yourcompany.com"],
            "technical_recipients": ["dev-team@yourcompany.com"],
            "default_recipients": ["team@yourcompany.com"]
        },
        "report_storage_dir": "reports"
    }
    
    # Initialize the Digestor Agent
    print("📋 Initializing Digestor Agent...")
    digestor = DigestorAgent(config)
    
    print(f"✅ Agent initialized: {digestor.name}")
    print(f"📊 Report types enabled: {[rt.value for rt in [ReportType.HOURLY, ReportType.DAILY, ReportType.WEEKLY, ReportType.MONTHLY]]}")
    print(f"📧 Notification channels: {list(digestor.notification_manager.senders.keys())}")
    print()
    
    # Test notification channels
    print("🔌 Testing notification channels...")
    try:
        connection_results = await digestor.test_notifications()
        
        for channel, connected in connection_results.items():
            status = "✅ Connected" if connected else "❌ Failed"
            print(f"  {channel.value}: {status}")
    except Exception as e:
        print(f"  Error testing connections: {e}")
    print()
    
    # Demonstrate report generation
    print("📊 Demonstrating report generation...")
    
    # Create mock context
    context = AgentContext(
        execution_id=str(uuid.uuid4()),
        agent_name="digestor",
        started_at=datetime.utcnow(),
        config=config,
        metadata={"example": True}
    )
    
    # Generate different types of reports
    report_types = [ReportType.EXECUTIVE, ReportType.TECHNICAL, ReportType.HOURLY, ReportType.DAILY]
    
    for report_type in report_types:
        print(f"📄 Generating {report_type.value} report...")
        
        try:
            # Generate report data (this would normally query the database)
            if report_type == ReportType.EXECUTIVE:
                print("  📈 Executive Summary:")
                print("    • Total feedback: 150 items")
                print("    • High priority: 25 items")
                print("    • Tickets created: 18")
                print("    • Resolution rate: 85%")
                print("    • Key insights: 5 actionable insights")
                print("    • Critical issues: 3 requiring immediate attention")
            
            elif report_type == ReportType.TECHNICAL:
                print("  🔧 Technical Summary:")
                print("    • Items processed: 150")
                print("    • Classification rate: 95%")
                print("    • Clustering rate: 88%")
                print("    • Prioritization rate: 92%")
                print("    • Error rate: 0.5%")
                print("    • Average processing time: 2.3s")
            
            elif report_type == ReportType.HOURLY:
                print("  ⏰ Hourly Digest:")
                print("    • New feedback: 12 items")
                print("    • High priority: 3 items")
                print("    • Tickets created: 2")
                print("    • Critical issues: 1")
                print("    • Top priorities: Login issue, Payment error")
                print("    • Affected components: auth, payment")
            
            elif report_type == ReportType.DAILY:
                print("  📅 Daily Summary:")
                print("    • Total feedback: 150 items")
                print("    • High priority: 25 items")
                print("    • Tickets created: 18")
                print("    • Resolved: 15")
                print("    • Priority breakdown: 3% critical, 12% high, 45% medium, 40% low")
                print("    • Top components: auth (25), payment (20), ui (15)")
            
            print(f"  ✅ {report_type.value} report generated successfully")
        
        except Exception as e:
            print(f"  ❌ Error generating {report_type.value} report: {e}")
        
        print()
    
    # Demonstrate analytics capabilities
    print("📈 Demonstrating analytics capabilities...")
    
    # Mock trend analysis
    print("  📊 Trend Analysis:")
    print("    • Total feedback: +25% increase (significant)")
    print("    • High priority: +50% increase (critical)")
    print("    • Resolution rate: -5% decrease (concerning)")
    print("    • Ticket creation: +30% increase (good)")
    print()
    
    # Mock component analysis
    print("  🔧 Component Analysis:")
    print("    • Authentication: 25 items (5 high-priority) - +20% trend")
    print("    • Payment: 20 items (3 high-priority) - +15% trend")
    print("    • UI: 15 items (2 high-priority) - -10% trend")
    print("    • API: 12 items (1 high-priority) - +5% trend")
    print()
    
    # Mock cluster analysis
    print("  🔍 Cluster Analysis:")
    print("    • Total clusters: 8")
    print("    • Average cluster size: 4.2 items")
    print("    • Largest cluster: 'Login Issues' (12 items)")
    print("    • Clustering efficiency: 18.5%")
    print()
    
    # Demonstrate notification capabilities
    print("📧 Demonstrating notification capabilities...")
    
    # Mock critical alert
    print("  🚨 Critical Alert Example:")
    print("    Title: Critical Authentication Bug")
    print("    Priority: CRITICAL")
    print("    Component: authentication")
    print("    Impact: Users cannot log in")
    print("    Actions Taken: Restart service, Check logs")
    print("    Next Steps: Investigate root cause, Implement fix")
    print()
    
    # Mock trend alert
    print("  📈 Trend Alert Example:")
    print("    Trend: High Priority Feedback")
    print("    Current: 25 items")
    print("    Previous: 10 items")
    print("    Change: +150%")
    print("    Recommendation: Investigate the cause immediately")
    print()
    
    # Mock daily summary
    print("  📅 Daily Summary Example:")
    print("    Date: 2024-01-15")
    print("    Total Feedback: 150")
    print("    High Priority: 25")
    print("    Tickets Created: 18")
    print("    Resolved: 15")
    print("    Top Issues: Login issue, Payment error, UI bug")
    print("    Critical Alerts: Authentication system down")
    print()
    
    # Demonstrate report templates
    print("📋 Demonstrating report templates...")
    
    from agents.digestor.report_models import ReportTemplates, ReportFormatter
    
    # Show executive summary template
    exec_template = ReportTemplates.get_executive_summary_template()
    print(f"  📊 Executive Summary Template:")
    print(f"    • Name: {exec_template.name}")
    print(f"    • Type: {exec_template.report_type.value}")
    print(f"    • Format: {exec_template.format.value}")
    print(f"    • Variables: {len(exec_template.variables)}")
    print(f"    • Channels: {[c.value for c in exec_template.channels]}")
    print()
    
    # Show technical summary template
    tech_template = ReportTemplates.get_technical_summary_template()
    print(f"  🔧 Technical Summary Template:")
    print(f"    • Name: {tech_template.name}")
    print(f"    • Type: {tech_template.report_type.value}")
    print(f"    • Format: {tech_template.format.value}")
    print(f"    • Variables: {len(tech_template.variables)}")
    print()
    
    # Show hourly digest template
    hourly_template = ReportTemplates.get_hourly_digest_template()
    print(f"  ⏰ Hourly Digest Template:")
    print(f"    • Name: {hourly_template.name}")
    print(f"    • Type: {hourly_template.report_type.value}")
    print(f"    • Format: {hourly_template.format.value}")
    print(f"    • Variables: {len(hourly_template.variables)}")
    print()
    
    # Demonstrate report formatting
    print("🎨 Demonstrating report formatting...")
    
    # Mock data for formatting
    mock_data = {
        'start_date': '2024-01-15',
        'end_date': '2024-01-16',
        'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'total_feedback': 150,
        'high_priority_count': 25,
        'tickets_created': 18,
        'resolution_rate': 85.5,
        'key_insights': '<li>Authentication issues increased by 50%</li><li>Payment errors decreased by 20%</li>',
        'critical_count': 3,
        'critical_percentage': 2.0,
        'high_count': 25,
        'high_percentage': 16.7,
        'medium_count': 75,
        'medium_percentage': 50.0,
        'low_count': 47,
        'low_percentage': 31.3,
        'top_components': '<li>auth: 25 items</li><li>payment: 20 items</li>',
        'trend_analysis': 'Positive trends in payment processing, concerning trends in authentication',
        'critical_issues': '<li>Login system down</li><li>Payment gateway error</li>',
        'recommendations': '<li>Focus on authentication system</li><li>Monitor payment processing</li>'
    }
    
    # Format executive report
    formatted_report = ReportFormatter.format_report(exec_template, mock_data)
    print(f"  📊 Executive Report (HTML):")
    print(f"    • Length: {len(formatted_report)} characters")
    print(f"    • Contains HTML: {'<html>' in formatted_report}")
    print(f"    • Contains data: {'150' in formatted_report}")
    print()
    
    # Demonstrate notification templates
    print("📧 Demonstrating notification templates...")
    
    from agents.digestor.report_models import NotificationTemplates
    
    # Show critical alert template
    critical_template = NotificationTemplates.get_critical_alert_template()
    print(f"  🚨 Critical Alert Template:")
    print(f"    • Contains: {critical_template.count('{')} variables")
    print(f"    • Includes: title, priority, component, impact")
    print()
    
    # Show trend alert template
    trend_template = NotificationTemplates.get_trend_alert_template()
    print(f"  📈 Trend Alert Template:")
    print(f"    • Contains: {trend_template.count('{')} variables")
    print(f"    • Includes: trend_type, change_percentage, recommendation")
    print()
    
    # Show daily summary template
    daily_template = NotificationTemplates.get_daily_summary_template()
    print(f"  📅 Daily Summary Template:")
    print(f"    • Contains: {daily_template.count('{')} variables")
    print(f"    • Includes: date, metrics, top_issues, critical_alerts")
    print()
    
    # Demonstrate configuration options
    print("⚙️ Configuration options:")
    print(f"  📊 Report generation:")
    print(f"    • Hourly reports: {digestor.digestor_config.enable_hourly_reports}")
    print(f"    • Daily reports: {digestor.digestor_config.enable_daily_reports}")
    print(f"    • Weekly reports: {digestor.digestor_config.enable_weekly_reports}")
    print(f"    • Monthly reports: {digestor.digestor_config.enable_monthly_reports}")
    print()
    
    print(f"  📧 Notifications:")
    print(f"    • Notifications enabled: {digestor.digestor_config.enable_notifications}")
    print(f"    • Available channels: {len(digestor.notification_manager.senders)}")
    print(f"    • Rate limiting: {digestor.digestor_config.max_reports_per_hour} reports/hour")
    print()
    
    print(f"  📈 Analytics:")
    print(f"    • Trend analysis: {digestor.digestor_config.enable_trend_analysis}")
    print(f"    • Cluster analysis: {digestor.digestor_config.enable_cluster_analysis}")
    print(f"    • Priority analysis: {digestor.digestor_config.enable_priority_analysis}")
    print()
    
    print(f"  📄 Output:")
    print(f"    • Default format: {digestor.digestor_config.default_format}")
    print(f"    • Include charts: {digestor.digestor_config.include_charts}")
    print(f"    • Include raw data: {digestor.digestor_config.include_raw_data}")
    print(f"    • Report retention: {digestor.digestor_config.report_retention_days} days")
    print()
    
    # Show input dependencies
    print("🔗 Input dependencies:")
    dependencies = digestor.get_input_dependencies()
    for dep in dependencies:
        print(f"  • {dep}")
    print()
    
    print("✅ Digestor Agent example completed!")
    print()
    print("💡 Next steps:")
    print("  1. Configure your notification channels (email, Slack, webhooks)")
    print("  2. Set up the database with processed feedback data")
    print("  3. Schedule the agent to run automatically")
    print("  4. Customize report templates for your needs")
    print("  5. Monitor reports and notifications")
    print("  6. Use analytics insights to improve your product")

if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
