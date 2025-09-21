"""
Data models for the Ingestor Agent.

This module defines the data structures used by the Ingestor Agent
for collecting and processing raw feedback data.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class IngestorStatus(str, Enum):
    """Status of ingestion process."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class IngestorConfig:
    """Configuration for the Ingestor Agent."""
    # GitHub configuration
    repositories: List[Dict[str, Any]]
    github_labels: List[str]
    include_discussions: bool = False
    
    # Hacker News configuration
    hn_keywords: List[str]
    hn_top_stories_limit: int = 50
    hn_keyword_limit: int = 30
    hn_min_score: int = 10
    
    # Exa AI configuration
    exa_queries: List[str]
    exa_results_limit: int = 50
    exa_query_limit: int = 20
    
    # General configuration
    product_name: str = "Product"
    days_back: int = 7
    batch_size: int = 100
    max_workers: int = 5

@dataclass
class IngestorResult:
    """Result of ingestion process."""
    status: IngestorStatus
    items_processed: int
    items_successful: int
    items_failed: int
    sources_processed: int
    execution_time: float
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class SourceData:
    """Data collected from a single source."""
    source_type: str
    source_id: str
    url: str
    title: str
    content: str
    author: str
    author_url: str
    timestamp: datetime
    raw_metadata: Dict[str, Any]

@dataclass
class IngestorMetrics:
    """Metrics for the Ingestor Agent."""
    total_runs: int
    successful_runs: int
    failed_runs: int
    total_items_processed: int
    total_items_successful: int
    total_items_failed: int
    average_execution_time: float
    last_run_time: Optional[datetime]
    last_run_status: Optional[IngestorStatus]
    api_connection_status: Dict[str, bool]
