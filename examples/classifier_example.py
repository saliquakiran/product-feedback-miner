#!/usr/bin/env python3
"""
Example usage of the Classifier Agent.

This script demonstrates how to use the Classifier Agent to classify
feedback documents and get classification results.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.classifier.agent import ClassifierAgent
from agents.classifier.models import FeedbackType, SeverityLevel, ComponentType

async def main():
    """Main example function."""
    print("🤖 Product Feedback Classifier Agent Example")
    print("=" * 50)
    
    # Initialize the classifier agent
    classifier = ClassifierAgent({
        "batch_size": 5,
        "confidence_threshold": 0.5,
        "enable_batch_processing": True,
        "model_name": "gpt-3.5-turbo",
        "temperature": 0.1
    })
    
    # Test OpenAI connection
    print("🔗 Testing OpenAI connection...")
    is_connected = await classifier.test_openai_connection()
    if not is_connected:
        print("❌ OpenAI connection failed. Please check your API key.")
        return
    print("✅ OpenAI connection successful!")
    
    # Example feedback items to classify
    feedback_examples = [
        {
            "title": "API timeout errors",
            "content": "The API is frequently timing out when making requests. This is causing our application to fail and users are getting frustrated. This happens especially during peak hours.",
            "author": "developer123"
        },
        {
            "title": "Feature request: Dark mode",
            "content": "It would be great to have a dark mode option for the dashboard. Many users have requested this feature and it would improve the user experience, especially for night-time usage.",
            "author": "user456"
        },
        {
            "title": "Login page is broken",
            "content": "The login page is completely broken and users cannot access their accounts. This is a critical issue that needs immediate attention.",
            "author": "admin789"
        },
        {
            "title": "Documentation is unclear",
            "content": "The API documentation is confusing and doesn't explain how to use the new endpoints. Could you please update it with better examples?",
            "author": "developer999"
        },
        {
            "title": "Performance issues",
            "content": "The application is running very slowly, especially when loading large datasets. It takes several minutes to load the dashboard.",
            "author": "user111"
        }
    ]
    
    print(f"\n📝 Classifying {len(feedback_examples)} feedback items...")
    print("-" * 50)
    
    # Classify each feedback item
    for i, feedback in enumerate(feedback_examples, 1):
        print(f"\n{i}. {feedback['title']}")
        print(f"   Content: {feedback['content'][:100]}...")
        
        try:
            result = await classifier.classify_single_feedback(
                title=feedback['title'],
                content=feedback['content'],
                author=feedback['author']
            )
            
            if result:
                print(f"   ✅ Classification Results:")
                print(f"      Type: {result.feedback_type.value}")
                print(f"      Severity: {result.severity_level.value}")
                print(f"      Component: {result.component.value}")
                print(f"      Confidence: {result.overall_confidence:.2f}")
                print(f"      Sentiment: {result.sentiment}")
                print(f"      Keywords: {', '.join(result.keywords[:3])}")
                if result.urgency_indicators:
                    print(f"      Urgency: {', '.join(result.urgency_indicators)}")
            else:
                print("   ❌ Classification failed")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Get classification statistics
    print(f"\n📊 Classification Statistics:")
    print("-" * 30)
    stats = await classifier.get_classification_stats()
    print(f"Total classified: {stats['total_classified']}")
    print(f"Success rate: {stats['success_rate']:.2%}")
    print(f"Average confidence: {stats['average_confidence']:.2f}")
    print(f"Average processing time: {stats['average_processing_time_ms']:.1f}ms")
    
    # Show distribution
    if stats['type_distribution']:
        print(f"\n📈 Type Distribution:")
        for feedback_type, count in stats['type_distribution'].items():
            print(f"   {feedback_type}: {count}")
    
    if stats['severity_distribution']:
        print(f"\n🚨 Severity Distribution:")
        for severity, count in stats['severity_distribution'].items():
            print(f"   {severity}: {count}")
    
    if stats['component_distribution']:
        print(f"\n🔧 Component Distribution:")
        for component, count in stats['component_distribution'].items():
            print(f"   {component}: {count}")
    
    print(f"\n✅ Example completed successfully!")

if __name__ == "__main__":
    # Run the example
    asyncio.run(main())

