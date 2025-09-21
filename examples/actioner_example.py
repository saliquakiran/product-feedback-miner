#!/usr/bin/env python3
"""
Example script demonstrating the Actioner Agent functionality.

This script shows how to:
1. Initialize the Actioner Agent
2. Create tickets from high-priority feedback
3. Test platform connections
4. Get ticket statistics
5. Update ticket status

Run this script to see the Actioner Agent in action.
"""

import asyncio
import sys
import os
from datetime import datetime
import uuid

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.actioner.agent import ActionerAgent
from agents.actioner.ticket_models import PlatformType, TicketStatus
from database.models import FeedbackType, SourceType, ProcessingStatus, PriorityLevel

async def main():
    """Main example function."""
    print("🚀 Actioner Agent Example")
    print("=" * 50)
    
    # Configuration for the Actioner Agent
    config = {
        "actioner": {
            "priority_threshold": 0.7,
            "max_tickets_per_hour": 10,
            "max_tickets_per_day": 50,
            "enable_jira": True,
            "enable_github": True,
            "auto_assign": True,
            "require_approval": False
        },
        "jira": {
            "base_url": "https://your-company.atlassian.net",
            "username": "your-email@example.com",
            "api_token": "your-jira-api-token"
        },
        "github": {
            "token": "your-github-token",
            "owner": "your-org",
            "repo": "your-repo"
        }
    }
    
    # Initialize the Actioner Agent
    print("📋 Initializing Actioner Agent...")
    actioner = ActionerAgent(config)
    
    print(f"✅ Agent initialized: {actioner.name}")
    print(f"📊 Priority threshold: {actioner.actioner_config.priority_threshold}")
    print(f"🔧 Available platforms: {list(actioner.platform_managers.keys())}")
    print()
    
    # Test platform connections
    print("🔌 Testing platform connections...")
    connection_results = await actioner.test_platform_connections()
    
    for platform, connected in connection_results.items():
        status = "✅ Connected" if connected else "❌ Failed"
        print(f"  {platform}: {status}")
    print()
    
    # Demonstrate ticket creation with mock data
    print("🎫 Demonstrating ticket creation...")
    
    # Create mock high-priority feedback data
    mock_feedback_data = {
        "id": str(uuid.uuid4()),
        "title": "Critical Login Bug - Users Cannot Access System",
        "body": """
**Description:**
Users are unable to log into the system due to a critical authentication bug.

**Steps to Reproduce:**
1. Navigate to the login page
2. Enter valid credentials
3. Click the login button
4. Observe that nothing happens

**Expected Behavior:**
User should be redirected to the dashboard after successful login.

**Actual Behavior:**
Login button does not respond, users remain on login page.

**Environment:**
- Browser: Chrome 120.0
- OS: Windows 11
- User Agent: Mozilla/5.0...
        """,
        "feedback_type": "bug",
        "component": "authentication",
        "severity": 0.95,
        "author": "john.doe@example.com",
        "url": "https://github.com/your-org/your-repo/issues/123",
        "timestamp": datetime.utcnow().isoformat(),
        "language": "en",
        "source": "github"
    }
    
    mock_priority_data = {
        "overall_score": 0.92,
        "severity_score": 0.95,
        "reach_score": 0.90,
        "recency_score": 0.85,
        "persona_score": 0.80,
        "priority_level": 5,
        "is_revenue_critical": True,
        "reasoning": [
            "Critical severity impact",
            "Affects many users",
            "Recent feedback",
            "High-value user segment",
            "Revenue-critical issue"
        ]
    }
    
    mock_cluster_data = {
        "id": str(uuid.uuid4()),
        "title": "Authentication Issues Cluster",
        "size": 8,
        "avg_severity": 0.88
    }
    
    # Simulate ticket creation (without actually creating tickets)
    print("📝 Mock ticket data:")
    print(f"  Title: {mock_feedback_data['title']}")
    print(f"  Priority Score: {mock_priority_data['overall_score']}")
    print(f"  Component: {mock_feedback_data['component']}")
    print(f"  Cluster Size: {mock_cluster_data['size']}")
    print(f"  Revenue Critical: {mock_priority_data['is_revenue_critical']}")
    print()
    
    # Demonstrate platform selection
    print("🎯 Platform selection logic:")
    item = {
        "priority_data": mock_priority_data
    }
    
    try:
        selected_platform = actioner._select_platform(item)
        print(f"  Selected platform: {selected_platform.value}")
        print(f"  Reason: {'High priority item' if mock_priority_data['overall_score'] >= 0.9 else 'Standard priority item'}")
    except Exception as e:
        print(f"  Platform selection error: {e}")
    print()
    
    # Demonstrate priority reasoning generation
    print("🧠 Priority reasoning generation:")
    from database.models import PrioritizationScore
    
    # Create a mock priority score object
    class MockPriorityScore:
        def __init__(self, data):
            self.severity_score = data['severity_score']
            self.reach_score = data['reach_score']
            self.recency_score = data['recency_score']
            self.persona_weight = data['persona_score']
            self.is_revenue_critical = data['is_revenue_critical']
            self.revenue_impact_multiplier = 1.2
    
    mock_priority = MockPriorityScore(mock_priority_data)
    reasoning = actioner._generate_priority_reasoning(mock_priority)
    
    for reason in reasoning:
        print(f"  • {reason}")
    print()
    
    # Demonstrate ticket templates
    print("📋 Ticket template examples:")
    from agents.actioner.ticket_models import TicketTemplates, TicketFormatter
    
    # Show Jira bug template
    jira_template = TicketTemplates.get_bug_template(PlatformType.JIRA)
    print(f"  Jira Bug Template:")
    print(f"    Title: {jira_template.title_template}")
    print(f"    Labels: {jira_template.labels}")
    print(f"    Components: {jira_template.components}")
    print()
    
    # Show GitHub issue template
    github_template = TicketTemplates.get_bug_template(PlatformType.GITHUB)
    print(f"  GitHub Issue Template:")
    print(f"    Title: {github_template.title_template}")
    print(f"    Labels: {github_template.labels}")
    print()
    
    # Demonstrate ticket formatting
    print("🎨 Ticket formatting example:")
    formatted_ticket = TicketFormatter.format_ticket_data(
        mock_feedback_data,
        mock_priority_data,
        mock_cluster_data,
        jira_template
    )
    
    print(f"  Formatted Title: {formatted_ticket.title}")
    print(f"  Priority: {formatted_ticket.priority.value}")
    print(f"  Labels: {formatted_ticket.labels}")
    print(f"  Components: {formatted_ticket.components}")
    print()
    
    # Demonstrate rate limiting
    print("⏱️ Rate limiting demonstration:")
    print(f"  Max tickets per hour: {actioner.actioner_config.max_tickets_per_hour}")
    print(f"  Max tickets per day: {actioner.actioner_config.max_tickets_per_day}")
    print(f"  Current hourly count: {actioner.tickets_created_this_hour}")
    print(f"  Current daily count: {actioner.tickets_created_today}")
    print(f"  Can create more tickets: {actioner._check_rate_limits()}")
    print()
    
    # Demonstrate ticket statistics (mock)
    print("📊 Ticket statistics (mock):")
    try:
        stats = await actioner.get_ticket_statistics()
        print(f"  Total tickets: {stats.get('total_tickets', 0)}")
        print(f"  Platform breakdown: {stats.get('platform_breakdown', {})}")
        print(f"  Status breakdown: {stats.get('status_breakdown', {})}")
        print(f"  Priority breakdown: {stats.get('priority_breakdown', {})}")
    except Exception as e:
        print(f"  Statistics error: {e}")
    print()
    
    # Demonstrate status update (mock)
    print("🔄 Ticket status update demonstration:")
    print("  Simulating status update for ticket TEST-123...")
    print("  Status: open -> in_progress")
    print("  Status: in_progress -> resolved")
    print("  Status: resolved -> closed")
    print()
    
    # Show configuration options
    print("⚙️ Configuration options:")
    print(f"  Priority threshold: {actioner.actioner_config.priority_threshold}")
    print(f"  Auto assign: {actioner.actioner_config.auto_assign}")
    print(f"  Require approval: {actioner.actioner_config.require_approval}")
    print(f"  Jira enabled: {actioner.actioner_config.enable_jira}")
    print(f"  GitHub enabled: {actioner.actioner_config.enable_github}")
    print()
    
    # Show input dependencies
    print("🔗 Input dependencies:")
    dependencies = actioner.get_input_dependencies()
    for dep in dependencies:
        print(f"  • {dep}")
    print()
    
    print("✅ Actioner Agent example completed!")
    print()
    print("💡 Next steps:")
    print("  1. Configure your Jira/GitHub credentials")
    print("  2. Set up the database with processed feedback")
    print("  3. Run the agent to create tickets automatically")
    print("  4. Monitor ticket creation and resolution")
    print("  5. Use the feedback loop to improve prioritization")

if __name__ == "__main__":
    # Run the example
    asyncio.run(main())

