"""
API Client Example for Product Feedback Miner.

This script demonstrates how to use the Product Feedback Miner API
from external applications and scripts.
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

class ProductFeedbackMinerClient:
    """Client for Product Feedback Miner API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        """Initialize the API client."""
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self.auth_token: Optional[str] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        elif self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login and get authentication token."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        login_data = {
            "username": username,
            "password": password
        }
        
        async with self.session.post(
            f"{self.base_url}/auth/login",
            json=login_data,
            headers=self._get_headers()
        ) as response:
            if response.status == 200:
                data = await response.json()
                self.auth_token = data["access_token"]
                return data
            else:
                error_data = await response.json()
                raise Exception(f"Login failed: {error_data.get('message', 'Unknown error')}")
    
    async def get_health(self) -> Dict[str, Any]:
        """Get system health status."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.get(
            f"{self.base_url}/health",
            headers=self._get_headers()
        ) as response:
            return await response.json()
    
    async def execute_workflow(self, workflow_name: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a workflow."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        workflow_data = {
            "workflow_name": workflow_name,
            "config": config or {}
        }
        
        async with self.session.post(
            f"{self.base_url}/workflows/execute",
            json=workflow_data,
            headers=self._get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_data = await response.json()
                raise Exception(f"Workflow execution failed: {error_data.get('message', 'Unknown error')}")
    
    async def get_workflow_status(self, execution_id: str) -> Dict[str, Any]:
        """Get workflow execution status."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.get(
            f"{self.base_url}/workflows/{execution_id}/status",
            headers=self._get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_data = await response.json()
                raise Exception(f"Failed to get workflow status: {error_data.get('message', 'Unknown error')}")
    
    async def cancel_workflow(self, execution_id: str) -> Dict[str, Any]:
        """Cancel a workflow execution."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.delete(
            f"{self.base_url}/workflows/{execution_id}/cancel",
            headers=self._get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_data = await response.json()
                raise Exception(f"Failed to cancel workflow: {error_data.get('message', 'Unknown error')}")
    
    async def list_workflows(self) -> List[str]:
        """List available workflows."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.get(
            f"{self.base_url}/workflows",
            headers=self._get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_data = await response.json()
                raise Exception(f"Failed to list workflows: {error_data.get('message', 'Unknown error')}")
    
    async def get_agents_status(self) -> List[Dict[str, Any]]:
        """Get status of all agents."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.get(
            f"{self.base_url}/agents/status",
            headers=self._get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_data = await response.json()
                raise Exception(f"Failed to get agents status: {error_data.get('message', 'Unknown error')}")
    
    async def get_feedback(
        self,
        page: int = 1,
        page_size: int = 20,
        feedback_type: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get feedback items with filtering and pagination."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if feedback_type:
            params["feedback_type"] = feedback_type
        if source:
            params["source"] = source
        if search:
            params["search"] = search
        
        async with self.session.get(
            f"{self.base_url}/feedback",
            params=params,
            headers=self._get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_data = await response.json()
                raise Exception(f"Failed to get feedback: {error_data.get('message', 'Unknown error')}")
    
    async def get_feedback_item(self, feedback_id: str) -> Dict[str, Any]:
        """Get a specific feedback item."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.get(
            f"{self.base_url}/feedback/{feedback_id}",
            headers=self._get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_data = await response.json()
                raise Exception(f"Failed to get feedback item: {error_data.get('message', 'Unknown error')}")
    
    async def get_clusters(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get clusters with pagination and search."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if search:
            params["search"] = search
        
        async with self.session.get(
            f"{self.base_url}/api/v1/clusters",
            params=params,
            headers=self._get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_data = await response.json()
                raise Exception(f"Failed to get clusters: {error_data.get('message', 'Unknown error')}")
    
    async def get_tickets(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        platform: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get tickets with pagination and filtering."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        params = {
            "page": page,
            "page_size": page_size
        }
        
        if status:
            params["status"] = status
        if platform:
            params["platform"] = platform
        
        async with self.session.get(
            f"{self.base_url}/api/v1/tickets",
            params=params,
            headers=self._get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_data = await response.json()
                raise Exception(f"Failed to get tickets: {error_data.get('message', 'Unknown error')}")
    
    async def generate_report(
        self,
        report_type: str,
        format: str = "html",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_charts: bool = True
    ) -> Dict[str, Any]:
        """Generate a report."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        report_data = {
            "report_type": report_type,
            "format": format,
            "include_charts": include_charts,
            "include_raw_data": False,
            "filters": {}
        }
        
        if start_date:
            report_data["start_date"] = start_date.isoformat()
        if end_date:
            report_data["end_date"] = end_date.isoformat()
        
        async with self.session.post(
            f"{self.base_url}/api/v1/reports/generate",
            json=report_data,
            headers=self._get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_data = await response.json()
                raise Exception(f"Failed to generate report: {error_data.get('message', 'Unknown error')}")
    
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Search across all data."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        search_data = {
            "query": query,
            "filters": filters or {},
            "page": page,
            "page_size": page_size,
            "sort_by": "relevance",
            "sort_order": "desc"
        }
        
        async with self.session.post(
            f"{self.base_url}/api/v1/search",
            json=search_data,
            headers=self._get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_data = await response.json()
                raise Exception(f"Search failed: {error_data.get('message', 'Unknown error')}")
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        async with self.session.get(
            f"{self.base_url}/metrics",
            headers=self._get_headers()
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_data = await response.json()
                raise Exception(f"Failed to get system metrics: {error_data.get('message', 'Unknown error')}")

async def main():
    """Main example function."""
    print("Product Feedback Miner API Client Example")
    print("=" * 50)
    
    # Initialize client
    async with ProductFeedbackMinerClient("http://localhost:8000") as client:
        try:
            # Login
            print("1. Logging in...")
            login_result = await client.login("admin", "admin123")
            print(f"   Login successful! Token expires in {login_result['expires_in']} seconds")
            
            # Check health
            print("\n2. Checking system health...")
            health = await client.get_health()
            print(f"   System status: {health['status']}")
            print(f"   Version: {health['version']}")
            print(f"   Agents: {len(health['agents'])}")
            
            # List workflows
            print("\n3. Listing available workflows...")
            workflows = await client.list_workflows()
            print(f"   Available workflows: {workflows}")
            
            # Get agents status
            print("\n4. Checking agents status...")
            agents = await client.get_agents_status()
            for agent in agents:
                print(f"   {agent['agent_name']}: {agent['status']} - {agent['message']}")
            
            # Execute a workflow
            print("\n5. Executing workflow...")
            execution = await client.execute_workflow(
                "quick_processing",
                {"test_mode": True, "max_items": 10}
            )
            print(f"   Workflow execution started: {execution['execution_id']}")
            print(f"   Status: {execution['status']}")
            
            # Monitor workflow status
            print("\n6. Monitoring workflow status...")
            execution_id = execution['execution_id']
            
            for i in range(5):  # Check status 5 times
                await asyncio.sleep(2)  # Wait 2 seconds between checks
                
                status = await client.get_workflow_status(execution_id)
                print(f"   Status check {i+1}: {status['status']} - {status['progress']:.1f}% complete")
                
                if status['status'] in ['completed', 'failed', 'cancelled']:
                    break
            
            # Get feedback
            print("\n7. Getting feedback items...")
            feedback = await client.get_feedback(page=1, page_size=5)
            print(f"   Total feedback items: {feedback['total']}")
            print(f"   Items on this page: {len(feedback['items'])}")
            
            if feedback['items']:
                print("   Sample feedback:")
                for item in feedback['items'][:3]:  # Show first 3 items
                    print(f"     - {item['title']} ({item['feedback_type']})")
            
            # Search feedback
            print("\n8. Searching feedback...")
            search_results = await client.search("bug", page=1, page_size=5)
            print(f"   Search results: {search_results['total']} items found")
            print(f"   Search time: {search_results['search_time']:.3f} seconds")
            
            if search_results['results']:
                print("   Sample search results:")
                for result in search_results['results'][:3]:
                    print(f"     - {result['title']} (relevance: {result['relevance_score']})")
            
            # Get clusters
            print("\n9. Getting clusters...")
            clusters = await client.get_clusters(page=1, page_size=5)
            print(f"   Total clusters: {clusters['total']}")
            print(f"   Clusters on this page: {len(clusters['clusters'])}")
            
            if clusters['clusters']:
                print("   Sample clusters:")
                for cluster in clusters['clusters'][:3]:
                    print(f"     - {cluster['name']} ({cluster['member_count']} members)")
            
            # Get tickets
            print("\n10. Getting tickets...")
            tickets = await client.get_tickets(page=1, page_size=5)
            print(f"    Total tickets: {tickets['total']}")
            print(f"    Tickets on this page: {len(tickets['tickets'])}")
            
            if tickets['tickets']:
                print("    Sample tickets:")
                for ticket in tickets['tickets'][:3]:
                    print(f"      - {ticket['title']} ({ticket['platform']})")
            
            # Generate a report
            print("\n11. Generating report...")
            report = await client.generate_report(
                "executive_summary",
                format="html",
                include_charts=True
            )
            print(f"    Report generated: {report['id']}")
            print(f"    Report type: {report['report_type']}")
            print(f"    Format: {report['format']}")
            
            # Get system metrics
            print("\n12. Getting system metrics...")
            metrics = await client.get_system_metrics()
            print(f"    Workflows: {metrics['workflows']}")
            print(f"    Agents: {metrics['agents']}")
            print(f"    Feedback: {metrics['feedback']}")
            print(f"    Clusters: {metrics['clusters']}")
            print(f"    Tickets: {metrics['tickets']}")
            
            print("\n✅ API Client example completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

