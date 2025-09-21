"""
Custom exceptions for the Product Feedback Miner agent system.

This module defines all custom exceptions used throughout the agent pipeline,
providing clear error handling and debugging capabilities.
"""

class AgentError(Exception):
    """Base exception for all agent-related errors."""
    
    def __init__(self, message: str, agent_name: str = None, error_code: str = None):
        super().__init__(message)
        self.agent_name = agent_name
        self.error_code = error_code

class AgentTimeoutError(AgentError):
    """Exception raised when an agent operation times out."""
    
    def __init__(self, message: str, timeout_seconds: float = None, agent_name: str = None):
        super().__init__(message, agent_name, "TIMEOUT")
        self.timeout_seconds = timeout_seconds

class AgentValidationError(AgentError):
    """Exception raised when agent input validation fails."""
    
    def __init__(self, message: str, validation_field: str = None, agent_name: str = None):
        super().__init__(message, agent_name, "VALIDATION")
        self.validation_field = validation_field

class AgentDependencyError(AgentError):
    """Exception raised when agent dependencies are not met."""
    
    def __init__(self, message: str, missing_dependencies: list = None, agent_name: str = None):
        super().__init__(message, agent_name, "DEPENDENCY")
        self.missing_dependencies = missing_dependencies or []

class AgentConfigurationError(AgentError):
    """Exception raised when agent configuration is invalid."""
    
    def __init__(self, message: str, config_key: str = None, agent_name: str = None):
        super().__init__(message, agent_name, "CONFIGURATION")
        self.config_key = config_key

class AgentAPIError(AgentError):
    """Exception raised when external API calls fail."""
    
    def __init__(self, message: str, api_name: str = None, status_code: int = None, agent_name: str = None):
        super().__init__(message, agent_name, "API_ERROR")
        self.api_name = api_name
        self.status_code = status_code

class AgentDatabaseError(AgentError):
    """Exception raised when database operations fail."""
    
    def __init__(self, message: str, operation: str = None, agent_name: str = None):
        super().__init__(message, agent_name, "DATABASE")
        self.operation = operation

class AgentProcessingError(AgentError):
    """Exception raised when data processing fails."""
    
    def __init__(self, message: str, processing_stage: str = None, agent_name: str = None):
        super().__init__(message, agent_name, "PROCESSING")
        self.processing_stage = processing_stage

class AgentRateLimitError(AgentAPIError):
    """Exception raised when API rate limits are exceeded."""
    
    def __init__(self, message: str, api_name: str = None, retry_after: int = None, agent_name: str = None):
        super().__init__(message, api_name, 429, agent_name)
        self.retry_after = retry_after

class AgentQuotaExceededError(AgentAPIError):
    """Exception raised when API quotas are exceeded."""
    
    def __init__(self, message: str, api_name: str = None, agent_name: str = None):
        super().__init__(message, api_name, 429, agent_name)

class AgentAuthenticationError(AgentAPIError):
    """Exception raised when API authentication fails."""
    
    def __init__(self, message: str, api_name: str = None, agent_name: str = None):
        super().__init__(message, api_name, 401, agent_name)

class AgentPermissionError(AgentAPIError):
    """Exception raised when API permission is denied."""
    
    def __init__(self, message: str, api_name: str = None, agent_name: str = None):
        super().__init__(message, api_name, 403, agent_name)

class AgentNotFoundError(AgentAPIError):
    """Exception raised when a requested resource is not found."""
    
    def __init__(self, message: str, api_name: str = None, agent_name: str = None):
        super().__init__(message, api_name, 404, agent_name)

class AgentServerError(AgentAPIError):
    """Exception raised when external server returns an error."""
    
    def __init__(self, message: str, api_name: str = None, status_code: int = None, agent_name: str = None):
        super().__init__(message, agent_name, "SERVER_ERROR")
        self.api_name = api_name
        self.status_code = status_code

class AgentNetworkError(AgentError):
    """Exception raised when network operations fail."""
    
    def __init__(self, message: str, agent_name: str = None):
        super().__init__(message, agent_name, "NETWORK")

class AgentDataError(AgentError):
    """Exception raised when data format or content is invalid."""
    
    def __init__(self, message: str, data_type: str = None, agent_name: str = None):
        super().__init__(message, agent_name, "DATA")
        self.data_type = data_type

class AgentRetryError(AgentError):
    """Exception raised when all retry attempts are exhausted."""
    
    def __init__(self, message: str, max_retries: int = None, agent_name: str = None):
        super().__init__(message, agent_name, "RETRY_EXHAUSTED")
        self.max_retries = max_retries

class AgentOrchestrationError(AgentError):
    """Exception raised when agent orchestration fails."""
    
    def __init__(self, message: str, workflow_step: str = None, agent_name: str = None):
        super().__init__(message, agent_name, "ORCHESTRATION")
        self.workflow_step = workflow_step

class AgentMonitoringError(AgentError):
    """Exception raised when monitoring or metrics collection fails."""
    
    def __init__(self, message: str, metric_name: str = None, agent_name: str = None):
        super().__init__(message, agent_name, "MONITORING")
        self.metric_name = metric_name
