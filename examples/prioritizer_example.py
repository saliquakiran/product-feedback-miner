#!/usr/bin/env python3
"""
Example script demonstrating the Prioritizer Agent functionality.

This script shows how to:
1. Initialize the Prioritizer Agent
2. Process feedback items for prioritization
3. View priority scores and rankings
4. Test different scoring scenarios
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.prioritizer.agent import PrioritizerAgent
from agents.prioritizer.scoring import (
    ScoringWeights, BusinessRules, PriorityLevel, UserSegment
)
from agents.base.agent import AgentContext
from database.models import ProcessedDocument, RawFeedback, SourceType, ProcessingStatus, FeedbackType
from database.setup import get_session_maker, create_all_tables

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def create_sample_data():
    """Create sample feedback data for prioritization demonstration."""
    logger.info("Creating sample feedback data...")
    
    # Sample feedback data with different priority scenarios
    sample_feedback = [
        {
            "title": "Critical: Payment system down",
            "body": "Users cannot process payments. This is blocking all transactions. Revenue is being lost every minute. Please fix immediately!",
            "component": "payment",
            "feedback_type": FeedbackType.BUG,
            "severity": "critical",
            "user_count": 500,
            "user_segment": "enterprise"
        },
        {
            "title": "Login button not working",
            "body": "When I click the login button, nothing happens. I can't access my account.",
            "component": "authentication",
            "feedback_type": FeedbackType.BUG,
            "severity": "high",
            "user_count": 50,
            "user_segment": "individual"
        },
        {
            "title": "Add dark mode theme",
            "body": "It would be great to have a dark mode option for the application. Many users have requested this feature.",
            "component": "ui",
            "feedback_type": FeedbackType.FEATURE_REQUEST,
            "severity": "low",
            "user_count": 25,
            "user_segment": "professional"
        },
        {
            "title": "API timeout errors",
            "body": "Getting frequent timeout errors when calling the API. Response times are too slow for our integration.",
            "component": "api",
            "feedback_type": FeedbackType.PERFORMANCE,
            "severity": "high",
            "user_count": 10,
            "user_segment": "enterprise"
        },
        {
            "title": "Mobile app crashes on startup",
            "body": "The mobile app immediately crashes when I try to open it. This is critical for mobile users.",
            "component": "mobile",
            "feedback_type": FeedbackType.BUG,
            "severity": "critical",
            "user_count": 100,
            "user_segment": "individual"
        },
        {
            "title": "Documentation needs update",
            "body": "The API documentation is outdated and doesn't match the current implementation.",
            "component": "docs",
            "feedback_type": FeedbackType.DOCS,
            "severity": "medium",
            "user_count": 5,
            "user_segment": "professional"
        },
        {
            "title": "Security vulnerability in auth",
            "body": "Found a potential security issue in the authentication system. Users can bypass login in certain conditions.",
            "component": "security",
            "feedback_type": FeedbackType.SECURITY,
            "severity": "critical",
            "user_count": 1,
            "user_segment": "enterprise"
        },
        {
            "title": "Slow dashboard loading",
            "body": "The dashboard takes too long to load. It's affecting user productivity.",
            "component": "ui",
            "feedback_type": FeedbackType.PERFORMANCE,
            "severity": "medium",
            "user_count": 30,
            "user_segment": "professional"
        }
    ]
    
    # Create database session
    session_maker = get_session_maker()
    
    with session_maker() as session:
        # Create raw feedback records
        raw_feedback_records = []
        for i, feedback in enumerate(sample_feedback):
            raw_feedback = RawFeedback(
                source_type=SourceType.GITHUB_ISSUE.value,
                source_id=f"priority_sample_{i}",
                url=f"https://example.com/issue/{i}",
                title=feedback["title"],
                content=feedback["body"],
                timestamp=datetime.utcnow() - timedelta(hours=i*2)  # Stagger timestamps
            )
            session.add(raw_feedback)
            raw_feedback_records.append(raw_feedback)
        
        session.commit()
        
        # Create processed documents
        processed_docs = []
        for i, (raw_feedback, feedback) in enumerate(zip(raw_feedback_records, sample_feedback)):
            processed_doc = ProcessedDocument(
                raw_feedback_id=raw_feedback.id,
                title=feedback["title"],
                body=feedback["body"],
                author=f"user_{i}",
                timestamp=datetime.utcnow() - timedelta(hours=i*2),
                url=f"https://example.com/issue/{i}",
                language="en",
                word_count=len(feedback["body"].split()),
                feedback_type=feedback["feedback_type"],
                component=feedback["component"],
                processing_status=ProcessingStatus.COMPLETED
            )
            session.add(processed_doc)
            processed_docs.append(processed_doc)
        
        session.commit()
        logger.info(f"Created {len(processed_docs)} sample documents for prioritization")
        return processed_docs

async def demonstrate_scoring_scenarios():
    """Demonstrate different scoring scenarios."""
    logger.info("=== Scoring Scenarios Demo ===")
    
    # Initialize prioritizer agent
    agent = PrioritizerAgent({
        "prioritizer_batch_size": 10,
        "max_items_to_prioritize": 100
    })
    
    # Test different scenarios
    scenarios = [
        {
            "name": "Critical Enterprise Issue",
            "data": {
                "title": "System down for enterprise customers",
                "body": "Critical system failure affecting all enterprise users. Revenue impact is significant.",
                "severity": "critical",
                "component": "authentication",
                "user_count": 1000,
                "user_segment": "enterprise",
                "timestamp": datetime.utcnow(),
                "feedback_quality": "high"
            }
        },
        {
            "name": "Individual User Feature Request",
            "data": {
                "title": "Add new button color",
                "body": "Can we change the button color to blue?",
                "severity": "low",
                "component": "ui",
                "user_count": 1,
                "user_segment": "individual",
                "timestamp": datetime.utcnow() - timedelta(days=7),
                "feedback_quality": "low"
            }
        },
        {
            "name": "Security Vulnerability",
            "data": {
                "title": "Security issue in payment processing",
                "body": "Found a security vulnerability that could expose payment data. This is urgent and needs immediate attention.",
                "severity": "critical",
                "component": "security",
                "user_count": 1,
                "user_segment": "enterprise",
                "timestamp": datetime.utcnow(),
                "feedback_quality": "high"
            }
        },
        {
            "name": "Performance Issue",
            "data": {
                "title": "API response time too slow",
                "body": "API calls are taking 10+ seconds to respond. This is affecting our application performance.",
                "severity": "high",
                "component": "api",
                "user_count": 50,
                "user_segment": "professional",
                "timestamp": datetime.utcnow() - timedelta(hours=2),
                "feedback_quality": "medium"
            }
        }
    ]
    
    for scenario in scenarios:
        logger.info(f"\n--- {scenario['name']} ---")
        
        # Calculate priority score
        priority_score = agent.calculator.calculate_priority(scenario['data'])
        
        logger.info(f"Overall Score: {priority_score.final_score:.3f}")
        logger.info(f"Priority Level: {priority_score.priority_level.value}")
        logger.info(f"Severity Score: {priority_score.severity_score:.3f}")
        logger.info(f"Reach Score: {priority_score.reach_score:.3f}")
        logger.info(f"Recency Score: {priority_score.recency_score:.3f}")
        logger.info(f"Persona Score: {priority_score.persona_score:.3f}")
        logger.info(f"Cluster Amplification: {priority_score.cluster_amplification:.3f}")
        logger.info(f"Urgency Boost: {priority_score.urgency_boost:.3f}")
        logger.info(f"Revenue Boost: {priority_score.revenue_boost:.3f}")
        logger.info(f"Reasoning: {', '.join(priority_score.reasoning)}")

async def demonstrate_priority_calculation():
    """Demonstrate priority calculation with different factors."""
    logger.info("\n=== Priority Calculation Demo ===")
    
    agent = PrioritizerAgent()
    
    # Test urgency detection
    urgency_tests = [
        ("Normal feedback", "Please add a new feature", "It would be nice to have this"),
        ("Urgent feedback", "Critical bug blocking users", "This is urgent and needs immediate fix"),
        ("Emergency feedback", "System down - emergency", "Critical system failure - can't work")
    ]
    
    for test_name, title, body in urgency_tests:
        is_urgent, indicators = agent.calculator.rule_engine.urgency_detector.detect_urgency(title, body)
        boost = agent.calculator.rule_engine.urgency_detector.get_urgency_boost(indicators)
        logger.info(f"{test_name}: Urgent={is_urgent}, Boost={boost:.3f}, Indicators={indicators}")
    
    # Test cluster amplification
    cluster_tests = [
        ("No cluster", None),
        ("Small cluster", {"size": 2, "avg_similarity": 0.8}),
        ("Large cluster", {"size": 10, "avg_similarity": 0.9}),
        ("High-quality cluster", {"size": 5, "avg_similarity": 0.95, "temporal_coherence": 0.9, "user_diversity": 0.8})
    ]
    
    for test_name, cluster_data in cluster_tests:
        amplification = agent.calculator.rule_engine.apply_cluster_amplification(cluster_data)
        logger.info(f"{test_name}: Amplification={amplification:.3f}")

async def demonstrate_prioritization_process():
    """Demonstrate the full prioritization process."""
    logger.info("\n=== Prioritization Process Demo ===")
    
    # Initialize agent
    agent = PrioritizerAgent({
        "prioritizer_batch_size": 5,
        "max_items_to_prioritize": 50
    })
    
    # Create agent context
    context = AgentContext(
        agent_name="prioritizer",
        execution_id="demo_execution",
        started_at=datetime.utcnow()
    )
    
    # Run prioritization process
    logger.info("Running prioritization process...")
    result = await agent.process(context)
    
    if result.success:
        logger.info(f"Prioritization completed successfully!")
        logger.info(f"Items processed: {result.items_processed}")
        logger.info(f"Items successful: {result.items_successful}")
        logger.info(f"Items failed: {result.items_failed}")
        logger.info(f"Execution time: {result.execution_time:.2f} seconds")
        
        if result.metadata:
            logger.info(f"Priority scores created: {result.metadata.get('priority_scores_created', 0)}")
            logger.info(f"Rankings generated: {result.metadata.get('rankings_generated', 0)}")
            
            # Show priority distribution
            distribution = result.metadata.get('priority_distribution', {})
            logger.info("Priority Distribution:")
            for level, count in distribution.items():
                logger.info(f"  {level}: {count}")
            
            # Show top priority items
            top_items = result.metadata.get('top_priority_items', [])
            if top_items:
                logger.info("Top Priority Items:")
                for item in top_items[:5]:  # Show top 5
                    logger.info(f"  {item['rank']}. {item['title']} (Score: {item['priority_score']:.3f})")
    else:
        logger.error(f"Prioritization failed: {result.error_message}")

async def demonstrate_statistics():
    """Demonstrate prioritization statistics."""
    logger.info("\n=== Prioritization Statistics Demo ===")
    
    agent = PrioritizerAgent()
    
    # Get prioritization statistics
    stats = await agent.get_prioritization_stats()
    
    logger.info("Prioritization Statistics:")
    for key, value in stats.items():
        if isinstance(value, dict):
            logger.info(f"  {key}:")
            for sub_key, sub_value in value.items():
                logger.info(f"    {sub_key}: {sub_value}")
        else:
            logger.info(f"  {key}: {value}")

async def demonstrate_weight_adjustment():
    """Demonstrate weight adjustment based on feedback."""
    logger.info("\n=== Weight Adjustment Demo ===")
    
    agent = PrioritizerAgent({
        "enable_learning": True,
        "learning_rate": 0.1
    })
    
    # Show initial weights
    logger.info("Initial weights:")
    logger.info(f"  Severity: {agent.weights.severity:.3f}")
    logger.info(f"  Reach: {agent.weights.reach:.3f}")
    logger.info(f"  Recency: {agent.weights.recency:.3f}")
    logger.info(f"  Persona: {agent.weights.persona:.3f}")
    
    # Simulate feedback loop data
    feedback_data = [
        {
            "resolution_successful": True,
            "high_severity": True,
            "high_reach": False,
            "high_recency": True,
            "high_persona": False
        },
        {
            "resolution_successful": True,
            "high_severity": False,
            "high_reach": True,
            "high_recency": False,
            "high_persona": True
        }
    ]
    
    # Update weights based on feedback
    await agent.update_weights_from_feedback(feedback_data)
    
    # Show updated weights
    logger.info("Updated weights after learning:")
    logger.info(f"  Severity: {agent.weights.severity:.3f}")
    logger.info(f"  Reach: {agent.weights.reach:.3f}")
    logger.info(f"  Recency: {agent.weights.recency:.3f}")
    logger.info(f"  Persona: {agent.weights.persona:.3f}")

async def main():
    """Main demonstration function."""
    logger.info("Starting Prioritizer Agent Demonstration")
    logger.info("=" * 60)
    
    try:
        # Ensure database is set up
        logger.info("Setting up database...")
        create_all_tables()
        
        # Create sample data
        await create_sample_data()
        
        # Demonstrate scoring scenarios
        await demonstrate_scoring_scenarios()
        
        # Demonstrate priority calculation
        await demonstrate_priority_calculation()
        
        # Demonstrate full prioritization process
        await demonstrate_prioritization_process()
        
        # Demonstrate statistics
        await demonstrate_statistics()
        
        # Demonstrate weight adjustment
        await demonstrate_weight_adjustment()
        
        logger.info("\n" + "=" * 60)
        logger.info("Prioritizer Agent demonstration completed successfully!")
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    # Run the demonstration
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

