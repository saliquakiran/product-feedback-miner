"""
FastAPI Server for Product Feedback Miner.

This module provides the main API server with all endpoints
for external access to the feedback processing system.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, status, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer
import uvicorn

from api.models import (
    APIResponse, WorkflowExecutionRequest, WorkflowExecutionResponse,
    WorkflowStatusResponse, AgentHealthResponse, AgentControlRequest,
    FeedbackListResponse, FeedbackQueryRequest, FeedbackItem,
    ClusterListResponse, ClusterItem, TicketListResponse, TicketItem,
    ReportListResponse, ReportItem, ReportGenerationRequest,
    ScheduledJobItem, ScheduledJobRequest, JobExecutionResponse,
    SystemHealthResponse, SystemMetricsResponse, SystemConfigResponse,
    ConfigUpdateRequest, LoginRequest, LoginResponse, TokenResponse,
    APIError, PaginationParams, SearchRequest, SearchResponse,
    WebhookRequest, WebhookResponse
)
from api.auth import (
    get_current_user, get_optional_user, require_permission, require_role,
    login, verify_token_endpoint, refresh_token, check_rate_limit,
    get_rate_limit_info
)
from orchestration.workflow import WorkflowEngine
from orchestration.scheduler import PipelineScheduler
from orchestration.state import StateManager
from database import get_session
from database.models import (
    ProcessedDocument, Cluster, Ticket, DigestReport,
    FeedbackType, PriorityLevel, SourceType, ProcessingStatus, TicketStatus
)
from api.endpoints import router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Product Feedback Miner API",
    description="API for the Product Feedback Miner system - intelligent feedback processing and analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Include additional endpoints
app.include_router(router, prefix="/api/v1")

# Initialize core components
workflow_engine = WorkflowEngine()
scheduler = PipelineScheduler(workflow_engine)
state_manager = StateManager()

# Security
security = HTTPBearer()

# Rate limiting configuration
RATE_LIMITS = {
    "default": {"limit": 100, "window": 3600},  # 100 requests per hour
    "workflow": {"limit": 10, "window": 3600},  # 10 workflow executions per hour
    "reports": {"limit": 20, "window": 3600},   # 20 report generations per hour
    "admin": {"limit": 1000, "window": 3600},   # 1000 requests per hour for admin
}

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            status="error",
            message=exc.detail,
            data={"status_code": exc.status_code}
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=APIResponse(
            status="error",
            message="Internal server error",
            data={"error": str(exc)}
        ).dict()
    )

# Middleware for rate limiting
@app.middleware("http")
async def rate_limit_middleware(request, call_next):
    """Rate limiting middleware."""
    # Get client identifier
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")
    identifier = f"{client_ip}:{user_agent}"
    
    # Get rate limit for endpoint
    endpoint = request.url.path
    if "/workflows/" in endpoint:
        limit_config = RATE_LIMITS["workflow"]
    elif "/reports/" in endpoint:
        limit_config = RATE_LIMITS["reports"]
    elif "/admin/" in endpoint:
        limit_config = RATE_LIMITS["admin"]
    else:
        limit_config = RATE_LIMITS["default"]
    
    # Check rate limit
    if not check_rate_limit(identifier, limit_config["limit"], limit_config["window"]):
        return JSONResponse(
            status_code=429,
            content=APIResponse(
                status="error",
                message="Rate limit exceeded",
                data=limit_config
            ).dict()
        )
    
    response = await call_next(request)
    return response

# Health check endpoint
@app.get("/health", response_model=SystemHealthResponse)
async def health_check():
    """System health check."""
    try:
        # Get agent health
        agent_health = await workflow_engine.get_agent_health()
        agents = [
            AgentHealthResponse(
                agent_name=name,
                status=health["status"],
                message=health["message"],
                last_check=datetime.utcnow(),
                metrics=health.get("metrics", {})
            )
            for name, health in agent_health.items()
        ]
        
        # Get system metrics
        workflow_metrics = await workflow_engine.get_workflow_metrics()
        state_metrics = await state_manager.get_state_metrics()
        
        return SystemHealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            uptime=0.0,  # Would be calculated from start time
            version="1.0.0",
            agents=agents,
            workflows=workflow_metrics,
            database={"status": "connected"},
            memory_usage={"used": 0, "total": 0},
            cpu_usage={"percent": 0}
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return SystemHealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            uptime=0.0,
            version="1.0.0",
            agents=[],
            workflows={},
            database={"status": "error", "error": str(e)},
            memory_usage={"used": 0, "total": 0},
            cpu_usage={"percent": 0}
        )

# Authentication endpoints
@app.post("/auth/login", response_model=LoginResponse)
async def login_endpoint(login_request: LoginRequest):
    """Authenticate user and return JWT token."""
    return await login(login_request)

@app.post("/auth/verify", response_model=TokenResponse)
async def verify_token(token: str):
    """Verify JWT token."""
    return await verify_token_endpoint(token)

@app.post("/auth/refresh", response_model=LoginResponse)
async def refresh_token_endpoint(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Refresh JWT token."""
    return await refresh_token(current_user)

# Workflow endpoints
@app.post("/workflows/execute", response_model=WorkflowExecutionResponse)
@require_permission("write")
async def execute_workflow(
    request: WorkflowExecutionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Execute a workflow."""
    try:
        execution = await workflow_engine.execute_workflow(
            workflow_name=request.workflow_name,
            config=request.config,
            execution_id=request.execution_id
        )
        
        return WorkflowExecutionResponse(
            execution_id=execution.execution_id,
            workflow_name=execution.workflow_name,
            status=execution.status.value,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            duration=execution.total_duration,
            steps_completed=execution.steps_completed,
            steps_failed=execution.steps_failed,
            steps_total=execution.steps_total,
            error_message=execution.error_message,
            metadata=execution.metadata
        )
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/workflows/{execution_id}/status", response_model=WorkflowStatusResponse)
@require_permission("read")
async def get_workflow_status(
    execution_id: str = Path(..., description="Workflow execution ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get workflow execution status."""
    try:
        execution = await workflow_engine.get_workflow_status(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Workflow execution not found")
        
        progress = (execution.steps_completed / execution.steps_total * 100) if execution.steps_total > 0 else 0
        
        return WorkflowStatusResponse(
            execution_id=execution.execution_id,
            workflow_name=execution.workflow_name,
            status=execution.status.value,
            progress=progress,
            current_step=None,  # Would be tracked in pipeline state
            steps_completed=execution.steps_completed,
            steps_total=execution.steps_total,
            started_at=execution.started_at,
            estimated_completion=None,  # Would be calculated
            error_message=execution.error_message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/workflows/{execution_id}/cancel")
@require_permission("write")
async def cancel_workflow(
    execution_id: str = Path(..., description="Workflow execution ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Cancel a workflow execution."""
    try:
        success = await workflow_engine.cancel_workflow(execution_id)
        if not success:
            raise HTTPException(status_code=404, detail="Workflow execution not found")
        
        return APIResponse(
            status="success",
            message="Workflow cancelled successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/workflows", response_model=List[str])
@require_permission("read")
async def list_workflows(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List available workflows."""
    return workflow_engine.get_available_workflows()

# Agent endpoints
@app.get("/agents/status", response_model=List[AgentHealthResponse])
@require_permission("read")
async def get_agents_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get status of all agents."""
    try:
        agent_health = await workflow_engine.get_agent_health()
        return [
            AgentHealthResponse(
                agent_name=name,
                status=health["status"],
                message=health["message"],
                last_check=datetime.utcnow(),
                metrics=health.get("metrics", {})
            )
            for name, health in agent_health.items()
        ]
    except Exception as e:
        logger.error(f"Failed to get agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agents/{agent_name}/start")
@require_permission("admin")
async def start_agent(
    agent_name: str = Path(..., description="Agent name"),
    request: AgentControlRequest = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Start an agent."""
    # This would implement agent starting logic
    return APIResponse(
        status="success",
        message=f"Agent {agent_name} started successfully"
    )

@app.post("/agents/{agent_name}/stop")
@require_permission("admin")
async def stop_agent(
    agent_name: str = Path(..., description="Agent name"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Stop an agent."""
    # This would implement agent stopping logic
    return APIResponse(
        status="success",
        message=f"Agent {agent_name} stopped successfully"
    )

# Feedback endpoints
@app.get("/feedback", response_model=FeedbackListResponse)
@require_permission("read")
async def get_feedback(
    query: FeedbackQueryRequest = Depends(),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get feedback items with filtering and pagination."""
    try:
        with get_session() as session:
            # Build query
            db_query = session.query(ProcessedDocument)
            
            # Apply filters
            if query.feedback_type:
                db_query = db_query.filter(ProcessedDocument.feedback_type == query.feedback_type.value)
            
            if query.source:
                db_query = db_query.filter(ProcessedDocument.source_type == query.source)
            
            if query.cluster_id:
                db_query = db_query.filter(ProcessedDocument.cluster_id == query.cluster_id)
            
            if query.date_from:
                db_query = db_query.filter(ProcessedDocument.created_at >= query.date_from)
            
            if query.date_to:
                db_query = db_query.filter(ProcessedDocument.created_at <= query.date_to)
            
            if query.search:
                db_query = db_query.filter(
                    ProcessedDocument.content.ilike(f"%{query.search}%")
                )
            
            # Get total count
            total = db_query.count()
            
            # Apply pagination
            offset = (query.page - 1) * query.page_size
            db_query = db_query.offset(offset).limit(query.page_size)
            
            # Apply sorting
            if query.sort_by == "created_at":
                if query.sort_order == "desc":
                    db_query = db_query.order_by(ProcessedDocument.created_at.desc())
                else:
                    db_query = db_query.order_by(ProcessedDocument.created_at.asc())
            
            # Execute query
            documents = db_query.all()
            
            # Convert to response format
            items = []
            for doc in documents:
                items.append(FeedbackItem(
                    id=str(doc.id),
                    title=doc.title or "Untitled",
                    content=doc.content or "",
                    feedback_type=doc.feedback_type.value if doc.feedback_type else "other",
                    priority="medium",  # Would be calculated from priority score
                    source=doc.source_type.value if doc.source_type else "unknown",
                    source_url=doc.source_url,
                    author=doc.author,
                    created_at=doc.created_at,
                    processed_at=doc.processed_at,
                    cluster_id=str(doc.cluster_id) if doc.cluster_id else None,
                    ticket_id=None,  # Would be looked up from tickets table
                    metadata={}
                ))
            
            return FeedbackListResponse(
                items=items,
                total=total,
                page=query.page,
                page_size=query.page_size,
                has_next=offset + query.page_size < total,
                has_previous=query.page > 1
            )
    
    except Exception as e:
        logger.error(f"Failed to get feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/feedback/{feedback_id}", response_model=FeedbackItem)
@require_permission("read")
async def get_feedback_item(
    feedback_id: str = Path(..., description="Feedback ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a specific feedback item."""
    try:
        with get_session() as session:
            doc = session.query(ProcessedDocument).filter(ProcessedDocument.id == feedback_id).first()
            if not doc:
                raise HTTPException(status_code=404, detail="Feedback not found")
            
            return FeedbackItem(
                id=str(doc.id),
                title=doc.title or "Untitled",
                content=doc.content or "",
                feedback_type=doc.feedback_type.value if doc.feedback_type else "other",
                priority="medium",
                source=doc.source_type.value if doc.source_type else "unknown",
                source_url=doc.source_url,
                author=doc.author,
                created_at=doc.created_at,
                processed_at=doc.processed_at,
                cluster_id=str(doc.cluster_id) if doc.cluster_id else None,
                ticket_id=None,
                metadata={}
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get feedback item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System metrics endpoint
@app.get("/metrics", response_model=SystemMetricsResponse)
@require_permission("read")
async def get_system_metrics(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get system metrics."""
    try:
        workflow_metrics = await workflow_engine.get_workflow_metrics()
        scheduler_metrics = await scheduler.get_scheduler_metrics()
        state_metrics = await state_manager.get_state_metrics()
        
        return SystemMetricsResponse(
            timestamp=datetime.utcnow(),
            workflows=workflow_metrics,
            agents={},  # Would be populated with agent metrics
            feedback={"total": 0, "processed": 0, "pending": 0},
            clusters={"total": 0, "active": 0},
            tickets={"total": 0, "open": 0, "closed": 0},
            reports={"total": 0, "generated_today": 0},
            performance=state_metrics
        )
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Root endpoint
@app.get("/", response_model=APIResponse)
async def root():
    """Root endpoint with API information."""
    return APIResponse(
        status="success",
        message="Product Feedback Miner API",
        data={
            "version": "1.0.0",
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "health_url": "/health"
        }
    )

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Product Feedback Miner API...")
    
    # Start scheduler
    await scheduler.start()
    
    # Start state manager cleanup
    await state_manager.start_cleanup_task()
    
    logger.info("API startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Product Feedback Miner API...")
    
    # Stop scheduler
    await scheduler.stop()
    
    # Shutdown state manager
    await state_manager.shutdown()
    
    # Shutdown workflow engine
    await workflow_engine.shutdown()
    
    logger.info("API shutdown complete")

# Run the server
if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
