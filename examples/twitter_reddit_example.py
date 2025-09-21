#!/usr/bin/env python3
"""
Example script demonstrating Twitter and Reddit API integration
with the Product Feedback Miner Ingestor Agent.

This script shows how to configure and run the Ingestor agent
with Twitter and Reddit APIs enabled.
"""

import asyncio
import sys
import os
from datetime import datetime
import uuid

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.ingestor.agent import IngestorAgent
from agents.base.agent import AgentContext
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_twitter_reddit_ingestion():
    """Test the Ingestor agent with Twitter and Reddit APIs."""
    
    print("🚀 Testing Product Feedback Miner with Twitter and Reddit APIs")
    print("=" * 70)
    
    # Configuration for the Ingestor agent
    config = {
        # GitHub configuration
        "repositories": [
            {
                "owner": "microsoft",
                "name": "vscode", 
                "labels": ["bug", "feature-request", "feedback"]
            }
        ],
        
        # Hacker News configuration
        "hn_keywords": ["vscode", "visual studio code"],
        
        # Exa AI configuration
        "exa_queries": ["vscode feedback", "visual studio code issues"],
        
        # Twitter configuration (requires TWITTER_BEARER_TOKEN)
        "twitter_queries": ["vscode feedback", "visual studio code"],
        
        # Reddit configuration (requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET)
        "reddit_subreddits": [
            "programming", "webdev", "datascience", "machinelearning",
            "productivity", "software", "technology"
        ],
        
        # General configuration
        "product_name": "VSCode",
        "days_back": 1,
        
        # Limits for testing
        "hn_top_stories_limit": 5,
        "exa_results_limit": 5,
        "twitter_results_limit": 10,
        "reddit_results_limit": 10
    }
    
    # Create the Ingestor agent
    agent = IngestorAgent(config_overrides=config)
    
    print("🔍 Testing API connections...")
    
    # Test all API connections
    connections = await agent.test_all_connections()
    
    print("\nAPI Connection Status:")
    for api, status in connections.items():
        status_icon = "✅ Connected" if status else "❌ Not Connected"
        print(f"   {api.upper()}: {status_icon}")
    
    print(f"\n📊 Connected APIs: {sum(connections.values())}/{len(connections)}")
    
    if not any(connections.values()):
        print("❌ No APIs are connected. Please check your API keys in .env file")
        return
    
    print("\n🔍 Running data ingestion...")
    
    # Create agent context
    context = AgentContext(
        execution_id=str(uuid.uuid4()),
        agent_name="ingestor",
        started_at=datetime.utcnow(),
        config=config,
        metadata={}
    )
    
    # Run the ingestion
    start_time = datetime.now()
    result = await agent.process(context)
    end_time = datetime.now()
    
    print(f"\n✅ Ingestion completed in {(end_time - start_time).total_seconds():.2f} seconds")
    print("=" * 70)
    
    # Display results
    print(f"📊 Results Summary:")
    print(f"   Success: {'✅' if result.success else '❌'}")
    print(f"   Items processed: {result.items_processed}")
    print(f"   Items successful: {result.items_successful}")
    print(f"   Items failed: {result.items_failed}")
    print(f"   Execution time: {result.execution_time:.2f}s")
    
    if result.metadata:
        print(f"\n📈 Data by Source:")
        print(f"   GitHub Issues: {result.metadata.get('github_items', 0)}")
        print(f"   Hacker News: {result.metadata.get('hn_items', 0)}")
        print(f"   Exa AI: {result.metadata.get('exa_items', 0)}")
        print(f"   Twitter: {result.metadata.get('twitter_items', 0)}")
        print(f"   Reddit: {result.metadata.get('reddit_items', 0)}")
        print(f"   Total Sources: {result.metadata.get('sources_processed', 0)}")
    
    if result.error_message:
        print(f"\n❌ Error: {result.error_message}")
    
    print("\n🎉 Test completed!")

def print_setup_instructions():
    """Print instructions for setting up API keys."""
    print("""
🔧 Setup Instructions for Twitter and Reddit APIs:

1. TWITTER API SETUP:
   - Go to: https://developer.twitter.com/
   - Create a developer account
   - Create a new app
   - Get your Bearer Token
   - Add to .env: TWITTER_BEARER_TOKEN=your_bearer_token_here

2. REDDIT API SETUP:
   - Go to: https://www.reddit.com/prefs/apps
   - Click "Create App" or "Create Another App"
   - Choose "script" as the app type
   - Get your client ID and secret
   - Add to .env:
     REDDIT_CLIENT_ID=your_client_id_here
     REDDIT_CLIENT_SECRET=your_client_secret_here

3. CURRENT .ENV REQUIREMENTS:
   # Existing APIs (already working)
   GITHUB_TOKEN=your_github_token_here
   EXA_API_KEY=your_exa_api_key_here
   
   # New APIs (add these)
   TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here
   REDDIT_CLIENT_ID=your_reddit_client_id_here
   REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
   
   # Database (already configured)
   DATABASE_HOST=localhost
   DATABASE_PORT=5432
   DATABASE_NAME=product_feedback_miner
   DATABASE_USER=postgres
   DATABASE_PASSWORD=password

4. RUN THIS SCRIPT:
   python examples/twitter_reddit_example.py
""")

if __name__ == "__main__":
    print_setup_instructions()
    
    # Check if user wants to continue
    response = input("\nDo you want to run the test? (y/n): ").lower().strip()
    
    if response in ['y', 'yes']:
        asyncio.run(test_twitter_reddit_ingestion())
    else:
        print("Test cancelled. Set up your API keys and run again!")
