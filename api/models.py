"""
API Models for Product Feedback Miner.

This module defines Pydantic models for API request/response validation,
data serialization, and API documentation.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid

# Enums for API responses
class APIStatus(str, Enum):
    """API response status."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"

class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentStatus(str, Enum):
    """Agent execution status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class PriorityLevel(str, Enum):
    """Priority levels for feedback."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"

class FeedbackType(str, Enum):
    """Types of feedback."""
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    UX = "ux"
    PRICING = "pricing"
    DOCS = "docs"
    OTHER = "other"

# Base API Response Model
class APIResponse(BaseModel):
    """Standard API response format."""
    status: APIStatus
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Workflow Models
class WorkflowExecutionRequest(BaseModel):
    """Request to execute a workflow."""
    workflow_name: str = Field(..., description="Name of the workflow to execute")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Workflow configuration")
    execution_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Optional execution ID")

class WorkflowExecutionResponse(BaseModel):
    """Response from workflow execution."""
    execution_id: str
    workflow_name: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    steps_completed: int = 0
    steps_failed: int = 0
    steps_total: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class WorkflowStatusResponse(BaseModel):
    """Workflow status response."""
    execution_id: str
    workflow_name: str
    status: WorkflowStatus
    progress: float = Field(..., ge=0, le=100, description="Progress percentage")
    current_step: Optional[str] = None
    steps_completed: int
    steps_total: int
    started_at: datetime
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Agent Models
class AgentHealthResponse(BaseModel):
    """Agent health status response."""
    agent_name: str
    status: AgentStatus
    message: str
    last_check: datetime
    uptime: Optional[float] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AgentControlRequest(BaseModel):
    """Request to control an agent."""
    action: str = Field(..., description="Action to perform: start, stop, restart, status")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Agent configuration")

# Feedback Models
class FeedbackItem(BaseModel):
    """Feedback item response."""
    id: str
    title: str
    content: str
    feedback_type: FeedbackType
    priority: PriorityLevel
    source: str
    source_url: Optional[str] = None
    author: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    cluster_id: Optional[str] = None
    ticket_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FeedbackListResponse(BaseModel):
    """List of feedback items."""
    items: List[FeedbackItem]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

class FeedbackQueryRequest(BaseModel):
    """Request to query feedback items."""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    feedback_type: Optional[FeedbackType] = None
    priority: Optional[PriorityLevel] = None
    source: Optional[str] = None
    cluster_id: Optional[str] = None
    ticket_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", description="Sort order: asc or desc")

    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('sort_order must be "asc" or "desc"')
        return v

# Cluster Models
class ClusterItem(BaseModel):
    """Cluster item response."""
    id: str
    name: str
    description: Optional[str] = None
    member_count: int
    created_at: datetime
    updated_at: datetime
    top_keywords: List[str] = Field(default_factory=list)
    representative_feedback: Optional[FeedbackItem] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ClusterListResponse(BaseModel):
    """List of clusters."""
    clusters: List[ClusterItem]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

# Ticket Models
class TicketItem(BaseModel):
    """Ticket item response."""
    id: str
    external_id: str
    external_url: str
    platform: str
    title: str
    description: Optional[str] = None
    status: str
    priority: int
    source_feedback_id: str
    cluster_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TicketListResponse(BaseModel):
    """List of tickets."""
    tickets: List[TicketItem]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

# Report Models
class ReportItem(BaseModel):
    """Report item response."""
    id: str
    report_type: str
    title: str
    content: str
    format: str
    generated_at: datetime
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ReportListResponse(BaseModel):
    """List of reports."""
    reports: List[ReportItem]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

class ReportGenerationRequest(BaseModel):
    """Request to generate a report."""
    report_type: str = Field(..., description="Type of report to generate")
    format: str = Field(default="html", description="Report format: html, markdown, json, pdf")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_charts: bool = Field(default=True, description="Include charts in report")
    include_raw_data: bool = Field(default=False, description="Include raw data in report")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Report filters")

# Job/Scheduling Models
class ScheduledJobItem(BaseModel):
    """Scheduled job item response."""
    id: str
    name: str
    description: Optional[str] = None
    workflow_name: str
    schedule_type: str
    schedule_value: str
    timezone: str
    enabled: bool
    max_concurrent: int
    timeout: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    config: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ScheduledJobRequest(BaseModel):
    """Request to create/update a scheduled job."""
    name: str = Field(..., description="Job name")
    description: Optional[str] = None
    workflow_name: str = Field(..., description="Workflow to execute")
    schedule_type: str = Field(..., description="Schedule type: cron, interval, once")
    schedule_value: str = Field(..., description="Schedule value (cron expression or interval)")
    timezone: str = Field(default="UTC", description="Timezone for scheduling")
    enabled: bool = Field(default=True, description="Whether job is enabled")
    max_concurrent: int = Field(default=1, ge=1, description="Maximum concurrent executions")
    timeout: Optional[int] = Field(None, ge=1, description="Job timeout in seconds")
    config: Dict[str, Any] = Field(default_factory=dict, description="Job configuration")

class JobExecutionResponse(BaseModel):
    """Job execution response."""
    execution_id: str
    job_id: str
    workflow_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# System Models
class SystemHealthResponse(BaseModel):
    """System health response."""
    status: str
    timestamp: datetime
    uptime: float
    version: str
    agents: List[AgentHealthResponse]
    workflows: Dict[str, Any] = Field(default_factory=dict)
    database: Dict[str, Any] = Field(default_factory=dict)
    memory_usage: Dict[str, Any] = Field(default_factory=dict)
    cpu_usage: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SystemMetricsResponse(BaseModel):
    """System metrics response."""
    timestamp: datetime
    workflows: Dict[str, Any] = Field(default_factory=dict)
    agents: Dict[str, Any] = Field(default_factory=dict)
    feedback: Dict[str, Any] = Field(default_factory=dict)
    clusters: Dict[str, Any] = Field(default_factory=dict)
    tickets: Dict[str, Any] = Field(default_factory=dict)
    reports: Dict[str, Any] = Field(default_factory=dict)
    performance: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Configuration Models
class SystemConfigResponse(BaseModel):
    """System configuration response."""
    config: Dict[str, Any]
    last_updated: datetime
    version: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ConfigUpdateRequest(BaseModel):
    """Request to update system configuration."""
    config: Dict[str, Any] = Field(..., description="Configuration updates")
    validate: bool = Field(default=True, description="Validate configuration before applying")

# Authentication Models
class LoginRequest(BaseModel):
    """Login request."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

class LoginResponse(BaseModel):
    """Login response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class TokenResponse(BaseModel):
    """Token validation response."""
    valid: bool
    user: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Error Models
class APIError(BaseModel):
    """API error response."""
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Pagination Models
class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

class PaginatedResponse(BaseModel):
    """Paginated response base."""
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

    @property
    def total_pages(self) -> int:
        """Calculate total pages."""
        return (self.total + self.page_size - 1) // self.page_size

# Search Models
class SearchRequest(BaseModel):
    """Search request."""
    query: str = Field(..., description="Search query")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Search filters")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: str = Field(default="relevance", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order")

class SearchResponse(BaseModel):
    """Search response."""
    results: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool
    query: str
    filters: Dict[str, Any]
    search_time: float

# Webhook Models
class WebhookRequest(BaseModel):
    """Webhook request."""
    url: str = Field(..., description="Webhook URL")
    events: List[str] = Field(..., description="Events to subscribe to")
    secret: Optional[str] = Field(None, description="Webhook secret for verification")
    enabled: bool = Field(default=True, description="Whether webhook is enabled")

class WebhookResponse(BaseModel):
    """Webhook response."""
    id: str
    url: str
    events: List[str]
    enabled: bool
    created_at: datetime
    last_triggered: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

