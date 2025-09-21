"""
Workflow Engine for Product Feedback Miner.

This module provides pipeline orchestration, agent coordination,
and workflow management for the entire feedback processing system.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from agents.base.agent import BaseAgent, AgentResult, AgentContext
from agents.ingestor.agent import IngestorAgent
from agents.normalizer.agent import NormalizerAgent
from agents.classifier.agent import ClassifierAgent
from agents.clusterer.agent import ClustererAgent
from agents.prioritizer.agent import PrioritizerAgent
from agents.actioner.agent import ActionerAgent
from agents.digestor.agent import DigestorAgent
from agents.feedback_loop.agent import FeedbackLoopAgent
from database.models import AgentExecution, ProcessingStatus
from database import get_session

logger = logging.getLogger(__name__)

class WorkflowStatus(str, Enum):
    """Status of workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class AgentStatus(str, Enum):
    """Status of individual agent execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"

@dataclass
class WorkflowStep:
    """Represents a single step in the workflow."""
    agent_name: str
    agent_class: type
    dependencies: List[str] = field(default_factory=list)
    timeout: Optional[int] = None  # seconds
    retry_count: int = 0
    max_retries: int = 3
    enabled: bool = True
    parallel: bool = False
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None

@dataclass
class WorkflowExecution:
    """Represents a workflow execution instance."""
    execution_id: str
    workflow_name: str
    status: WorkflowStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration: Optional[float] = None
    steps_completed: int = 0
    steps_failed: int = 0
    steps_total: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, AgentResult] = field(default_factory=dict)

@dataclass
class WorkflowConfig:
    """Configuration for workflow execution."""
    max_concurrent_agents: int = 3
    default_timeout: int = 300  # 5 minutes
    retry_delay: int = 30  # seconds
    enable_parallel_execution: bool = True
    enable_error_recovery: bool = True
    enable_monitoring: bool = True
    log_level: str = "INFO"
    save_execution_history: bool = True

class WorkflowEngine:
    """
    Main workflow engine for orchestrating the feedback processing pipeline.
    
    This engine:
    1. Manages agent execution order and dependencies
    2. Handles parallel and sequential execution
    3. Provides error handling and recovery
    4. Monitors pipeline health and performance
    5. Manages workflow state and persistence
    6. Coordinates data flow between agents
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize workflow engine."""
        self.config = WorkflowConfig(**(config or {}))
        self.logger = logging.getLogger(__name__)
        
        # Agent registry
        self.agents = {}
        self.agent_instances = {}
        
        # Workflow definitions
        self.workflows = {}
        
        # Execution tracking
        self.active_executions = {}
        self.execution_history = []
        
        # Thread pool for parallel execution
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_agents)
        
        # Initialize agents
        self._initialize_agents()
        
        # Define workflows
        self._define_workflows()
    
    def _initialize_agents(self):
        """Initialize all available agents."""
        try:
            # Register all agents
            self.agents = {
                "ingestor": IngestorAgent,
                "normalizer": NormalizerAgent,
                "classifier": ClassifierAgent,
                "clusterer": ClustererAgent,
                "prioritizer": PrioritizerAgent,
                "actioner": ActionerAgent,
                "digestor": DigestorAgent,
                "feedback_loop": FeedbackLoopAgent
            }
            
            self.logger.info(f"Initialized {len(self.agents)} agents")
        
        except Exception as e:
            self.logger.error(f"Error initializing agents: {e}")
            raise
    
    def _define_workflows(self):
        """Define available workflows."""
        try:
            # Main feedback processing workflow
            self.workflows["feedback_processing"] = [
                WorkflowStep(
                    agent_name="ingestor",
                    agent_class=IngestorAgent,
                    dependencies=[],
                    timeout=600,  # 10 minutes
                    max_retries=2
                ),
                WorkflowStep(
                    agent_name="normalizer",
                    agent_class=NormalizerAgent,
                    dependencies=["ingestor"],
                    timeout=300,  # 5 minutes
                    max_retries=3
                ),
                WorkflowStep(
                    agent_name="classifier",
                    agent_class=ClassifierAgent,
                    dependencies=["normalizer"],
                    timeout=300,  # 5 minutes
                    max_retries=2
                ),
                WorkflowStep(
                    agent_name="clusterer",
                    agent_class=ClustererAgent,
                    dependencies=["classifier"],
                    timeout=300,  # 5 minutes
                    max_retries=2
                ),
                WorkflowStep(
                    agent_name="prioritizer",
                    agent_class=PrioritizerAgent,
                    dependencies=["clusterer"],
                    timeout=300,  # 5 minutes
                    max_retries=2
                ),
                WorkflowStep(
                    agent_name="actioner",
                    agent_class=ActionerAgent,
                    dependencies=["prioritizer"],
                    timeout=600,  # 10 minutes
                    max_retries=2
                ),
                WorkflowStep(
                    agent_name="digestor",
                    agent_class=DigestorAgent,
                    dependencies=["actioner"],
                    timeout=300,  # 5 minutes
                    max_retries=2
                )
            ]
            
            # Learning and improvement workflow
            self.workflows["learning_improvement"] = [
                WorkflowStep(
                    agent_name="feedback_loop",
                    agent_class=FeedbackLoopAgent,
                    dependencies=["digestor"],
                    timeout=600,  # 10 minutes
                    max_retries=2
                )
            ]
            
            # Full pipeline workflow (includes learning)
            self.workflows["full_pipeline"] = (
                self.workflows["feedback_processing"] + 
                self.workflows["learning_improvement"]
            )
            
            # Quick processing workflow (no learning)
            self.workflows["quick_processing"] = [
                WorkflowStep(
                    agent_name="ingestor",
                    agent_class=IngestorAgent,
                    dependencies=[],
                    timeout=300,  # 5 minutes
                    max_retries=1
                ),
                WorkflowStep(
                    agent_name="normalizer",
                    agent_class=NormalizerAgent,
                    dependencies=["ingestor"],
                    timeout=180,  # 3 minutes
                    max_retries=2
                ),
                WorkflowStep(
                    agent_name="classifier",
                    agent_class=ClassifierAgent,
                    dependencies=["normalizer"],
                    timeout=180,  # 3 minutes
                    max_retries=1
                ),
                WorkflowStep(
                    agent_name="prioritizer",
                    agent_class=PrioritizerAgent,
                    dependencies=["classifier"],
                    timeout=180,  # 3 minutes
                    max_retries=1
                ),
                WorkflowStep(
                    agent_name="actioner",
                    agent_class=ActionerAgent,
                    dependencies=["prioritizer"],
                    timeout=300,  # 5 minutes
                    max_retries=1
                )
            ]
            
            self.logger.info(f"Defined {len(self.workflows)} workflows")
        
        except Exception as e:
            self.logger.error(f"Error defining workflows: {e}")
            raise
    
    async def execute_workflow(
        self, 
        workflow_name: str, 
        config: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None
    ) -> WorkflowExecution:
        """
        Execute a workflow.
        
        Args:
            workflow_name: Name of the workflow to execute
            config: Configuration overrides
            execution_id: Optional execution ID
            
        Returns:
            WorkflowExecution result
        """
        try:
            if workflow_name not in self.workflows:
                raise ValueError(f"Unknown workflow: {workflow_name}")
            
            # Create execution instance
            execution_id = execution_id or str(uuid.uuid4())
            execution = WorkflowExecution(
                execution_id=execution_id,
                workflow_name=workflow_name,
                status=WorkflowStatus.PENDING,
                started_at=datetime.utcnow(),
                steps_total=len(self.workflows[workflow_name])
            )
            
            # Store execution
            self.active_executions[execution_id] = execution
            
            self.logger.info(f"Starting workflow execution: {workflow_name} (ID: {execution_id})")
            
            try:
                # Execute workflow steps
                await self._execute_workflow_steps(execution, config)
                
                # Mark as completed
                execution.status = WorkflowStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
                execution.total_duration = (
                    execution.completed_at - execution.started_at
                ).total_seconds()
                
                self.logger.info(
                    f"Workflow completed: {workflow_name} "
                    f"(Duration: {execution.total_duration:.2f}s, "
                    f"Steps: {execution.steps_completed}/{execution.steps_total})"
                )
            
            except Exception as e:
                # Mark as failed
                execution.status = WorkflowStatus.FAILED
                execution.completed_at = datetime.utcnow()
                execution.total_duration = (
                    execution.completed_at - execution.started_at
                ).total_seconds()
                execution.error_message = str(e)
                
                self.logger.error(
                    f"Workflow failed: {workflow_name} - {e}",
                    exc_info=True
                )
            
            finally:
                # Move to history
                self.execution_history.append(execution)
                if execution_id in self.active_executions:
                    del self.active_executions[execution_id]
                
                # Save execution history if enabled
                if self.config.save_execution_history:
                    await self._save_execution_history(execution)
            
            return execution
        
        except Exception as e:
            self.logger.error(f"Error executing workflow {workflow_name}: {e}")
            raise
    
    async def _execute_workflow_steps(
        self, 
        execution: WorkflowExecution, 
        config: Optional[Dict[str, Any]]
    ):
        """Execute workflow steps in order."""
        try:
            workflow_steps = self.workflows[execution.workflow_name]
            execution.status = WorkflowStatus.RUNNING
            
            # Track completed steps for dependency resolution
            completed_steps = set()
            
            for step in workflow_steps:
                if not step.enabled:
                    self.logger.info(f"Skipping disabled step: {step.agent_name}")
                    continue
                
                # Check dependencies
                if not all(dep in completed_steps for dep in step.dependencies):
                    missing_deps = [dep for dep in step.dependencies if dep not in completed_steps]
                    raise ValueError(f"Missing dependencies for {step.agent_name}: {missing_deps}")
                
                # Check condition
                if step.condition and not step.condition(execution.metadata):
                    self.logger.info(f"Skipping step due to condition: {step.agent_name}")
                    continue
                
                # Execute step
                try:
                    result = await self._execute_workflow_step(step, execution, config)
                    execution.step_results[step.agent_name] = result
                    
                    if result.success:
                        execution.steps_completed += 1
                        completed_steps.add(step.agent_name)
                        self.logger.info(f"Step completed: {step.agent_name}")
                    else:
                        execution.steps_failed += 1
                        if step.retry_count < step.max_retries:
                            step.retry_count += 1
                            self.logger.warning(
                                f"Step failed, retrying ({step.retry_count}/{step.max_retries}): {step.agent_name}"
                            )
                            await asyncio.sleep(self.config.retry_delay)
                            continue
                        else:
                            raise Exception(f"Step failed after {step.max_retries} retries: {step.agent_name}")
                
                except Exception as e:
                    execution.steps_failed += 1
                    if step.retry_count < step.max_retries:
                        step.retry_count += 1
                        self.logger.warning(
                            f"Step error, retrying ({step.retry_count}/{step.max_retries}): {step.agent_name} - {e}"
                        )
                        await asyncio.sleep(self.config.retry_delay)
                        continue
                    else:
                        raise Exception(f"Step failed after {step.max_retries} retries: {step.agent_name} - {e}")
        
        except Exception as e:
            self.logger.error(f"Error executing workflow steps: {e}")
            raise
    
    async def _execute_workflow_step(
        self, 
        step: WorkflowStep, 
        execution: WorkflowExecution, 
        config: Optional[Dict[str, Any]]
    ) -> AgentResult:
        """Execute a single workflow step."""
        try:
            # Get or create agent instance
            agent = await self._get_agent_instance(step.agent_name, step.agent_class, config)
            
            # Create agent context
            context = AgentContext(
                execution_id=execution.execution_id,
                agent_name=step.agent_name,
                started_at=datetime.utcnow(),
                config=config or {},
                metadata=execution.metadata
            )
            
            # Execute agent with timeout
            timeout = step.timeout or self.config.default_timeout
            
            if step.parallel and self.config.enable_parallel_execution:
                # Execute in thread pool for parallel execution
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    lambda: asyncio.run(agent.process(context))
                )
            else:
                # Execute directly
                result = await asyncio.wait_for(
                    agent.process(context),
                    timeout=timeout
                )
            
            return result
        
        except asyncio.TimeoutError:
            self.logger.error(f"Step timeout: {step.agent_name}")
            return AgentResult(
                success=False,
                items_processed=0,
                items_successful=0,
                items_failed=1,
                execution_time=step.timeout or self.config.default_timeout,
                error_message=f"Timeout after {step.timeout or self.config.default_timeout} seconds"
            )
        
        except Exception as e:
            self.logger.error(f"Error executing step {step.agent_name}: {e}")
            return AgentResult(
                success=False,
                items_processed=0,
                items_successful=0,
                items_failed=1,
                execution_time=0.0,
                error_message=str(e)
            )
    
    async def _get_agent_instance(
        self, 
        agent_name: str, 
        agent_class: type, 
        config: Optional[Dict[str, Any]]
    ) -> BaseAgent:
        """Get or create agent instance."""
        try:
            if agent_name not in self.agent_instances:
                # Create new instance
                agent_config = config.get(agent_name, {}) if config else {}
                self.agent_instances[agent_name] = agent_class(agent_config)
            
            return self.agent_instances[agent_name]
        
        except Exception as e:
            self.logger.error(f"Error creating agent instance {agent_name}: {e}")
            raise
    
    async def _save_execution_history(self, execution: WorkflowExecution):
        """Save execution history to database."""
        try:
            with get_session() as session:
                # Create execution record
                db_execution = AgentExecution(
                    id=uuid.uuid4(),
                    execution_id=execution.execution_id,
                    agent_name=execution.workflow_name,
                    status=execution.status.value,
                    started_at=execution.started_at,
                    completed_at=execution.completed_at,
                    execution_time=execution.total_duration,
                    items_processed=execution.steps_completed,
                    items_successful=execution.steps_completed,
                    items_failed=execution.steps_failed,
                    error_message=execution.error_message,
                    metadata=json.dumps(execution.metadata)
                )
                
                session.add(db_execution)
                session.commit()
                
                self.logger.info(f"Saved execution history: {execution.execution_id}")
        
        except Exception as e:
            self.logger.error(f"Error saving execution history: {e}")
    
    async def get_workflow_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution status."""
        try:
            # Check active executions
            if execution_id in self.active_executions:
                return self.active_executions[execution_id]
            
            # Check history
            for execution in self.execution_history:
                if execution.execution_id == execution_id:
                    return execution
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error getting workflow status: {e}")
            return None
    
    async def cancel_workflow(self, execution_id: str) -> bool:
        """Cancel a running workflow."""
        try:
            if execution_id in self.active_executions:
                execution = self.active_executions[execution_id]
                execution.status = WorkflowStatus.CANCELLED
                execution.completed_at = datetime.utcnow()
                
                self.logger.info(f"Cancelled workflow: {execution_id}")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error cancelling workflow: {e}")
            return False
    
    async def get_workflow_metrics(self) -> Dict[str, Any]:
        """Get workflow execution metrics."""
        try:
            total_executions = len(self.execution_history)
            successful_executions = sum(
                1 for e in self.execution_history 
                if e.status == WorkflowStatus.COMPLETED
            )
            failed_executions = sum(
                1 for e in self.execution_history 
                if e.status == WorkflowStatus.FAILED
            )
            
            avg_duration = 0.0
            if total_executions > 0:
                durations = [
                    e.total_duration for e in self.execution_history 
                    if e.total_duration is not None
                ]
                avg_duration = sum(durations) / len(durations) if durations else 0.0
            
            return {
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "failed_executions": failed_executions,
                "success_rate": successful_executions / total_executions if total_executions > 0 else 0.0,
                "average_duration": avg_duration,
                "active_executions": len(self.active_executions),
                "workflows_available": list(self.workflows.keys())
            }
        
        except Exception as e:
            self.logger.error(f"Error getting workflow metrics: {e}")
            return {}
    
    async def get_agent_health(self) -> Dict[str, Any]:
        """Get health status of all agents."""
        try:
            health_status = {}
            
            for agent_name, agent_class in self.agents.items():
                try:
                    # Try to create agent instance
                    agent = await self._get_agent_instance(agent_name, agent_class, {})
                    
                    # Check if agent has health check method
                    if hasattr(agent, 'health_check'):
                        health = await agent.health_check()
                    else:
                        health = {"status": "healthy", "message": "No health check available"}
                    
                    health_status[agent_name] = health
                
                except Exception as e:
                    health_status[agent_name] = {
                        "status": "unhealthy",
                        "message": str(e)
                    }
            
            return health_status
        
        except Exception as e:
            self.logger.error(f"Error getting agent health: {e}")
            return {}
    
    def get_available_workflows(self) -> List[str]:
        """Get list of available workflows."""
        return list(self.workflows.keys())
    
    def get_workflow_definition(self, workflow_name: str) -> Optional[List[WorkflowStep]]:
        """Get workflow definition."""
        return self.workflows.get(workflow_name)
    
    async def shutdown(self):
        """Shutdown workflow engine."""
        try:
            # Cancel all active executions
            for execution_id in list(self.active_executions.keys()):
                await self.cancel_workflow(execution_id)
            
            # Shutdown thread pool
            self.executor.shutdown(wait=True)
            
            self.logger.info("Workflow engine shutdown complete")
        
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

