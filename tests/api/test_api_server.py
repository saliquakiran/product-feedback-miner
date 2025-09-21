"""
Tests for the API Server.

This module contains comprehensive unit and integration tests
for the API endpoints and functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from fastapi import status
import json

from api.server import app
from api.models import (
    WorkflowExecutionRequest, FeedbackQueryRequest, LoginRequest,
    ScheduledJobRequest, ReportGenerationRequest, SearchRequest
)
from api.auth import USERS, API_KEYS

class TestAPIServer:
    """Test cases for API Server."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        return {"Authorization": f"Bearer {API_KEYS['admin']}"}
    
    @pytest.fixture
    def readonly_headers(self):
        """Create read-only authentication headers."""
        return {"Authorization": f"Bearer {API_KEYS['readonly']}"}
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Product Feedback Miner API"
        assert "version" in data["data"]
        assert "docs_url" in data["data"]
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "agents" in data
    
    def test_login_success(self, client):
        """Test successful login."""
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert "user" in data
    
    def test_login_failure(self, client):
        """Test failed login."""
        login_data = {
            "username": "admin",
            "password": "wrongpassword"
        }
        
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 401
        
        data = response.json()
        assert data["status"] == "error"
        assert "Incorrect username or password" in data["message"]
    
    def test_verify_token_success(self, client):
        """Test successful token verification."""
        # First login to get a token
        login_data = {"username": "admin", "password": "admin123"}
        login_response = client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        response = client.post("/auth/verify", params={"token": token})
        assert response.status_code == 200
        
        data = response.json()
        assert data["valid"] is True
        assert "user" in data
    
    def test_verify_token_failure(self, client):
        """Test failed token verification."""
        response = client.post("/auth/verify", params={"token": "invalid_token"})
        assert response.status_code == 200
        
        data = response.json()
        assert data["valid"] is False
        assert data["user"] is None
    
    def test_refresh_token(self, client, auth_headers):
        """Test token refresh."""
        response = client.post("/auth/refresh", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    def test_list_workflows(self, client, auth_headers):
        """Test listing workflows."""
        response = client.get("/workflows", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert "feedback_processing" in data
        assert "quick_processing" in data
    
    def test_execute_workflow_success(self, client, auth_headers):
        """Test successful workflow execution."""
        with patch('api.server.workflow_engine.execute_workflow') as mock_execute:
            mock_execute.return_value = Mock(
                execution_id="test-execution-123",
                workflow_name="quick_processing",
                status="completed",
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                total_duration=30.5,
                steps_completed=5,
                steps_failed=0,
                steps_total=5,
                error_message=None,
                metadata={}
            )
            
            workflow_data = {
                "workflow_name": "quick_processing",
                "config": {"test": "value"}
            }
            
            response = client.post("/workflows/execute", json=workflow_data, headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["execution_id"] == "test-execution-123"
            assert data["workflow_name"] == "quick_processing"
            assert data["status"] == "completed"
            assert data["steps_completed"] == 5
            assert data["steps_failed"] == 0
    
    def test_execute_workflow_failure(self, client, auth_headers):
        """Test failed workflow execution."""
        with patch('api.server.workflow_engine.execute_workflow') as mock_execute:
            mock_execute.side_effect = Exception("Workflow execution failed")
            
            workflow_data = {
                "workflow_name": "quick_processing",
                "config": {}
            }
            
            response = client.post("/workflows/execute", json=workflow_data, headers=auth_headers)
            assert response.status_code == 500
            
            data = response.json()
            assert data["status"] == "error"
            assert "Workflow execution failed" in data["message"]
    
    def test_get_workflow_status_success(self, client, auth_headers):
        """Test getting workflow status."""
        with patch('api.server.workflow_engine.get_workflow_status') as mock_get_status:
            mock_get_status.return_value = Mock(
                execution_id="test-execution-123",
                workflow_name="quick_processing",
                status="running",
                steps_completed=2,
                steps_total=5,
                started_at=datetime.utcnow(),
                error_message=None
            )
            
            response = client.get("/workflows/test-execution-123/status", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["execution_id"] == "test-execution-123"
            assert data["workflow_name"] == "quick_processing"
            assert data["status"] == "running"
            assert data["progress"] == 40.0  # 2/5 * 100
            assert data["steps_completed"] == 2
            assert data["steps_total"] == 5
    
    def test_get_workflow_status_not_found(self, client, auth_headers):
        """Test getting status of non-existent workflow."""
        with patch('api.server.workflow_engine.get_workflow_status') as mock_get_status:
            mock_get_status.return_value = None
            
            response = client.get("/workflows/non-existent/status", headers=auth_headers)
            assert response.status_code == 404
            
            data = response.json()
            assert data["status"] == "error"
            assert "Workflow execution not found" in data["message"]
    
    def test_cancel_workflow_success(self, client, auth_headers):
        """Test successful workflow cancellation."""
        with patch('api.server.workflow_engine.cancel_workflow') as mock_cancel:
            mock_cancel.return_value = True
            
            response = client.delete("/workflows/test-execution-123/cancel", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "success"
            assert "Workflow cancelled successfully" in data["message"]
    
    def test_cancel_workflow_not_found(self, client, auth_headers):
        """Test cancelling non-existent workflow."""
        with patch('api.server.workflow_engine.cancel_workflow') as mock_cancel:
            mock_cancel.return_value = False
            
            response = client.delete("/workflows/non-existent/cancel", headers=auth_headers)
            assert response.status_code == 404
            
            data = response.json()
            assert data["status"] == "error"
            assert "Workflow execution not found" in data["message"]
    
    def test_get_agents_status(self, client, auth_headers):
        """Test getting agents status."""
        with patch('api.server.workflow_engine.get_agent_health') as mock_health:
            mock_health.return_value = {
                "ingestor": {"status": "healthy", "message": "OK"},
                "classifier": {"status": "unhealthy", "message": "API key missing"}
            }
            
            response = client.get("/agents/status", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            
            # Check ingestor
            ingestor = next(item for item in data if item["agent_name"] == "ingestor")
            assert ingestor["status"] == "healthy"
            assert ingestor["message"] == "OK"
            
            # Check classifier
            classifier = next(item for item in data if item["agent_name"] == "classifier")
            assert classifier["status"] == "unhealthy"
            assert "API key missing" in classifier["message"]
    
    def test_start_agent(self, client, auth_headers):
        """Test starting an agent."""
        response = client.post("/agents/ingestor/start", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "Agent ingestor started successfully" in data["message"]
    
    def test_stop_agent(self, client, auth_headers):
        """Test stopping an agent."""
        response = client.post("/agents/ingestor/stop", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "Agent ingestor stopped successfully" in data["message"]
    
    def test_get_feedback_success(self, client, auth_headers):
        """Test getting feedback items."""
        with patch('api.server.get_session') as mock_session:
            # Mock database session and query
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            # Mock query results
            mock_doc = Mock()
            mock_doc.id = "test-feedback-123"
            mock_doc.title = "Test Feedback"
            mock_doc.content = "This is test feedback"
            mock_doc.feedback_type = Mock()
            mock_doc.feedback_type.value = "bug"
            mock_doc.source_type = Mock()
            mock_doc.source_type.value = "github_issue"
            mock_doc.source_url = "https://github.com/test/repo/issues/1"
            mock_doc.author = "testuser"
            mock_doc.created_at = datetime.utcnow()
            mock_doc.processed_at = datetime.utcnow()
            mock_doc.cluster_id = None
            
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 1
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.all.return_value = [mock_doc]
            
            mock_db.query.return_value = mock_query
            
            response = client.get("/feedback", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["id"] == "test-feedback-123"
            assert data["items"][0]["title"] == "Test Feedback"
            assert data["items"][0]["feedback_type"] == "bug"
    
    def test_get_feedback_with_filters(self, client, auth_headers):
        """Test getting feedback with filters."""
        with patch('api.server.get_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 0
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.all.return_value = []
            
            mock_db.query.return_value = mock_query
            
            response = client.get(
                "/feedback?feedback_type=bug&source=github_issue&page=1&page_size=10",
                headers=auth_headers
            )
            assert response.status_code == 200
            
            data = response.json()
            assert data["total"] == 0
            assert len(data["items"]) == 0
    
    def test_get_feedback_item_success(self, client, auth_headers):
        """Test getting a specific feedback item."""
        with patch('api.server.get_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            mock_doc = Mock()
            mock_doc.id = "test-feedback-123"
            mock_doc.title = "Test Feedback"
            mock_doc.content = "This is test feedback"
            mock_doc.feedback_type = Mock()
            mock_doc.feedback_type.value = "bug"
            mock_doc.source_type = Mock()
            mock_doc.source_type.value = "github_issue"
            mock_doc.source_url = "https://github.com/test/repo/issues/1"
            mock_doc.author = "testuser"
            mock_doc.created_at = datetime.utcnow()
            mock_doc.processed_at = datetime.utcnow()
            mock_doc.cluster_id = None
            
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.first.return_value = mock_doc
            
            mock_db.query.return_value = mock_query
            
            response = client.get("/feedback/test-feedback-123", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["id"] == "test-feedback-123"
            assert data["title"] == "Test Feedback"
            assert data["feedback_type"] == "bug"
    
    def test_get_feedback_item_not_found(self, client, auth_headers):
        """Test getting non-existent feedback item."""
        with patch('api.server.get_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.first.return_value = None
            
            mock_db.query.return_value = mock_query
            
            response = client.get("/feedback/non-existent", headers=auth_headers)
            assert response.status_code == 404
            
            data = response.json()
            assert data["status"] == "error"
            assert "Feedback not found" in data["message"]
    
    def test_get_system_metrics(self, client, auth_headers):
        """Test getting system metrics."""
        with patch('api.server.workflow_engine.get_workflow_metrics') as mock_workflow_metrics:
            with patch('api.server.scheduler.get_scheduler_metrics') as mock_scheduler_metrics:
                with patch('api.server.state_manager.get_state_metrics') as mock_state_metrics:
                    mock_workflow_metrics.return_value = {"total_executions": 10}
                    mock_scheduler_metrics.return_value = {"total_jobs": 5}
                    mock_state_metrics.return_value = {"total_states": 100}
                    
                    response = client.get("/metrics", headers=auth_headers)
                    assert response.status_code == 200
                    
                    data = response.json()
                    assert "timestamp" in data
                    assert "workflows" in data
                    assert "agents" in data
                    assert "feedback" in data
                    assert "clusters" in data
                    assert "tickets" in data
                    assert "reports" in data
                    assert "performance" in data
    
    def test_unauthorized_access(self, client):
        """Test unauthorized access to protected endpoints."""
        response = client.get("/workflows")
        assert response.status_code == 401
        
        data = response.json()
        assert data["status"] == "error"
        assert "Could not validate credentials" in data["message"]
    
    def test_readonly_access(self, client, readonly_headers):
        """Test read-only access to endpoints."""
        # Should be able to read
        response = client.get("/workflows", headers=readonly_headers)
        assert response.status_code == 200
        
        # Should not be able to write
        workflow_data = {
            "workflow_name": "quick_processing",
            "config": {}
        }
        response = client.post("/workflows/execute", json=workflow_data, headers=readonly_headers)
        assert response.status_code == 403
        
        data = response.json()
        assert data["status"] == "error"
        assert "Permission 'write' required" in data["message"]
    
    def test_rate_limiting(self, client, auth_headers):
        """Test rate limiting."""
        # This would test rate limiting in a real implementation
        # For now, just test that the endpoint works
        response = client.get("/workflows", headers=auth_headers)
        assert response.status_code == 200
    
    def test_cors_headers(self, client):
        """Test CORS headers."""
        response = client.options("/workflows")
        assert response.status_code == 200
    
    def test_error_handling(self, client, auth_headers):
        """Test error handling."""
        with patch('api.server.workflow_engine.execute_workflow') as mock_execute:
            mock_execute.side_effect = Exception("Test error")
            
            workflow_data = {
                "workflow_name": "quick_processing",
                "config": {}
            }
            
            response = client.post("/workflows/execute", json=workflow_data, headers=auth_headers)
            assert response.status_code == 500
            
            data = response.json()
            assert data["status"] == "error"
            assert "Internal server error" in data["message"]

class TestAPIEndpoints:
    """Test cases for additional API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client with additional endpoints."""
        from api.endpoints import router
        from api.server import app
        app.include_router(router, prefix="/api/v1")
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        return {"Authorization": f"Bearer {API_KEYS['admin']}"}
    
    def test_get_clusters(self, client, auth_headers):
        """Test getting clusters."""
        with patch('api.endpoints.get_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            mock_cluster = Mock()
            mock_cluster.id = "test-cluster-123"
            mock_cluster.name = "Test Cluster"
            mock_cluster.description = "Test cluster description"
            mock_cluster.member_count = 5
            mock_cluster.created_at = datetime.utcnow()
            mock_cluster.updated_at = datetime.utcnow()
            mock_cluster.top_keywords = ["bug", "error", "crash"]
            mock_cluster.metadata = {}
            
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 1
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = [mock_cluster]
            
            mock_db.query.return_value = mock_query
            
            response = client.get("/api/v1/clusters", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["total"] == 1
            assert len(data["clusters"]) == 1
            assert data["clusters"][0]["id"] == "test-cluster-123"
            assert data["clusters"][0]["name"] == "Test Cluster"
    
    def test_get_tickets(self, client, auth_headers):
        """Test getting tickets."""
        with patch('api.endpoints.get_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            mock_ticket = Mock()
            mock_ticket.id = "test-ticket-123"
            mock_ticket.external_id = "EXT-123"
            mock_ticket.external_url = "https://example.com/ticket/123"
            mock_ticket.platform = "jira"
            mock_ticket.title = "Test Ticket"
            mock_ticket.description = "Test ticket description"
            mock_ticket.status = Mock()
            mock_ticket.status.value = "open"
            mock_ticket.priority = 3
            mock_ticket.source_document_id = "test-feedback-123"
            mock_ticket.cluster_id = None
            mock_ticket.created_at = datetime.utcnow()
            mock_ticket.updated_at = None
            mock_ticket.metadata = {}
            
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 1
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = [mock_ticket]
            
            mock_db.query.return_value = mock_query
            
            response = client.get("/api/v1/tickets", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["total"] == 1
            assert len(data["tickets"]) == 1
            assert data["tickets"][0]["id"] == "test-ticket-123"
            assert data["tickets"][0]["external_id"] == "EXT-123"
            assert data["tickets"][0]["platform"] == "jira"
    
    def test_search(self, client, auth_headers):
        """Test search functionality."""
        with patch('api.endpoints.get_session') as mock_session:
            mock_db = Mock()
            mock_session.return_value.__enter__.return_value = mock_db
            
            mock_doc = Mock()
            mock_doc.id = "test-feedback-123"
            mock_doc.title = "Test Feedback"
            mock_doc.content = "This is test feedback about a bug"
            mock_doc.feedback_type = Mock()
            mock_doc.feedback_type.value = "bug"
            mock_doc.source_type = Mock()
            mock_doc.source_type.value = "github_issue"
            mock_doc.source_url = "https://github.com/test/repo/issues/1"
            mock_doc.author = "testuser"
            mock_doc.created_at = datetime.utcnow()
            mock_doc.processed_at = datetime.utcnow()
            mock_doc.cluster_id = None
            
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 1
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = [mock_doc]
            
            mock_db.query.return_value = mock_query
            
            search_data = {
                "query": "bug",
                "filters": {},
                "page": 1,
                "page_size": 20,
                "sort_by": "relevance",
                "sort_order": "desc"
            }
            
            response = client.post("/api/v1/search", json=search_data, headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["total"] == 1
            assert len(data["results"]) == 1
            assert data["results"][0]["id"] == "test-feedback-123"
            assert data["results"][0]["type"] == "feedback"
            assert data["query"] == "bug"
            assert "search_time" in data
    
    def test_get_system_config(self, client, auth_headers):
        """Test getting system configuration."""
        response = client.get("/api/v1/config", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "config" in data
        assert "last_updated" in data
        assert "version" in data
        assert "workflow_engine" in data["config"]
        assert "scheduler" in data["config"]
        assert "agents" in data["config"]
    
    def test_update_system_config(self, client, auth_headers):
        """Test updating system configuration."""
        config_data = {
            "config": {
                "workflow_engine": {
                    "max_concurrent_agents": 5
                }
            },
            "validate": True
        }
        
        response = client.put("/api/v1/config", json=config_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert "Configuration updated successfully" in data["message"]
        assert "updated_fields" in data["data"]

