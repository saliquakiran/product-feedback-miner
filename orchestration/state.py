"""
State Management for Product Feedback Miner.

This module provides state management, persistence,
and coordination for the workflow engine.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import json
import pickle
import hashlib

from database.models import (
    ProcessedDocument, PrioritizationScore, Cluster, Ticket,
    FeedbackType, PriorityLevel, TicketStatus, ProcessingStatus
)
from database import get_session

logger = logging.getLogger(__name__)

class StateType(str, Enum):
    """Types of state data."""
    WORKFLOW = "workflow"
    AGENT = "agent"
    PIPELINE = "pipeline"
    USER = "user"
    SYSTEM = "system"

class StateStatus(str, Enum):
    """Status of state data."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    LOCKED = "locked"

@dataclass
class StateData:
    """Represents a piece of state data."""
    key: str
    value: Any
    state_type: StateType
    status: StateStatus = StateStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    checksum: Optional[str] = None

@dataclass
class PipelineState:
    """Represents the state of a pipeline execution."""
    execution_id: str
    workflow_name: str
    current_step: str
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    step_results: Dict[str, Any] = field(default_factory=dict)
    data_flow: Dict[str, Any] = field(default_factory=dict)
    status: str = "running"
    started_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentState:
    """Represents the state of an agent."""
    agent_name: str
    execution_id: str
    status: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    processing_metrics: Dict[str, Any] = field(default_factory=dict)
    error_info: Optional[Dict[str, Any]] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

class StateManager:
    """
    Manages state for the workflow engine.
    
    This manager:
    1. Stores and retrieves state data
    2. Manages pipeline execution state
    3. Handles agent state coordination
    4. Provides state persistence and recovery
    5. Manages state locks and concurrency
    6. Handles state expiration and cleanup
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize state manager."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # In-memory state storage
        self.state_store: Dict[str, StateData] = {}
        self.pipeline_states: Dict[str, PipelineState] = {}
        self.agent_states: Dict[str, AgentState] = {}
        
        # State locks for concurrency control
        self.state_locks: Dict[str, asyncio.Lock] = {}
        
        # Configuration
        self.default_ttl = self.config.get("default_ttl", 3600)  # 1 hour
        self.cleanup_interval = self.config.get("cleanup_interval", 300)  # 5 minutes
        self.max_state_size = self.config.get("max_state_size", 10 * 1024 * 1024)  # 10MB
        
        # Start cleanup task (will be created when needed)
        self.cleanup_task = None
    
    async def start_cleanup_task(self):
        """Start the cleanup task if not already running."""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_expired_states())
    
    async def set_state(
        self,
        key: str,
        value: Any,
        state_type: StateType,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Set state data.
        
        Args:
            key: State key
            value: State value
            state_type: Type of state
            ttl: Time to live in seconds
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        try:
            # Create state data
            expires_at = None
            if ttl:
                expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            elif self.default_ttl:
                expires_at = datetime.utcnow() + timedelta(seconds=self.default_ttl)
            
            # Calculate checksum
            checksum = self._calculate_checksum(value)
            
            state_data = StateData(
                key=key,
                value=value,
                state_type=state_type,
                expires_at=expires_at,
                metadata=metadata or {},
                checksum=checksum
            )
            
            # Store state
            self.state_store[key] = state_data
            
            self.logger.debug(f"State set: {key} ({state_type.value})")
            return True
        
        except Exception as e:
            self.logger.error(f"Error setting state {key}: {e}")
            return False
    
    async def get_state(
        self,
        key: str,
        state_type: Optional[StateType] = None
    ) -> Optional[Any]:
        """
        Get state data.
        
        Args:
            key: State key
            state_type: Expected state type
            
        Returns:
            State value or None
        """
        try:
            if key not in self.state_store:
                return None
            
            state_data = self.state_store[key]
            
            # Check if expired
            if state_data.expires_at and datetime.utcnow() > state_data.expires_at:
                state_data.status = StateStatus.EXPIRED
                return None
            
            # Check state type
            if state_type and state_data.state_type != state_type:
                return None
            
            # Check status
            if state_data.status != StateStatus.ACTIVE:
                return None
            
            # Verify checksum
            if state_data.checksum:
                current_checksum = self._calculate_checksum(state_data.value)
                if current_checksum != state_data.checksum:
                    self.logger.warning(f"State checksum mismatch: {key}")
                    return None
            
            return state_data.value
        
        except Exception as e:
            self.logger.error(f"Error getting state {key}: {e}")
            return None
    
    async def delete_state(self, key: str) -> bool:
        """Delete state data."""
        try:
            if key in self.state_store:
                del self.state_store[key]
                self.logger.debug(f"State deleted: {key}")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error deleting state {key}: {e}")
            return False
    
    async def list_states(
        self,
        state_type: Optional[StateType] = None,
        status: Optional[StateStatus] = None
    ) -> List[str]:
        """List state keys matching criteria."""
        try:
            keys = []
            
            for key, state_data in self.state_store.items():
                # Check state type
                if state_type and state_data.state_type != state_type:
                    continue
                
                # Check status
                if status and state_data.status != status:
                    continue
                
                # Check if expired
                if state_data.expires_at and datetime.utcnow() > state_data.expires_at:
                    continue
                
                keys.append(key)
            
            return keys
        
        except Exception as e:
            self.logger.error(f"Error listing states: {e}")
            return []
    
    async def set_pipeline_state(
        self,
        execution_id: str,
        workflow_name: str,
        current_step: str,
        **kwargs
    ) -> bool:
        """Set pipeline state."""
        try:
            pipeline_state = PipelineState(
                execution_id=execution_id,
                workflow_name=workflow_name,
                current_step=current_step,
                **kwargs
            )
            
            self.pipeline_states[execution_id] = pipeline_state
            
            self.logger.debug(f"Pipeline state set: {execution_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error setting pipeline state: {e}")
            return False
    
    async def get_pipeline_state(self, execution_id: str) -> Optional[PipelineState]:
        """Get pipeline state."""
        try:
            return self.pipeline_states.get(execution_id)
        
        except Exception as e:
            self.logger.error(f"Error getting pipeline state: {e}")
            return None
    
    async def update_pipeline_state(
        self,
        execution_id: str,
        **updates
    ) -> bool:
        """Update pipeline state."""
        try:
            if execution_id not in self.pipeline_states:
                return False
            
            pipeline_state = self.pipeline_states[execution_id]
            
            # Update fields
            for key, value in updates.items():
                if hasattr(pipeline_state, key):
                    setattr(pipeline_state, key, value)
            
            pipeline_state.updated_at = datetime.utcnow()
            
            self.logger.debug(f"Pipeline state updated: {execution_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error updating pipeline state: {e}")
            return False
    
    async def set_agent_state(
        self,
        agent_name: str,
        execution_id: str,
        status: str,
        **kwargs
    ) -> bool:
        """Set agent state."""
        try:
            agent_key = f"{agent_name}:{execution_id}"
            
            agent_state = AgentState(
                agent_name=agent_name,
                execution_id=execution_id,
                status=status,
                **kwargs
            )
            
            self.agent_states[agent_key] = agent_state
            
            self.logger.debug(f"Agent state set: {agent_key}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error setting agent state: {e}")
            return False
    
    async def get_agent_state(
        self,
        agent_name: str,
        execution_id: str
    ) -> Optional[AgentState]:
        """Get agent state."""
        try:
            agent_key = f"{agent_name}:{execution_id}"
            return self.agent_states.get(agent_key)
        
        except Exception as e:
            self.logger.error(f"Error getting agent state: {e}")
            return None
    
    async def update_agent_state(
        self,
        agent_name: str,
        execution_id: str,
        **updates
    ) -> bool:
        """Update agent state."""
        try:
            agent_key = f"{agent_name}:{execution_id}"
            
            if agent_key not in self.agent_states:
                return False
            
            agent_state = self.agent_states[agent_key]
            
            # Update fields
            for key, value in updates.items():
                if hasattr(agent_state, key):
                    setattr(agent_state, key, value)
            
            agent_state.updated_at = datetime.utcnow()
            
            self.logger.debug(f"Agent state updated: {agent_key}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error updating agent state: {e}")
            return False
    
    async def acquire_lock(self, key: str, timeout: int = 30) -> bool:
        """Acquire a state lock."""
        try:
            if key not in self.state_locks:
                self.state_locks[key] = asyncio.Lock()
            
            lock = self.state_locks[key]
            
            # Try to acquire lock with timeout
            try:
                await asyncio.wait_for(lock.acquire(), timeout=timeout)
                return True
            except asyncio.TimeoutError:
                return False
        
        except Exception as e:
            self.logger.error(f"Error acquiring lock {key}: {e}")
            return False
    
    async def release_lock(self, key: str) -> bool:
        """Release a state lock."""
        try:
            if key in self.state_locks:
                lock = self.state_locks[key]
                if lock.locked():
                    lock.release()
                    return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error releasing lock {key}: {e}")
            return False
    
    async def get_state_metrics(self) -> Dict[str, Any]:
        """Get state management metrics."""
        try:
            total_states = len(self.state_store)
            active_states = sum(
                1 for state in self.state_store.values()
                if state.status == StateStatus.ACTIVE
            )
            expired_states = sum(
                1 for state in self.state_store.values()
                if state.status == StateStatus.EXPIRED
            )
            
            # Calculate state size
            total_size = 0
            for state in self.state_store.values():
                try:
                    size = len(pickle.dumps(state.value))
                    total_size += size
                except:
                    pass
            
            # Count by type
            type_counts = {}
            for state in self.state_store.values():
                state_type = state.state_type.value
                type_counts[state_type] = type_counts.get(state_type, 0) + 1
            
            return {
                "total_states": total_states,
                "active_states": active_states,
                "expired_states": expired_states,
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "type_counts": type_counts,
                "pipeline_states": len(self.pipeline_states),
                "agent_states": len(self.agent_states),
                "active_locks": sum(1 for lock in self.state_locks.values() if lock.locked())
            }
        
        except Exception as e:
            self.logger.error(f"Error getting state metrics: {e}")
            return {}
    
    async def cleanup_expired_states(self) -> int:
        """Clean up expired states."""
        try:
            cleaned_count = 0
            now = datetime.utcnow()
            
            # Clean up expired states
            expired_keys = []
            for key, state_data in self.state_store.items():
                if state_data.expires_at and now > state_data.expires_at:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.state_store[key]
                cleaned_count += 1
            
            # Clean up old pipeline states (older than 24 hours)
            old_pipeline_keys = []
            cutoff_time = now - timedelta(hours=24)
            
            for execution_id, pipeline_state in self.pipeline_states.items():
                if pipeline_state.updated_at < cutoff_time:
                    old_pipeline_keys.append(execution_id)
            
            for key in old_pipeline_keys:
                del self.pipeline_states[key]
                cleaned_count += 1
            
            # Clean up old agent states (older than 24 hours)
            old_agent_keys = []
            for agent_key, agent_state in self.agent_states.items():
                if agent_state.updated_at < cutoff_time:
                    old_agent_keys.append(agent_key)
            
            for key in old_agent_keys:
                del self.agent_states[key]
                cleaned_count += 1
            
            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} expired states")
            
            return cleaned_count
        
        except Exception as e:
            self.logger.error(f"Error cleaning up expired states: {e}")
            return 0
    
    async def _cleanup_expired_states(self):
        """Background task to clean up expired states."""
        try:
            while True:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_expired_states()
        
        except asyncio.CancelledError:
            self.logger.info("State cleanup task cancelled")
        except Exception as e:
            self.logger.error(f"Error in state cleanup task: {e}")
    
    def _calculate_checksum(self, value: Any) -> str:
        """Calculate checksum for state value."""
        try:
            # Serialize value to bytes
            if isinstance(value, (str, int, float, bool)):
                data = str(value).encode('utf-8')
            else:
                data = pickle.dumps(value)
            
            # Calculate MD5 hash
            return hashlib.md5(data).hexdigest()
        
        except Exception:
            return ""
    
    async def export_state(self, state_type: Optional[StateType] = None) -> Dict[str, Any]:
        """Export state data for backup or migration."""
        try:
            export_data = {
                "exported_at": datetime.utcnow().isoformat(),
                "states": {},
                "pipeline_states": {},
                "agent_states": {}
            }
            
            # Export regular states
            for key, state_data in self.state_store.items():
                if state_type and state_data.state_type != state_type:
                    continue
                
                export_data["states"][key] = {
                    "value": state_data.value,
                    "state_type": state_data.state_type.value,
                    "status": state_data.status.value,
                    "created_at": state_data.created_at.isoformat(),
                    "updated_at": state_data.updated_at.isoformat(),
                    "expires_at": state_data.expires_at.isoformat() if state_data.expires_at else None,
                    "metadata": state_data.metadata,
                    "version": state_data.version
                }
            
            # Export pipeline states
            for execution_id, pipeline_state in self.pipeline_states.items():
                export_data["pipeline_states"][execution_id] = asdict(pipeline_state)
                # Convert datetime objects to ISO format
                for field in ["started_at", "updated_at"]:
                    if field in export_data["pipeline_states"][execution_id]:
                        export_data["pipeline_states"][execution_id][field] = getattr(pipeline_state, field).isoformat()
            
            # Export agent states
            for agent_key, agent_state in self.agent_states.items():
                export_data["agent_states"][agent_key] = asdict(agent_state)
                # Convert datetime objects to ISO format
                for field in ["started_at", "updated_at"]:
                    if field in export_data["agent_states"][agent_key]:
                        export_data["agent_states"][agent_key][field] = getattr(agent_state, field).isoformat()
            
            return export_data
        
        except Exception as e:
            self.logger.error(f"Error exporting state: {e}")
            return {}
    
    async def import_state(self, export_data: Dict[str, Any]) -> bool:
        """Import state data from backup or migration."""
        try:
            # Import regular states
            if "states" in export_data:
                for key, state_info in export_data["states"].items():
                    state_data = StateData(
                        key=key,
                        value=state_info["value"],
                        state_type=StateType(state_info["state_type"]),
                        status=StateStatus(state_info["status"]),
                        created_at=datetime.fromisoformat(state_info["created_at"]),
                        updated_at=datetime.fromisoformat(state_info["updated_at"]),
                        expires_at=datetime.fromisoformat(state_info["expires_at"]) if state_info["expires_at"] else None,
                        metadata=state_info["metadata"],
                        version=state_info["version"]
                    )
                    self.state_store[key] = state_data
            
            # Import pipeline states
            if "pipeline_states" in export_data:
                for execution_id, pipeline_info in export_data["pipeline_states"].items():
                    # Convert ISO format back to datetime
                    for field in ["started_at", "updated_at"]:
                        if field in pipeline_info:
                            pipeline_info[field] = datetime.fromisoformat(pipeline_info[field])
                    
                    pipeline_state = PipelineState(**pipeline_info)
                    self.pipeline_states[execution_id] = pipeline_state
            
            # Import agent states
            if "agent_states" in export_data:
                for agent_key, agent_info in export_data["agent_states"].items():
                    # Convert ISO format back to datetime
                    for field in ["started_at", "updated_at"]:
                        if field in agent_info:
                            agent_info[field] = datetime.fromisoformat(agent_info[field])
                    
                    agent_state = AgentState(**agent_info)
                    self.agent_states[agent_key] = agent_state
            
            self.logger.info("State data imported successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"Error importing state: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown state manager."""
        try:
            # Cancel cleanup task
            if hasattr(self, 'cleanup_task') and self.cleanup_task is not None:
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Release all locks
            for lock in self.state_locks.values():
                if lock.locked():
                    lock.release()
            
            self.logger.info("State manager shutdown complete")
        
        except Exception as e:
            self.logger.error(f"Error during state manager shutdown: {e}")
