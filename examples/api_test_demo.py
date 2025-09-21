"""
API Test Demo for Product Feedback Miner.

This script demonstrates the API functionality by testing
various endpoints and showing the responses.
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_api():
    """Test the API endpoints."""
    base_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        print("🚀 Product Feedback Miner API Test Demo")
        print("=" * 50)
        
        # Test 1: Root endpoint
        print("\n1. Testing root endpoint...")
        async with session.get(f"{base_url}/") as response:
            data = await response.json()
            print(f"   Status: {response.status}")
            print(f"   Response: {data['message']}")
            print(f"   Version: {data['data']['version']}")
        
        # Test 2: Health check
        print("\n2. Testing health check...")
        async with session.get(f"{base_url}/health") as response:
            data = await response.json()
            print(f"   Status: {response.status}")
            print(f"   System Status: {data['status']}")
            print(f"   Version: {data['version']}")
            print(f"   Agents: {len(data['agents'])}")
        
        # Test 3: Login
        print("\n3. Testing login...")
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        async with session.post(f"{base_url}/auth/login", json=login_data) as response:
            data = await response.json()
            print(f"   Status: {response.status}")
            if response.status == 200:
                print(f"   Login successful!")
                print(f"   Token type: {data['token_type']}")
                print(f"   Expires in: {data['expires_in']} seconds")
                token = data['access_token']
            else:
                print(f"   Login failed: {data.get('message', 'Unknown error')}")
                return
        
        # Test 4: List workflows (with auth)
        print("\n4. Testing workflow listing...")
        headers = {"Authorization": f"Bearer {token}"}
        async with session.get(f"{base_url}/workflows", headers=headers) as response:
            data = await response.json()
            print(f"   Status: {response.status}")
            if response.status == 200:
                print(f"   Available workflows: {data}")
            else:
                print(f"   Error: {data.get('message', 'Unknown error')}")
        
        # Test 5: Get agents status
        print("\n5. Testing agents status...")
        async with session.get(f"{base_url}/agents/status", headers=headers) as response:
            data = await response.json()
            print(f"   Status: {response.status}")
            if response.status == 200:
                print(f"   Agents found: {len(data)}")
                for agent in data:
                    print(f"     - {agent['agent_name']}: {agent['status']}")
            else:
                print(f"   Error: {data.get('message', 'Unknown error')}")
        
        # Test 6: Execute workflow
        print("\n6. Testing workflow execution...")
        workflow_data = {
            "workflow_name": "quick_processing",
            "config": {"test_mode": True, "max_items": 5}
        }
        async with session.post(f"{base_url}/workflows/execute", json=workflow_data, headers=headers) as response:
            data = await response.json()
            print(f"   Status: {response.status}")
            if response.status == 200:
                print(f"   Workflow execution started!")
                print(f"   Execution ID: {data['execution_id']}")
                print(f"   Workflow: {data['workflow_name']}")
                print(f"   Status: {data['status']}")
                execution_id = data['execution_id']
            else:
                print(f"   Error: {data.get('message', 'Unknown error')}")
                return
        
        # Test 7: Get workflow status
        print("\n7. Testing workflow status...")
        async with session.get(f"{base_url}/workflows/{execution_id}/status", headers=headers) as response:
            data = await response.json()
            print(f"   Status: {response.status}")
            if response.status == 200:
                print(f"   Execution ID: {data['execution_id']}")
                print(f"   Workflow: {data['workflow_name']}")
                print(f"   Status: {data['status']}")
                print(f"   Progress: {data['progress']:.1f}%")
                print(f"   Steps: {data['steps_completed']}/{data['steps_total']}")
            else:
                print(f"   Error: {data.get('message', 'Unknown error')}")
        
        # Test 8: Get feedback
        print("\n8. Testing feedback retrieval...")
        async with session.get(f"{base_url}/feedback?page=1&page_size=5", headers=headers) as response:
            data = await response.json()
            print(f"   Status: {response.status}")
            if response.status == 200:
                print(f"   Total feedback items: {data['total']}")
                print(f"   Items on this page: {len(data['items'])}")
                if data['items']:
                    print("   Sample feedback:")
                    for item in data['items'][:3]:
                        print(f"     - {item['title']} ({item['feedback_type']})")
            else:
                print(f"   Error: {data.get('message', 'Unknown error')}")
        
        # Test 9: Search
        print("\n9. Testing search...")
        search_data = {
            "query": "bug",
            "filters": {},
            "page": 1,
            "page_size": 5
        }
        async with session.post(f"{base_url}/api/v1/search", json=search_data, headers=headers) as response:
            data = await response.json()
            print(f"   Status: {response.status}")
            if response.status == 200:
                print(f"   Search results: {data['total']} items found")
                print(f"   Search time: {data['search_time']:.3f} seconds")
                if data['results']:
                    print("   Sample results:")
                    for result in data['results'][:3]:
                        print(f"     - {result['title']} (relevance: {result['relevance_score']})")
            else:
                print(f"   Error: {data.get('message', 'Unknown error')}")
        
        # Test 10: Get system metrics
        print("\n10. Testing system metrics...")
        async with session.get(f"{base_url}/metrics", headers=headers) as response:
            data = await response.json()
            print(f"    Status: {response.status}")
            if response.status == 200:
                print(f"    Timestamp: {data['timestamp']}")
                print(f"    Workflows: {data['workflows']}")
                print(f"    Agents: {data['agents']}")
                print(f"    Feedback: {data['feedback']}")
                print(f"    Clusters: {data['clusters']}")
                print(f"    Tickets: {data['tickets']}")
            else:
                print(f"    Error: {data.get('message', 'Unknown error')}")
        
        print("\n✅ API test demo completed!")
        print("\nTo start the API server, run:")
        print("   python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload")
        print("\nThen visit:")
        print("   - API Documentation: http://localhost:8000/docs")
        print("   - Alternative Docs: http://localhost:8000/redoc")
        print("   - Health Check: http://localhost:8000/health")

if __name__ == "__main__":
    asyncio.run(test_api())

