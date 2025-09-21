# Product Feedback Miner API Reference

The Product Feedback Miner API provides REST endpoints for external access to the feedback processing system. This document describes all available endpoints, authentication, and usage examples.

## Table of Contents

- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
- [Data Models](#data-models)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

## Getting Started

### Installation

The API server is included with the Product Feedback Miner. To start the server:

```bash
# Install dependencies
pip install -r requirements.txt

# Start the API server
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

### Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

### API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## Authentication

The API supports two authentication methods:

### 1. JWT Token Authentication

Login with username and password to get a JWT token:

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "username": "admin",
    "role": "admin",
    "permissions": ["read", "write", "delete", "admin"]
  }
}
```

### 2. API Key Authentication

Use API keys for programmatic access:

```bash
curl -X GET "http://localhost:8000/workflows" \
  -H "Authorization: Bearer admin-key-12345"
```

### Default Credentials

| Username | Password | Role | Permissions |
|----------|----------|------|-------------|
| admin | admin123 | admin | read, write, delete, admin |
| analyst | analyst123 | analyst | read, write |
| readonly | readonly123 | readonly | read |

### Default API Keys

| Key | Role | Permissions |
|-----|------|-------------|
| admin-key-12345 | admin | read, write, delete, admin |
| analyst-key-11111 | analyst | read, write |
| readonly-key-67890 | readonly | read |

## API Endpoints

### Authentication Endpoints

#### POST /auth/login
Login with username and password.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "username": "string",
    "role": "string",
    "permissions": ["string"]
  }
}
```

#### POST /auth/verify
Verify a JWT token.

**Parameters:**
- `token` (string): JWT token to verify

**Response:**
```json
{
  "valid": true,
  "user": {
    "username": "string",
    "role": "string"
  },
  "expires_at": "2024-01-01T00:00:00Z"
}
```

#### POST /auth/refresh
Refresh JWT token.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "username": "string",
    "role": "string",
    "permissions": ["string"]
  }
}
```

### System Endpoints

#### GET /health
Get system health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "uptime": 3600.0,
  "version": "1.0.0",
  "agents": [
    {
      "agent_name": "ingestor",
      "status": "healthy",
      "message": "OK",
      "last_check": "2024-01-01T00:00:00Z",
      "uptime": 3600.0,
      "metrics": {}
    }
  ],
  "workflows": {},
  "database": {"status": "connected"},
  "memory_usage": {"used": 0, "total": 0},
  "cpu_usage": {"percent": 0}
}
```

#### GET /metrics
Get system metrics.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "workflows": {
    "total_executions": 100,
    "successful_executions": 95,
    "failed_executions": 5
  },
  "agents": {},
  "feedback": {
    "total": 1000,
    "processed": 950,
    "pending": 50
  },
  "clusters": {
    "total": 50,
    "active": 45
  },
  "tickets": {
    "total": 200,
    "open": 150,
    "closed": 50
  },
  "reports": {
    "total": 25,
    "generated_today": 3
  },
  "performance": {}
}
```

### Workflow Endpoints

#### GET /workflows
List available workflows.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
["feedback_processing", "quick_processing", "deep_analysis", "report_generation"]
```

#### POST /workflows/execute
Execute a workflow.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "workflow_name": "quick_processing",
  "config": {
    "max_items": 100,
    "test_mode": false
  },
  "execution_id": "optional-execution-id"
}
```

**Response:**
```json
{
  "execution_id": "exec-123",
  "workflow_name": "quick_processing",
  "status": "running",
  "started_at": "2024-01-01T00:00:00Z",
  "completed_at": null,
  "duration": null,
  "steps_completed": 0,
  "steps_failed": 0,
  "steps_total": 5,
  "error_message": null,
  "metadata": {}
}
```

#### GET /workflows/{execution_id}/status
Get workflow execution status.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "execution_id": "exec-123",
  "workflow_name": "quick_processing",
  "status": "running",
  "progress": 60.0,
  "current_step": "classifier",
  "steps_completed": 3,
  "steps_total": 5,
  "started_at": "2024-01-01T00:00:00Z",
  "estimated_completion": "2024-01-01T00:05:00Z",
  "error_message": null
}
```

#### DELETE /workflows/{execution_id}/cancel
Cancel a workflow execution.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "status": "success",
  "message": "Workflow cancelled successfully"
}
```

### Agent Endpoints

#### GET /agents/status
Get status of all agents.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
[
  {
    "agent_name": "ingestor",
    "status": "healthy",
    "message": "OK",
    "last_check": "2024-01-01T00:00:00Z",
    "uptime": 3600.0,
    "metrics": {
      "items_processed": 1000,
      "success_rate": 0.95
    }
  }
]
```

#### POST /agents/{agent_name}/start
Start an agent.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "action": "start",
  "config": {}
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Agent ingestor started successfully"
}
```

#### POST /agents/{agent_name}/stop
Stop an agent.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "status": "success",
  "message": "Agent ingestor stopped successfully"
}
```

### Feedback Endpoints

#### GET /feedback
Get feedback items with filtering and pagination.

**Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 20, max: 100)
- `feedback_type` (string): Filter by feedback type (bug, feature_request, ux, pricing, docs, other)
- `priority` (string): Filter by priority (critical, high, medium, low, minimal)
- `source` (string): Filter by source (github_issue, hackernews, exa, manual)
- `cluster_id` (string): Filter by cluster ID
- `ticket_id` (string): Filter by ticket ID
- `date_from` (datetime): Filter by creation date (from)
- `date_to` (datetime): Filter by creation date (to)
- `search` (string): Search in content
- `sort_by` (string): Sort field (default: created_at)
- `sort_order` (string): Sort order (asc, desc, default: desc)

**Response:**
```json
{
  "items": [
    {
      "id": "feedback-123",
      "title": "Bug in login system",
      "content": "Users cannot login with special characters...",
      "feedback_type": "bug",
      "priority": "high",
      "source": "github_issue",
      "source_url": "https://github.com/user/repo/issues/123",
      "author": "user123",
      "created_at": "2024-01-01T00:00:00Z",
      "processed_at": "2024-01-01T00:01:00Z",
      "cluster_id": "cluster-456",
      "ticket_id": "ticket-789",
      "metadata": {}
    }
  ],
  "total": 1000,
  "page": 1,
  "page_size": 20,
  "has_next": true,
  "has_previous": false
}
```

#### GET /feedback/{feedback_id}
Get a specific feedback item.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "feedback-123",
  "title": "Bug in login system",
  "content": "Users cannot login with special characters...",
  "feedback_type": "bug",
  "priority": "high",
  "source": "github_issue",
  "source_url": "https://github.com/user/repo/issues/123",
  "author": "user123",
  "created_at": "2024-01-01T00:00:00Z",
  "processed_at": "2024-01-01T00:01:00Z",
  "cluster_id": "cluster-456",
  "ticket_id": "ticket-789",
  "metadata": {}
}
```

### Cluster Endpoints

#### GET /api/v1/clusters
Get clusters with pagination and search.

**Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 20, max: 100)
- `search` (string): Search in cluster name

**Response:**
```json
{
  "clusters": [
    {
      "id": "cluster-456",
      "name": "Login Issues",
      "description": "Feedback related to login problems",
      "member_count": 15,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "top_keywords": ["login", "password", "authentication"],
      "representative_feedback": {
        "id": "feedback-123",
        "title": "Bug in login system",
        "content": "Users cannot login...",
        "feedback_type": "bug",
        "priority": "high",
        "source": "github_issue",
        "source_url": "https://github.com/user/repo/issues/123",
        "author": "user123",
        "created_at": "2024-01-01T00:00:00Z",
        "processed_at": "2024-01-01T00:01:00Z",
        "cluster_id": "cluster-456",
        "ticket_id": "ticket-789",
        "metadata": {}
      },
      "metadata": {}
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20,
  "has_next": true,
  "has_previous": false
}
```

#### GET /api/v1/clusters/{cluster_id}
Get a specific cluster.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "cluster-456",
  "name": "Login Issues",
  "description": "Feedback related to login problems",
  "member_count": 15,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "top_keywords": ["login", "password", "authentication"],
  "representative_feedback": {
    "id": "feedback-123",
    "title": "Bug in login system",
    "content": "Users cannot login...",
    "feedback_type": "bug",
    "priority": "high",
    "source": "github_issue",
    "source_url": "https://github.com/user/repo/issues/123",
    "author": "user123",
    "created_at": "2024-01-01T00:00:00Z",
    "processed_at": "2024-01-01T00:01:00Z",
    "cluster_id": "cluster-456",
    "ticket_id": "ticket-789",
    "metadata": {}
  },
  "metadata": {}
}
```

### Ticket Endpoints

#### GET /api/v1/tickets
Get tickets with pagination and filtering.

**Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 20, max: 100)
- `status` (string): Filter by ticket status (open, in_progress, closed, cancelled)
- `platform` (string): Filter by platform (jira, github, linear)

**Response:**
```json
{
  "tickets": [
    {
      "id": "ticket-789",
      "external_id": "PROJ-123",
      "external_url": "https://company.atlassian.net/browse/PROJ-123",
      "platform": "jira",
      "title": "Fix login bug with special characters",
      "description": "Users cannot login when using special characters in password",
      "status": "open",
      "priority": 3,
      "source_feedback_id": "feedback-123",
      "cluster_id": "cluster-456",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "metadata": {}
    }
  ],
  "total": 200,
  "page": 1,
  "page_size": 20,
  "has_next": true,
  "has_previous": false
}
```

#### GET /api/v1/tickets/{ticket_id}
Get a specific ticket.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "ticket-789",
  "external_id": "PROJ-123",
  "external_url": "https://company.atlassian.net/browse/PROJ-123",
  "platform": "jira",
  "title": "Fix login bug with special characters",
  "description": "Users cannot login when using special characters in password",
  "status": "open",
  "priority": 3,
  "source_feedback_id": "feedback-123",
  "cluster_id": "cluster-456",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "metadata": {}
}
```

### Report Endpoints

#### GET /api/v1/reports
Get reports with pagination and filtering.

**Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 20, max: 100)
- `report_type` (string): Filter by report type

**Response:**
```json
{
  "reports": [
    {
      "id": "report-456",
      "report_type": "executive_summary",
      "title": "Weekly Executive Summary",
      "content": "<html><body><h1>Executive Summary</h1>...</body></html>",
      "format": "html",
      "generated_at": "2024-01-01T00:00:00Z",
      "start_date": "2023-12-25T00:00:00Z",
      "end_date": "2024-01-01T00:00:00Z",
      "metadata": {}
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 20,
  "has_next": true,
  "has_previous": false
}
```

#### POST /api/v1/reports/generate
Generate a new report.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "report_type": "executive_summary",
  "format": "html",
  "start_date": "2023-12-25T00:00:00Z",
  "end_date": "2024-01-01T00:00:00Z",
  "include_charts": true,
  "include_raw_data": false,
  "filters": {
    "feedback_type": "bug",
    "priority": "high"
  }
}
```

**Response:**
```json
{
  "id": "report-456",
  "report_type": "executive_summary",
  "title": "Executive Summary Report",
  "content": "<html><body><h1>Executive Summary</h1>...</body></html>",
  "format": "html",
  "generated_at": "2024-01-01T00:00:00Z",
  "start_date": "2023-12-25T00:00:00Z",
  "end_date": "2024-01-01T00:00:00Z",
  "metadata": {}
}
```

### Search Endpoints

#### POST /api/v1/search
Search across all data.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "query": "login bug",
  "filters": {
    "feedback_type": "bug",
    "source": "github_issue"
  },
  "page": 1,
  "page_size": 20,
  "sort_by": "relevance",
  "sort_order": "desc"
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "feedback-123",
      "type": "feedback",
      "title": "Bug in login system",
      "content": "Users cannot login with special characters...",
      "feedback_type": "bug",
      "source": "github_issue",
      "created_at": "2024-01-01T00:00:00Z",
      "relevance_score": 0.95
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20,
  "has_next": true,
  "has_previous": false,
  "query": "login bug",
  "filters": {
    "feedback_type": "bug",
    "source": "github_issue"
  },
  "search_time": 0.123
}
```

### Configuration Endpoints

#### GET /api/v1/config
Get system configuration.

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "config": {
    "workflow_engine": {
      "max_concurrent_agents": 3,
      "default_timeout": 300,
      "retry_delay": 30
    },
    "scheduler": {
      "enabled": true,
      "max_concurrent_jobs": 5
    },
    "agents": {
      "ingestor": {"enabled": true, "timeout": 600},
      "classifier": {"enabled": true, "timeout": 300}
    }
  },
  "last_updated": "2024-01-01T00:00:00Z",
  "version": "1.0.0"
}
```

#### PUT /api/v1/config
Update system configuration.

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "config": {
    "workflow_engine": {
      "max_concurrent_agents": 5
    }
  },
  "validate": true
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Configuration updated successfully",
  "data": {
    "updated_fields": ["workflow_engine.max_concurrent_agents"]
  }
}
```

## Data Models

### Common Fields

All API responses include these common fields:

- `status`: Response status (success, error, warning)
- `message`: Human-readable message
- `data`: Response data (optional)
- `timestamp`: Response timestamp
- `request_id`: Request ID for tracking (optional)

### Pagination

Paginated responses include:

- `total`: Total number of items
- `page`: Current page number
- `page_size`: Items per page
- `has_next`: Whether there are more pages
- `has_previous`: Whether there are previous pages

### Enums

#### FeedbackType
- `bug`: Bug reports
- `feature_request`: Feature requests
- `ux`: User experience feedback
- `pricing`: Pricing feedback
- `docs`: Documentation feedback
- `other`: Other types

#### PriorityLevel
- `critical`: Critical priority
- `high`: High priority
- `medium`: Medium priority
- `low`: Low priority
- `minimal`: Minimal priority

#### WorkflowStatus
- `pending`: Workflow is pending
- `running`: Workflow is running
- `completed`: Workflow completed successfully
- `failed`: Workflow failed
- `cancelled`: Workflow was cancelled

#### AgentStatus
- `healthy`: Agent is healthy
- `unhealthy`: Agent is unhealthy
- `unknown`: Agent status is unknown

## Error Handling

The API uses standard HTTP status codes and returns error details in the response body.

### HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
  "status": "error",
  "message": "Error description",
  "data": {
    "error_code": "VALIDATION_ERROR",
    "details": {
      "field": "username",
      "message": "Username is required"
    }
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "req-123"
}
```

### Common Error Codes

- `VALIDATION_ERROR`: Request validation failed
- `AUTHENTICATION_ERROR`: Authentication failed
- `AUTHORIZATION_ERROR`: Insufficient permissions
- `NOT_FOUND`: Resource not found
- `RATE_LIMIT_EXCEEDED`: Rate limit exceeded
- `INTERNAL_ERROR`: Internal server error

## Rate Limiting

The API implements rate limiting to prevent abuse:

### Rate Limits

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Default | 100 requests | 1 hour |
| Workflow execution | 10 requests | 1 hour |
| Report generation | 20 requests | 1 hour |
| Admin endpoints | 1000 requests | 1 hour |

### Rate Limit Headers

Responses include rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

### Rate Limit Exceeded

When rate limit is exceeded:

```json
{
  "status": "error",
  "message": "Rate limit exceeded",
  "data": {
    "limit": 100,
    "window": 3600,
    "retry_after": 300
  }
}
```

## Examples

### Python Client

```python
import asyncio
import aiohttp

async def main():
    async with aiohttp.ClientSession() as session:
        # Login
        async with session.post(
            "http://localhost:8000/auth/login",
            json={"username": "admin", "password": "admin123"}
        ) as response:
            data = await response.json()
            token = data["access_token"]
        
        # Execute workflow
        headers = {"Authorization": f"Bearer {token}"}
        async with session.post(
            "http://localhost:8000/workflows/execute",
            json={"workflow_name": "quick_processing"},
            headers=headers
        ) as response:
            data = await response.json()
            execution_id = data["execution_id"]
        
        # Get feedback
        async with session.get(
            "http://localhost:8000/feedback?page=1&page_size=10",
            headers=headers
        ) as response:
            data = await response.json()
            print(f"Found {data['total']} feedback items")

asyncio.run(main())
```

### cURL Examples

```bash
# Login
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Execute workflow
curl -X POST "http://localhost:8000/workflows/execute" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"workflow_name": "quick_processing"}'

# Get feedback
curl -X GET "http://localhost:8000/feedback?page=1&page_size=10" \
  -H "Authorization: Bearer <token>"

# Search
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "bug", "page": 1, "page_size": 10}'
```

### JavaScript Client

```javascript
class ProductFeedbackMinerAPI {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.token = null;
  }
  
  async login(username, password) {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    const data = await response.json();
    this.token = data.access_token;
    return data;
  }
  
  async getFeedback(page = 1, pageSize = 20) {
    const response = await fetch(
      `${this.baseUrl}/feedback?page=${page}&page_size=${pageSize}`,
      { headers: { 'Authorization': `Bearer ${this.token}` }}
    );
    
    return await response.json();
  }
  
  async executeWorkflow(workflowName, config = {}) {
    const response = await fetch(`${this.baseUrl}/workflows/execute`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ workflow_name: workflowName, config })
    });
    
    return await response.json();
  }
}

// Usage
const api = new ProductFeedbackMinerAPI();
await api.login('admin', 'admin123');
const feedback = await api.getFeedback();
console.log(feedback);
```

## Support

For API support and questions:

- **Documentation**: Visit `/docs` for interactive API documentation
- **Issues**: Report issues on the project repository
- **Email**: Contact the development team

## Changelog

### Version 1.0.0
- Initial API release
- Authentication and authorization
- Workflow management
- Agent control
- Feedback, cluster, and ticket management
- Report generation
- Search functionality
- System monitoring and metrics

