"""
Pipeline Scheduler for Product Feedback Miner.

This module provides automated scheduling and execution
of feedback processing workflows.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json
from croniter import croniter
import pytz

from orchestration.workflow import WorkflowEngine, WorkflowExecution, WorkflowStatus
from database.models import ScheduledJob
from database import get_session

logger = logging.getLogger(__name__)

class ScheduleType(str, Enum):
    """Types of schedules."""
    CRON = "cron"
    INTERVAL = "interval"
    ONCE = "once"
    MANUAL = "manual"

class JobStatus(str, Enum):
    """Status of scheduled jobs."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DISABLED = "disabled"

@dataclass
class ScheduleConfig:
    """Configuration for a scheduled job."""
    job_id: str
    name: str
    description: str
    workflow_name: str
    schedule_type: ScheduleType
    schedule_value: str  # cron expression or interval
    timezone: str = "UTC"
    enabled: bool = True
    max_concurrent: int = 1
    timeout: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    retry_delay: int = 300  # 5 minutes
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class JobExecution:
    """Represents a job execution instance."""
    execution_id: str
    job_id: str
    workflow_name: str
    status: JobStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    next_run: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class PipelineScheduler:
    """
    Scheduler for automated pipeline execution.
    
    This scheduler:
    1. Manages scheduled jobs and their execution
    2. Handles cron expressions and interval scheduling
    3. Provides job monitoring and management
    4. Handles job failures and retries
    5. Manages concurrent execution limits
    6. Persists job state and history
    """
    
    def __init__(self, workflow_engine: WorkflowEngine, config: Optional[Dict[str, Any]] = None):
        """Initialize pipeline scheduler."""
        self.workflow_engine = workflow_engine
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Job management
        self.scheduled_jobs: Dict[str, ScheduleConfig] = {}
        self.active_executions: Dict[str, JobExecution] = {}
        self.execution_history: List[JobExecution] = []
        
        # Scheduler state
        self.is_running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        
        # Don't load jobs immediately - will be done in start()
    
    async def start(self):
        """Start the scheduler."""
        try:
            if self.is_running:
                self.logger.warning("Scheduler is already running")
                return
            
            # Load existing jobs from database
            await self._load_jobs_from_database()
            
            self.is_running = True
            self.scheduler_task = asyncio.create_task(self._scheduler_loop())
            
            self.logger.info("Pipeline scheduler started")
        
        except Exception as e:
            self.logger.error(f"Error starting scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the scheduler."""
        try:
            if not self.is_running:
                self.logger.warning("Scheduler is not running")
                return
            
            self.is_running = False
            
            if self.scheduler_task:
                self.scheduler_task.cancel()
                try:
                    await self.scheduler_task
                except asyncio.CancelledError:
                    pass
            
            # Cancel all active executions
            for execution in list(self.active_executions.values()):
                await self.cancel_job_execution(execution.execution_id)
            
            self.logger.info("Pipeline scheduler stopped")
        
        except Exception as e:
            self.logger.error(f"Error stopping scheduler: {e}")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        try:
            while self.is_running:
                try:
                    # Check for jobs that need to run
                    await self._check_scheduled_jobs()
                    
                    # Clean up completed executions
                    await self._cleanup_completed_executions()
                    
                    # Wait before next check
                    await asyncio.sleep(60)  # Check every minute
                
                except Exception as e:
                    self.logger.error(f"Error in scheduler loop: {e}")
                    await asyncio.sleep(60)
        
        except asyncio.CancelledError:
            self.logger.info("Scheduler loop cancelled")
        except Exception as e:
            self.logger.error(f"Fatal error in scheduler loop: {e}")
    
    async def _check_scheduled_jobs(self):
        """Check for jobs that need to run."""
        try:
            now = datetime.utcnow()
            
            for job_id, job_config in self.scheduled_jobs.items():
                if not job_config.enabled:
                    continue
                
                # Check if job should run
                should_run = await self._should_job_run(job_config, now)
                
                if should_run:
                    # Check concurrent execution limit
                    active_count = sum(
                        1 for exec in self.active_executions.values()
                        if exec.job_id == job_id
                    )
                    
                    if active_count < job_config.max_concurrent:
                        # Start job execution
                        await self._start_job_execution(job_config)
                    else:
                        self.logger.warning(
                            f"Job {job_id} skipped - max concurrent executions reached"
                        )
        
        except Exception as e:
            self.logger.error(f"Error checking scheduled jobs: {e}")
    
    async def _should_job_run(self, job_config: ScheduleConfig, now: datetime) -> bool:
        """Check if a job should run at the given time."""
        try:
            if job_config.schedule_type == ScheduleType.CRON:
                # Parse cron expression
                cron = croniter(job_config.schedule_value, now)
                next_run = cron.get_next(datetime)
                
                # Check if it's time to run (within 1 minute tolerance)
                return abs((next_run - now).total_seconds()) < 60
            
            elif job_config.schedule_type == ScheduleType.INTERVAL:
                # Parse interval (e.g., "5m", "1h", "1d")
                interval_seconds = self._parse_interval(job_config.schedule_value)
                if interval_seconds is None:
                    return False
                
                # Check if enough time has passed since last run
                last_run = await self._get_last_job_run(job_config.job_id)
                if last_run is None:
                    return True
                
                time_since_last_run = (now - last_run).total_seconds()
                return time_since_last_run >= interval_seconds
            
            elif job_config.schedule_type == ScheduleType.ONCE:
                # Run once at a specific time
                try:
                    run_time = datetime.fromisoformat(job_config.schedule_value)
                    return abs((run_time - now).total_seconds()) < 60
                except ValueError:
                    return False
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error checking if job should run: {e}")
            return False
    
    def _parse_interval(self, interval_str: str) -> Optional[int]:
        """Parse interval string to seconds."""
        try:
            interval_str = interval_str.lower().strip()
            
            if interval_str.endswith('s'):
                return int(interval_str[:-1])
            elif interval_str.endswith('m'):
                return int(interval_str[:-1]) * 60
            elif interval_str.endswith('h'):
                return int(interval_str[:-1]) * 3600
            elif interval_str.endswith('d'):
                return int(interval_str[:-1]) * 86400
            else:
                # Assume seconds if no unit
                return int(interval_str)
        
        except (ValueError, AttributeError):
            return None
    
    async def _get_last_job_run(self, job_id: str) -> Optional[datetime]:
        """Get the last run time for a job."""
        try:
            # Check active executions
            for execution in self.active_executions.values():
                if execution.job_id == job_id and execution.started_at:
                    return execution.started_at
            
            # Check history
            for execution in reversed(self.execution_history):
                if execution.job_id == job_id and execution.started_at:
                    return execution.started_at
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error getting last job run: {e}")
            return None
    
    async def _start_job_execution(self, job_config: ScheduleConfig):
        """Start a job execution."""
        try:
            execution_id = str(uuid.uuid4())
            
            # Create job execution
            execution = JobExecution(
                execution_id=execution_id,
                job_id=job_config.job_id,
                workflow_name=job_config.workflow_name,
                status=JobStatus.PENDING,
                started_at=datetime.utcnow(),
                metadata=job_config.config.copy()
            )
            
            # Store execution
            self.active_executions[execution_id] = execution
            
            # Start workflow execution
            asyncio.create_task(self._execute_job(execution, job_config))
            
            self.logger.info(f"Started job execution: {job_config.name} (ID: {execution_id})")
        
        except Exception as e:
            self.logger.error(f"Error starting job execution: {e}")
    
    async def _execute_job(self, execution: JobExecution, job_config: ScheduleConfig):
        """Execute a job."""
        try:
            execution.status = JobStatus.RUNNING
            
            # Execute workflow
            workflow_result = await self.workflow_engine.execute_workflow(
                workflow_name=execution.workflow_name,
                config=execution.metadata,
                execution_id=execution.execution_id
            )
            
            # Update execution status
            if workflow_result.status == WorkflowStatus.COMPLETED:
                execution.status = JobStatus.COMPLETED
            else:
                execution.status = JobStatus.FAILED
                execution.error_message = workflow_result.error_message
            
            execution.completed_at = datetime.utcnow()
            
            # Calculate next run time
            if job_config.schedule_type in [ScheduleType.CRON, ScheduleType.INTERVAL]:
                execution.next_run = await self._calculate_next_run(job_config)
            
            self.logger.info(
                f"Job execution completed: {job_config.name} "
                f"(Status: {execution.status.value})"
            )
        
        except Exception as e:
            execution.status = JobStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            
            self.logger.error(f"Job execution failed: {job_config.name} - {e}")
        
        finally:
            # Move to history
            self.execution_history.append(execution)
            if execution.execution_id in self.active_executions:
                del self.active_executions[execution.execution_id]
            
            # Save to database
            await self._save_job_execution(execution)
    
    async def _calculate_next_run(self, job_config: ScheduleConfig) -> Optional[datetime]:
        """Calculate next run time for a job."""
        try:
            now = datetime.utcnow()
            
            if job_config.schedule_type == ScheduleType.CRON:
                cron = croniter(job_config.schedule_value, now)
                return cron.get_next(datetime)
            
            elif job_config.schedule_type == ScheduleType.INTERVAL:
                interval_seconds = self._parse_interval(job_config.schedule_value)
                if interval_seconds:
                    return now + timedelta(seconds=interval_seconds)
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error calculating next run time: {e}")
            return None
    
    async def _cleanup_completed_executions(self):
        """Clean up old completed executions."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=7)  # Keep 7 days
            
            # Remove old executions from history
            self.execution_history = [
                exec for exec in self.execution_history
                if exec.completed_at is None or exec.completed_at > cutoff_time
            ]
        
        except Exception as e:
            self.logger.error(f"Error cleaning up executions: {e}")
    
    async def create_scheduled_job(
        self,
        name: str,
        description: str,
        workflow_name: str,
        schedule_type: ScheduleType,
        schedule_value: str,
        timezone: str = "UTC",
        enabled: bool = True,
        max_concurrent: int = 1,
        timeout: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new scheduled job."""
        try:
            job_id = str(uuid.uuid4())
            
            job_config = ScheduleConfig(
                job_id=job_id,
                name=name,
                description=description,
                workflow_name=workflow_name,
                schedule_type=schedule_type,
                schedule_value=schedule_value,
                timezone=timezone,
                enabled=enabled,
                max_concurrent=max_concurrent,
                timeout=timeout,
                config=config or {}
            )
            
            # Store job
            self.scheduled_jobs[job_id] = job_config
            
            # Save to database
            await self._save_scheduled_job(job_config)
            
            self.logger.info(f"Created scheduled job: {name} (ID: {job_id})")
            return job_id
        
        except Exception as e:
            self.logger.error(f"Error creating scheduled job: {e}")
            raise
    
    async def update_scheduled_job(
        self,
        job_id: str,
        **updates
    ) -> bool:
        """Update a scheduled job."""
        try:
            if job_id not in self.scheduled_jobs:
                return False
            
            job_config = self.scheduled_jobs[job_id]
            
            # Update fields
            for key, value in updates.items():
                if hasattr(job_config, key):
                    setattr(job_config, key, value)
            
            job_config.updated_at = datetime.utcnow()
            
            # Save to database
            await self._save_scheduled_job(job_config)
            
            self.logger.info(f"Updated scheduled job: {job_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error updating scheduled job: {e}")
            return False
    
    async def delete_scheduled_job(self, job_id: str) -> bool:
        """Delete a scheduled job."""
        try:
            if job_id not in self.scheduled_jobs:
                return False
            
            # Disable job first
            self.scheduled_jobs[job_id].enabled = False
            
            # Remove from database
            await self._delete_scheduled_job(job_id)
            
            # Remove from memory
            del self.scheduled_jobs[job_id]
            
            self.logger.info(f"Deleted scheduled job: {job_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error deleting scheduled job: {e}")
            return False
    
    async def run_job_manually(self, job_id: str) -> str:
        """Run a job manually."""
        try:
            if job_id not in self.scheduled_jobs:
                raise ValueError(f"Job not found: {job_id}")
            
            job_config = self.scheduled_jobs[job_id]
            
            # Create manual execution
            execution_id = str(uuid.uuid4())
            execution = JobExecution(
                execution_id=execution_id,
                job_id=job_id,
                workflow_name=job_config.workflow_name,
                status=JobStatus.PENDING,
                started_at=datetime.utcnow(),
                metadata=job_config.config.copy()
            )
            
            # Store execution
            self.active_executions[execution_id] = execution
            
            # Start execution
            asyncio.create_task(self._execute_job(execution, job_config))
            
            self.logger.info(f"Started manual job execution: {job_config.name} (ID: {execution_id})")
            return execution_id
        
        except Exception as e:
            self.logger.error(f"Error running job manually: {e}")
            raise
    
    async def cancel_job_execution(self, execution_id: str) -> bool:
        """Cancel a job execution."""
        try:
            if execution_id not in self.active_executions:
                return False
            
            execution = self.active_executions[execution_id]
            execution.status = JobStatus.CANCELLED
            execution.completed_at = datetime.utcnow()
            
            # Cancel workflow execution
            await self.workflow_engine.cancel_workflow(execution_id)
            
            # Move to history
            self.execution_history.append(execution)
            del self.active_executions[execution_id]
            
            self.logger.info(f"Cancelled job execution: {execution_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error cancelling job execution: {e}")
            return False
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a scheduled job."""
        try:
            if job_id not in self.scheduled_jobs:
                return None
            
            job_config = self.scheduled_jobs[job_id]
            
            # Get active executions
            active_executions = [
                exec for exec in self.active_executions.values()
                if exec.job_id == job_id
            ]
            
            # Get recent execution history
            recent_executions = [
                exec for exec in self.execution_history
                if exec.job_id == job_id
            ][-10:]  # Last 10 executions
            
            return {
                "job_id": job_id,
                "name": job_config.name,
                "description": job_config.description,
                "workflow_name": job_config.workflow_name,
                "schedule_type": job_config.schedule_type.value,
                "schedule_value": job_config.schedule_value,
                "enabled": job_config.enabled,
                "active_executions": len(active_executions),
                "recent_executions": [
                    {
                        "execution_id": exec.execution_id,
                        "status": exec.status.value,
                        "started_at": exec.started_at.isoformat() if exec.started_at else None,
                        "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
                        "error_message": exec.error_message
                    }
                    for exec in recent_executions
                ]
            }
        
        except Exception as e:
            self.logger.error(f"Error getting job status: {e}")
            return None
    
    async def get_scheduler_metrics(self) -> Dict[str, Any]:
        """Get scheduler metrics."""
        try:
            total_jobs = len(self.scheduled_jobs)
            enabled_jobs = sum(1 for job in self.scheduled_jobs.values() if job.enabled)
            active_executions = len(self.active_executions)
            
            # Calculate success rate
            total_executions = len(self.execution_history)
            successful_executions = sum(
                1 for exec in self.execution_history
                if exec.status == JobStatus.COMPLETED
            )
            success_rate = successful_executions / total_executions if total_executions > 0 else 0.0
            
            return {
                "total_jobs": total_jobs,
                "enabled_jobs": enabled_jobs,
                "active_executions": active_executions,
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "success_rate": success_rate,
                "scheduler_running": self.is_running
            }
        
        except Exception as e:
            self.logger.error(f"Error getting scheduler metrics: {e}")
            return {}
    
    async def _load_jobs_from_database(self):
        """Load scheduled jobs from database."""
        try:
            with get_session() as session:
                jobs = session.query(ScheduledJob).filter(
                    ScheduledJob.status != JobStatus.DISABLED
                ).all()
                
                for job in jobs:
                    job_config = ScheduleConfig(
                        job_id=str(job.id),
                        name=job.name,
                        description=job.description,
                        workflow_name=job.workflow_name,
                        schedule_type=ScheduleType(job.schedule_type),
                        schedule_value=job.schedule_value,
                        timezone=job.timezone,
                        enabled=job.enabled,
                        max_concurrent=job.max_concurrent,
                        timeout=job.timeout,
                        config=json.loads(job.config) if job.config else {}
                    )
                    
                    self.scheduled_jobs[str(job.id)] = job_config
                
                self.logger.info(f"Loaded {len(jobs)} scheduled jobs from database")
        
        except Exception as e:
            self.logger.error(f"Error loading jobs from database: {e}")
    
    async def _save_scheduled_job(self, job_config: ScheduleConfig):
        """Save scheduled job to database."""
        try:
            with get_session() as session:
                # Check if job exists
                existing_job = session.query(ScheduledJob).filter(
                    ScheduledJob.id == job_config.job_id
                ).first()
                
                if existing_job:
                    # Update existing job
                    existing_job.name = job_config.name
                    existing_job.description = job_config.description
                    existing_job.workflow_name = job_config.workflow_name
                    existing_job.schedule_type = job_config.schedule_type.value
                    existing_job.schedule_value = job_config.schedule_value
                    existing_job.timezone = job_config.timezone
                    existing_job.enabled = job_config.enabled
                    existing_job.max_concurrent = job_config.max_concurrent
                    existing_job.timeout = job_config.timeout
                    existing_job.config = json.dumps(job_config.config)
                    existing_job.updated_at = job_config.updated_at
                else:
                    # Create new job
                    new_job = ScheduledJob(
                        id=job_config.job_id,
                        name=job_config.name,
                        description=job_config.description,
                        workflow_name=job_config.workflow_name,
                        schedule_type=job_config.schedule_type.value,
                        schedule_value=job_config.schedule_value,
                        timezone=job_config.timezone,
                        enabled=job_config.enabled,
                        max_concurrent=job_config.max_concurrent,
                        timeout=job_config.timeout,
                        config=json.dumps(job_config.config),
                        created_at=job_config.created_at,
                        updated_at=job_config.updated_at
                    )
                    session.add(new_job)
                
                session.commit()
        
        except Exception as e:
            self.logger.error(f"Error saving scheduled job: {e}")
    
    async def _delete_scheduled_job(self, job_id: str):
        """Delete scheduled job from database."""
        try:
            with get_session() as session:
                job = session.query(ScheduledJob).filter(
                    ScheduledJob.id == job_id
                ).first()
                
                if job:
                    job.status = JobStatus.DISABLED
                    session.commit()
        
        except Exception as e:
            self.logger.error(f"Error deleting scheduled job: {e}")
    
    async def _save_job_execution(self, execution: JobExecution):
        """Save job execution to database."""
        try:
            with get_session() as session:
                # This would typically save to a job execution table
                # For now, just log the execution
                self.logger.debug(f"Job execution saved: {execution.execution_id}")
        
        except Exception as e:
            self.logger.error(f"Error saving job execution: {e}")
