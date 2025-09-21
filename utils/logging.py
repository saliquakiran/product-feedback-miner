"""
Centralized logging configuration for Product Feedback Miner.

This module provides structured logging with proper formatting,
log levels, and integration with monitoring systems.
"""

import logging
import logging.handlers
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from config.settings import config

class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'agent_name'):
            log_entry['agent_name'] = record.agent_name
        if hasattr(record, 'execution_id'):
            log_entry['execution_id'] = record.execution_id
        if hasattr(record, 'items_processed'):
            log_entry['items_processed'] = record.items_processed
        if hasattr(record, 'duration_seconds'):
            log_entry['duration_seconds'] = record.duration_seconds
        if hasattr(record, 'error_code'):
            log_entry['error_code'] = record.error_code
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)

class AgentLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds agent-specific context to log records."""
    
    def __init__(self, logger: logging.Logger, agent_name: str, execution_id: str = None):
        super().__init__(logger, {
            'agent_name': agent_name,
            'execution_id': execution_id
        })
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process log message and add agent context."""
        # Add agent context to extra fields
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        kwargs['extra'].update(self.extra)
        return msg, kwargs

def setup_logging(log_level: str = None, log_file: str = None) -> logging.Logger:
    """
    Set up centralized logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        
    Returns:
        Configured root logger
    """
    # Use config values if not provided
    log_level = log_level or config.monitoring.log_level
    log_file = log_file or "logs/product_feedback_miner.log"
    
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with structured formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    if config.environment.value == "production":
        # Use structured JSON logging in production
        console_formatter = StructuredFormatter()
    else:
        # Use human-readable formatting in development
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with structured logging
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)  # Always debug level for files
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    return root_logger

def get_agent_logger(agent_name: str, execution_id: str = None) -> AgentLoggerAdapter:
    """
    Get a logger with agent-specific context.
    
    Args:
        agent_name: Name of the agent
        execution_id: Optional execution ID for this run
        
    Returns:
        Logger adapter with agent context
    """
    logger = logging.getLogger(f"agent.{agent_name}")
    return AgentLoggerAdapter(logger, agent_name, execution_id)

def log_agent_execution(
    logger: logging.Logger,
    agent_name: str,
    execution_id: str,
    status: str,
    items_processed: int = 0,
    items_successful: int = 0,
    items_failed: int = 0,
    duration_seconds: float = 0.0,
    error_message: str = None
):
    """
    Log agent execution metrics.
    
    Args:
        logger: Logger instance
        agent_name: Name of the agent
        execution_id: Unique execution identifier
        status: Execution status (running, completed, failed)
        items_processed: Number of items processed
        items_successful: Number of items processed successfully
        items_failed: Number of items that failed processing
        duration_seconds: Execution duration in seconds
        error_message: Error message if execution failed
    """
    extra = {
        'agent_name': agent_name,
        'execution_id': execution_id,
        'items_processed': items_processed,
        'items_successful': items_successful,
        'items_failed': items_failed,
        'duration_seconds': duration_seconds
    }
    
    if error_message:
        extra['error_message'] = error_message
        extra['error_code'] = 'EXECUTION_FAILED'
        logger.error(f"Agent {agent_name} execution failed", extra=extra)
    else:
        logger.info(f"Agent {agent_name} execution completed", extra=extra)

def log_api_call(
    logger: logging.Logger,
    api_name: str,
    endpoint: str,
    method: str,
    status_code: int,
    duration_seconds: float,
    response_size: int = None,
    error_message: str = None
):
    """
    Log API call metrics.
    
    Args:
        logger: Logger instance
        api_name: Name of the API service
        endpoint: API endpoint called
        method: HTTP method used
        status_code: HTTP status code
        duration_seconds: Request duration in seconds
        response_size: Size of response in bytes
        error_message: Error message if call failed
    """
    extra = {
        'api_name': api_name,
        'endpoint': endpoint,
        'method': method,
        'status_code': status_code,
        'duration_seconds': duration_seconds
    }
    
    if response_size:
        extra['response_size'] = response_size
    
    if error_message:
        extra['error_message'] = error_message
        extra['error_code'] = 'API_CALL_FAILED'
        logger.error(f"API call failed: {api_name} {method} {endpoint}", extra=extra)
    else:
        logger.info(f"API call: {api_name} {method} {endpoint}", extra=extra)

def log_database_operation(
    logger: logging.Logger,
    operation: str,
    table: str,
    duration_seconds: float,
    rows_affected: int = None,
    error_message: str = None
):
    """
    Log database operation metrics.
    
    Args:
        logger: Logger instance
        operation: Database operation (SELECT, INSERT, UPDATE, DELETE)
        table: Database table name
        duration_seconds: Operation duration in seconds
        rows_affected: Number of rows affected
        error_message: Error message if operation failed
    """
    extra = {
        'operation': operation,
        'table': table,
        'duration_seconds': duration_seconds
    }
    
    if rows_affected is not None:
        extra['rows_affected'] = rows_affected
    
    if error_message:
        extra['error_message'] = error_message
        extra['error_code'] = 'DATABASE_OPERATION_FAILED'
        logger.error(f"Database operation failed: {operation} on {table}", extra=extra)
    else:
        logger.info(f"Database operation: {operation} on {table}", extra=extra)

# Initialize logging on module import
setup_logging()
