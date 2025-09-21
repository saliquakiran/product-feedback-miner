"""
Base agent framework for Product Feedback Miner.

This module provides the abstract base class and common functionality
that all agents in the pipeline will inherit from.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import uuid
import logging
import asyncio
from contextlib import asynccontextmanager

from database.models import AgentExecution, ProcessingStatus
from database import get_session
from config.settings import config
from config.api_keys import api_keys

logger = logging.getLogger(__name__)

@dataclass
class AgentResult:
    """Standard result format for all agents."""
    success: bool
    items_processed: int = 0
    items_successful: int = 0
    items_failed: int = 0
    execution_time: float = 0.0
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class AgentContext:
    """Context object passed between agents."""
    execution_id: str
    agent_name: str
    started_at: datetime
    config: Dict[str, Any]
    metadata: Dict[str, Any]

class BaseAgent(ABC):
    """
    Abstract base class for all agents in the Product Feedback Miner pipeline.
    
    Provides common functionality including:
    - Execution tracking and logging
    - Error handling and retry logic
    - Performance monitoring
    - Database session management
    """
    
    def __init__(self, name: str, config_overrides: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = self._merge_config(config_overrides or {})
        self.logger = logging.getLogger(f"agent.{name}")
        
        # Execution tracking
        self.current_execution: Optional[AgentExecution] = None
        self.execution_id: Optional[str] = None
        
    def _merge_config(self, overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Merge agent-specific config with global config."""
        base_config = {
            "max_retries": 3,
            "timeout": 300,  # 5 minutes
            "batch_size": 10,
            "max_workers": 1,
            "enable_metrics": True
        }
        base_config.update(overrides)
        return base_config
    
    @abstractmethod
    async def process(self, context: AgentContext) -> AgentResult:
        """
        Main processing method that each agent must implement.
        
        Args:
            context: Agent context with execution metadata
            
        Returns:
            AgentResult: Processing results and statistics
        """
        pass
    
    @abstractmethod
    def get_input_dependencies(self) -> List[str]:
        """
        Get list of agent names that this agent depends on for input.
        
        Returns:
            List of agent names that must complete before this agent runs
        """
        pass
    
    def get_output_type(self) -> str:
        """
        Get the type of data this agent produces.
        
        Returns:
            String identifier for the output data type
        """
        return f"{self.name}_output"
    
    async def execute(self, context: Optional[AgentContext] = None) -> AgentResult:
        """
        Execute the agent with proper error handling and monitoring.
        
        Args:
            context: Optional context, will create default if not provided
            
        Returns:
            AgentResult: Processing results
        """
        if context is None:
            context = self._create_default_context()
        
        self.execution_id = context.execution_id
        start_time = datetime.utcnow()
        
        # Create execution record
        self.current_execution = await self._create_execution_record(context)
        
        try:
            self.logger.info(f"Starting {self.name} execution {self.execution_id}")
            
            # Execute the main processing logic
            result = await self.process(context)
            
            # Update execution record with success
            await self._update_execution_record(
                status="completed",
                items_processed=result.items_processed,
                items_successful=result.items_successful,
                items_failed=result.items_failed,
                duration_seconds=(datetime.utcnow() - start_time).total_seconds()
            )
            
            self.logger.info(
                f"Completed {self.name} execution {self.execution_id}: "
                f"{result.items_successful}/{result.items_processed} successful"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Agent {self.name} execution failed: {str(e)}", exc_info=True)
            
            # Update execution record with failure
            await self._update_execution_record(
                status="failed",
                error_message=str(e),
                duration_seconds=(datetime.utcnow() - start_time).total_seconds()
            )
            
            return AgentResult(
                success=False,
                error_message=str(e),
                execution_time=(datetime.utcnow() - start_time).total_seconds()
            )
        
        finally:
            self.current_execution = None
            self.execution_id = None
    
    def _create_default_context(self) -> AgentContext:
        """Create a default context for the agent."""
        return AgentContext(
            execution_id=str(uuid.uuid4()),
            agent_name=self.name,
            started_at=datetime.utcnow(),
            config=self.config,
            metadata={}
        )
    
    async def _create_execution_record(self, context: AgentContext) -> AgentExecution:
        """Create a database record for this execution."""
        execution = AgentExecution(
            agent_name=self.name,
            execution_id=context.execution_id,
            status="running",
            started_at=context.started_at
        )
        
        with get_session() as session:
            session.add(execution)
            session.commit()
            session.refresh(execution)
        
        return execution
    
    async def _update_execution_record(
        self,
        status: str,
        items_processed: int = 0,
        items_successful: int = 0,
        items_failed: int = 0,
        error_message: Optional[str] = None,
        duration_seconds: Optional[float] = None
    ):
        """Update the execution record with results."""
        if not self.current_execution:
            return
        
        with get_session() as session:
            execution = session.query(AgentExecution).filter(
                AgentExecution.id == self.current_execution.id
            ).first()
            
            if execution:
                execution.status = status
                execution.completed_at = datetime.utcnow()
                execution.items_processed = items_processed
                execution.items_successful = items_successful
                execution.items_failed = items_failed
                execution.duration_seconds = duration_seconds
                execution.error_message = error_message
                
                session.commit()
    
    @asynccontextmanager
    async def get_db_session(self):
        """Get a database session with proper cleanup."""
        session = None
        try:
            with get_session() as db_session:
                yield db_session
        except Exception as e:
            self.logger.error(f"Database session error in {self.name}: {e}")
            raise
        finally:
            if session:
                session.close()
    
    async def retry_with_backoff(
        self,
        func,
        max_retries: Optional[int] = None,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0
    ) -> Any:
        """
        Retry a function with exponential backoff.
        
        Args:
            func: Async function to retry
            max_retries: Maximum number of retries (uses config default if None)
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Multiplier for delay after each retry
            
        Returns:
            Result of the function call
        """
        max_retries = max_retries or self.config.get("max_retries", 3)
        delay = base_delay
        
        for attempt in range(max_retries + 1):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries:
                    self.logger.error(f"Max retries exceeded for {func.__name__}: {e}")
                    raise
                
                self.logger.warning(
                    f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                    f"Retrying in {delay:.2f} seconds..."
                )
                
                await asyncio.sleep(delay)
                delay = min(delay * backoff_factor, max_delay)
    
    def log_metrics(self, metrics: Dict[str, Any]):
        """Log performance metrics for monitoring."""
        if self.config.get("enable_metrics", True):
            self.logger.info(f"Metrics for {self.name}: {metrics}")
    
    def validate_input(self, data: Any) -> bool:
        """
        Validate input data before processing.
        Override in subclasses for specific validation logic.
        
        Args:
            data: Input data to validate
            
        Returns:
            True if valid, False otherwise
        """
        return data is not None
    
    def prepare_output(self, data: Any) -> Any:
        """
        Prepare output data before returning.
        Override in subclasses for specific preparation logic.
        
        Args:
            data: Output data to prepare
            
        Returns:
            Prepared output data
        """
        return data

class AgentError(Exception):
    """Base exception for agent-related errors."""
    pass

class AgentTimeoutError(AgentError):
    """Exception raised when an agent operation times out."""
    pass

class AgentValidationError(AgentError):
    """Exception raised when agent input validation fails."""
    pass

class AgentDependencyError(AgentError):
    """Exception raised when agent dependencies are not met."""
    pass
