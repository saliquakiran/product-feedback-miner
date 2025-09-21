"""
Additional API endpoints for Product Feedback Miner.

This module contains additional endpoints for clusters, tickets,
reports, scheduling, and other system functionality.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, status, Query, Path
from sqlalchemy.orm import Session

from api.models import (
    ClusterListResponse, ClusterItem, TicketListResponse, TicketItem,
    ReportListResponse, ReportItem, ReportGenerationRequest,
    ScheduledJobItem, ScheduledJobRequest, JobExecutionResponse,
    SystemConfigResponse, ConfigUpdateRequest, SearchRequest, SearchResponse,
    WebhookRequest, WebhookResponse, APIResponse, PaginationParams
)
from api.auth import get_current_user, require_permission, require_role
from database import get_session
from database.models import (
    Cluster, Ticket, DigestReport, ProcessedDocument,
    FeedbackType, PriorityLevel, SourceType, ProcessingStatus, TicketStatus
)
from orchestration.workflow import WorkflowEngine
from orchestration.scheduler import PipelineScheduler, ScheduleType
from orchestration.state import StateManager

logger = logging.getLogger(__name__)

# Create router for additional endpoints
router = APIRouter()

# Cluster endpoints
@router.get("/clusters", response_model=ClusterListResponse)
@require_permission("read")
async def get_clusters(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search query"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get clusters with pagination and search."""
    try:
        # Build query
        query = db.query(Cluster)
        
        if search:
            query = query.filter(Cluster.name.ilike(f"%{search}%"))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        clusters = query.offset(offset).limit(page_size).all()
        
        # Convert to response format
        cluster_items = []
        for cluster in clusters:
            # Get representative feedback
            representative_feedback = None
            if cluster.member_count > 0:
                feedback_doc = db.query(ProcessedDocument).filter(
                    ProcessedDocument.cluster_id == cluster.id
                ).first()
                
                if feedback_doc:
                    representative_feedback = {
                        "id": str(feedback_doc.id),
                        "title": feedback_doc.title or "Untitled",
                        "content": feedback_doc.content or "",
                        "feedback_type": feedback_doc.feedback_type.value if feedback_doc.feedback_type else "other",
                        "priority": "medium",
                        "source": feedback_doc.source_type.value if feedback_doc.source_type else "unknown",
                        "source_url": feedback_doc.source_url,
                        "author": feedback_doc.author,
                        "created_at": feedback_doc.created_at,
                        "processed_at": feedback_doc.processed_at,
                        "cluster_id": str(feedback_doc.cluster_id) if feedback_doc.cluster_id else None,
                        "ticket_id": None,
                        "metadata": {}
                    }
            
            cluster_items.append(ClusterItem(
                id=str(cluster.id),
                name=cluster.name,
                description=cluster.description,
                member_count=cluster.member_count or 0,
                created_at=cluster.created_at,
                updated_at=cluster.updated_at,
                top_keywords=cluster.top_keywords or [],
                representative_feedback=representative_feedback,
                metadata=cluster.metadata or {}
            ))
        
        return ClusterListResponse(
            clusters=cluster_items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=offset + page_size < total,
            has_previous=page > 1
        )
    
    except Exception as e:
        logger.error(f"Failed to get clusters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clusters/{cluster_id}", response_model=ClusterItem)
@require_permission("read")
async def get_cluster(
    cluster_id: str = Path(..., description="Cluster ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get a specific cluster."""
    try:
        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        # Get representative feedback
        representative_feedback = None
        if cluster.member_count > 0:
            feedback_doc = db.query(ProcessedDocument).filter(
                ProcessedDocument.cluster_id == cluster.id
            ).first()
            
            if feedback_doc:
                representative_feedback = {
                    "id": str(feedback_doc.id),
                    "title": feedback_doc.title or "Untitled",
                    "content": feedback_doc.content or "",
                    "feedback_type": feedback_doc.feedback_type.value if feedback_doc.feedback_type else "other",
                    "priority": "medium",
                    "source": feedback_doc.source_type.value if feedback_doc.source_type else "unknown",
                    "source_url": feedback_doc.source_url,
                    "author": feedback_doc.author,
                    "created_at": feedback_doc.created_at,
                    "processed_at": feedback_doc.processed_at,
                    "cluster_id": str(feedback_doc.cluster_id) if feedback_doc.cluster_id else None,
                    "ticket_id": None,
                    "metadata": {}
                }
        
        return ClusterItem(
            id=str(cluster.id),
            name=cluster.name,
            description=cluster.description,
            member_count=cluster.member_count or 0,
            created_at=cluster.created_at,
            updated_at=cluster.updated_at,
            top_keywords=cluster.top_keywords or [],
            representative_feedback=representative_feedback,
            metadata=cluster.metadata or {}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cluster: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Ticket endpoints
@router.get("/tickets", response_model=TicketListResponse)
@require_permission("read")
async def get_tickets(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Ticket status filter"),
    platform: Optional[str] = Query(None, description="Platform filter"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get tickets with pagination and filtering."""
    try:
        # Build query
        query = db.query(Ticket)
        
        if status:
            query = query.filter(Ticket.status == status)
        
        if platform:
            query = query.filter(Ticket.platform == platform)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        tickets = query.offset(offset).limit(page_size).all()
        
        # Convert to response format
        ticket_items = []
        for ticket in tickets:
            ticket_items.append(TicketItem(
                id=str(ticket.id),
                external_id=ticket.external_id,
                external_url=ticket.external_url,
                platform=ticket.platform,
                title=ticket.title,
                description=ticket.description,
                status=ticket.status.value if ticket.status else "open",
                priority=ticket.priority or 0,
                source_feedback_id=str(ticket.source_document_id),
                cluster_id=str(ticket.cluster_id) if ticket.cluster_id else None,
                created_at=ticket.created_at,
                updated_at=ticket.updated_at,
                metadata=ticket.metadata or {}
            ))
        
        return TicketListResponse(
            tickets=ticket_items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=offset + page_size < total,
            has_previous=page > 1
        )
    
    except Exception as e:
        logger.error(f"Failed to get tickets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tickets/{ticket_id}", response_model=TicketItem)
@require_permission("read")
async def get_ticket(
    ticket_id: str = Path(..., description="Ticket ID"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get a specific ticket."""
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
        
        return TicketItem(
            id=str(ticket.id),
            external_id=ticket.external_id,
            external_url=ticket.external_url,
            platform=ticket.platform,
            title=ticket.title,
            description=ticket.description,
            status=ticket.status.value if ticket.status else "open",
            priority=ticket.priority or 0,
            source_feedback_id=str(ticket.source_document_id),
            cluster_id=str(ticket.cluster_id) if ticket.cluster_id else None,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            metadata=ticket.metadata or {}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Report endpoints
@router.get("/reports", response_model=ReportListResponse)
@require_permission("read")
async def get_reports(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    report_type: Optional[str] = Query(None, description="Report type filter"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get reports with pagination and filtering."""
    try:
        # Build query
        query = db.query(DigestReport)
        
        if report_type:
            query = query.filter(DigestReport.report_type == report_type)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        reports = query.offset(offset).limit(page_size).all()
        
        # Convert to response format
        report_items = []
        for report in reports:
            report_items.append(ReportItem(
                id=str(report.id),
                report_type=report.report_type,
                title=report.title,
                content=report.content,
                format=report.format or "html",
                generated_at=report.generated_at,
                start_date=report.period_start,
                end_date=report.period_end,
                metadata=report.metadata or {}
            ))
        
        return ReportListResponse(
            reports=report_items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=offset + page_size < total,
            has_previous=page > 1
        )
    
    except Exception as e:
        logger.error(f"Failed to get reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reports/generate", response_model=ReportItem)
@require_permission("write")
async def generate_report(
    request: ReportGenerationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Generate a new report."""
    try:
        # This would integrate with the DigestorAgent
        # For now, return a mock response
        report = ReportItem(
            id="mock-report-id",
            report_type=request.report_type,
            title=f"{request.report_type.title()} Report",
            content="<html><body><h1>Report Content</h1></body></html>",
            format=request.format,
            generated_at=datetime.utcnow(),
            start_date=request.start_date,
            end_date=request.end_date,
            metadata=request.filters
        )
        
        return report
    
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Scheduling endpoints
@router.get("/jobs", response_model=List[ScheduledJobItem])
@require_permission("read")
async def get_scheduled_jobs(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all scheduled jobs."""
    try:
        # This would integrate with the PipelineScheduler
        # For now, return empty list
        return []
    
    except Exception as e:
        logger.error(f"Failed to get scheduled jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs", response_model=ScheduledJobItem)
@require_permission("write")
async def create_scheduled_job(
    request: ScheduledJobRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new scheduled job."""
    try:
        # This would integrate with the PipelineScheduler
        # For now, return a mock response
        job = ScheduledJobItem(
            id="mock-job-id",
            name=request.name,
            description=request.description,
            workflow_name=request.workflow_name,
            schedule_type=request.schedule_type,
            schedule_value=request.schedule_value,
            timezone=request.timezone,
            enabled=request.enabled,
            max_concurrent=request.max_concurrent,
            timeout=request.timeout,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            next_run=None,
            last_run=None,
            config=request.config
        )
        
        return job
    
    except Exception as e:
        logger.error(f"Failed to create scheduled job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/jobs/{job_id}", response_model=ScheduledJobItem)
@require_permission("write")
async def update_scheduled_job(
    job_id: str = Path(..., description="Job ID"),
    request: ScheduledJobRequest = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update a scheduled job."""
    try:
        # This would integrate with the PipelineScheduler
        # For now, return a mock response
        job = ScheduledJobItem(
            id=job_id,
            name=request.name if request else "Updated Job",
            description=request.description if request else "Updated description",
            workflow_name=request.workflow_name if request else "feedback_processing",
            schedule_type=request.schedule_type if request else "cron",
            schedule_value=request.schedule_value if request else "0 9 * * *",
            timezone=request.timezone if request else "UTC",
            enabled=request.enabled if request else True,
            max_concurrent=request.max_concurrent if request else 1,
            timeout=request.timeout,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            next_run=None,
            last_run=None,
            config=request.config if request else {}
        )
        
        return job
    
    except Exception as e:
        logger.error(f"Failed to update scheduled job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/jobs/{job_id}")
@require_permission("write")
async def delete_scheduled_job(
    job_id: str = Path(..., description="Job ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a scheduled job."""
    try:
        # This would integrate with the PipelineScheduler
        return APIResponse(
            status="success",
            message=f"Job {job_id} deleted successfully"
        )
    
    except Exception as e:
        logger.error(f"Failed to delete scheduled job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/jobs/{job_id}/run", response_model=JobExecutionResponse)
@require_permission("write")
async def run_job_manually(
    job_id: str = Path(..., description="Job ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Run a job manually."""
    try:
        # This would integrate with the PipelineScheduler
        # For now, return a mock response
        execution = JobExecutionResponse(
            execution_id="mock-execution-id",
            job_id=job_id,
            workflow_name="feedback_processing",
            status="running",
            started_at=datetime.utcnow(),
            completed_at=None,
            duration=None,
            error_message=None,
            metadata={}
        )
        
        return execution
    
    except Exception as e:
        logger.error(f"Failed to run job manually: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Search endpoint
@router.post("/search", response_model=SearchResponse)
@require_permission("read")
async def search(
    request: SearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Search across all data."""
    try:
        start_time = datetime.utcnow()
        
        # Build search query
        query = db.query(ProcessedDocument)
        
        if request.query:
            query = query.filter(
                ProcessedDocument.content.ilike(f"%{request.query}%")
            )
        
        # Apply filters
        if "feedback_type" in request.filters:
            query = query.filter(
                ProcessedDocument.feedback_type == request.filters["feedback_type"]
            )
        
        if "source" in request.filters:
            query = query.filter(
                ProcessedDocument.source_type == request.filters["source"]
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (request.page - 1) * request.page_size
        results = query.offset(offset).limit(request.page_size).all()
        
        # Convert to response format
        search_results = []
        for doc in results:
            search_results.append({
                "id": str(doc.id),
                "type": "feedback",
                "title": doc.title or "Untitled",
                "content": doc.content or "",
                "feedback_type": doc.feedback_type.value if doc.feedback_type else "other",
                "source": doc.source_type.value if doc.source_type else "unknown",
                "created_at": doc.created_at.isoformat(),
                "relevance_score": 0.8  # Would be calculated by search engine
            })
        
        search_time = (datetime.utcnow() - start_time).total_seconds()
        
        return SearchResponse(
            results=search_results,
            total=total,
            page=request.page,
            page_size=request.page_size,
            has_next=offset + request.page_size < total,
            has_previous=request.page > 1,
            query=request.query,
            filters=request.filters,
            search_time=search_time
        )
    
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Configuration endpoints
@router.get("/config", response_model=SystemConfigResponse)
@require_permission("read")
async def get_system_config(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get system configuration."""
    try:
        # This would get actual system configuration
        config = {
            "workflow_engine": {
                "max_concurrent_agents": 3,
                "default_timeout": 300,
                "retry_delay": 30
            },
            "scheduler": {
                "enabled": True,
                "max_concurrent_jobs": 5
            },
            "agents": {
                "ingestor": {"enabled": True, "timeout": 600},
                "normalizer": {"enabled": True, "timeout": 300},
                "classifier": {"enabled": True, "timeout": 300},
                "clusterer": {"enabled": True, "timeout": 300},
                "prioritizer": {"enabled": True, "timeout": 300},
                "actioner": {"enabled": True, "timeout": 600},
                "digestor": {"enabled": True, "timeout": 300},
                "feedback_loop": {"enabled": True, "timeout": 600}
            }
        }
        
        return SystemConfigResponse(
            config=config,
            last_updated=datetime.utcnow(),
            version="1.0.0"
        )
    
    except Exception as e:
        logger.error(f"Failed to get system config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/config", response_model=APIResponse)
@require_permission("admin")
async def update_system_config(
    request: ConfigUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update system configuration."""
    try:
        # This would update actual system configuration
        # For now, just return success
        return APIResponse(
            status="success",
            message="Configuration updated successfully",
            data={"updated_fields": list(request.config.keys())}
        )
    
    except Exception as e:
        logger.error(f"Failed to update system config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

