from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime
from enum import Enum

Base = declarative_base()

class FeedbackType(str, Enum):
    BUG = "bug"
    FEATURE_REQUEST = "feature_request"
    UX = "ux"
    PRICING = "pricing"
    DOCS = "docs"
    OTHER = "other"

class PriorityLevel(int, Enum):
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    MINIMAL = 1

class SourceType(str, Enum):
    EXA_BLOG = "exa_blog"
    EXA_FORUM = "exa_forum"
    EXA_REVIEW = "exa_review"
    GITHUB_ISSUE = "github_issue"
    GITHUB_DISCUSSION = "github_discussion"
    HACKER_NEWS = "hacker_news"
    STACKOVERFLOW = "stackoverflow"
    REDDIT = "reddit"
    REDDIT_COMMENT = "reddit_comment"
    TWITTER_POST = "twitter_post"
    TWITTER_MENTION = "twitter_mention"
    APP_STORE = "app_store"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    WONT_FIX = "wont_fix"
    DUPLICATE = "duplicate"

# Raw feedback data from external sources
class RawFeedback(Base):
    __tablename__ = "raw_feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(String(50), nullable=False)
    source_id = Column(String(255), nullable=False)  # External ID from source
    url = Column(Text, nullable=False)
    title = Column(Text)
    content = Column(Text, nullable=False)
    author = Column(String(255))
    author_url = Column(Text)
    timestamp = Column(DateTime, nullable=False)
    raw_metadata = Column(JSON)  # Source-specific metadata
    language = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    processed_docs = relationship("ProcessedDocument", back_populates="raw_feedback")
    
    # Indexes
    __table_args__ = (
        Index('idx_raw_feedback_source', 'source_type', 'source_id'),
        Index('idx_raw_feedback_timestamp', 'timestamp'),
        Index('idx_raw_feedback_url', 'url'),
    )

# Cleaned and normalized feedback documents
class ProcessedDocument(Base):
    __tablename__ = "processed_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raw_feedback_id = Column(UUID(as_uuid=True), ForeignKey('raw_feedback.id'), nullable=False)
    
    # Cleaned content
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    author = Column(String(255))
    timestamp = Column(DateTime, nullable=False)
    url = Column(Text, nullable=False)
    
    # Processing metadata
    language = Column(String(10))
    word_count = Column(Integer)
    processing_status = Column(String(20), default=ProcessingStatus.PENDING)
    processing_errors = Column(JSON)
    
    # Classification results
    feedback_type = Column(String(50))
    severity_score = Column(Float)  # 0-1 scale
    component = Column(String(100))
    version = Column(String(50))
    confidence_score = Column(Float)  # Classification confidence
    
    # Embedding for clustering
    embedding = Column(Vector(1536))  # OpenAI embedding dimension
    
    # Clustering
    cluster_id = Column(UUID(as_uuid=True), ForeignKey('clusters.id'), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    raw_feedback = relationship("RawFeedback", back_populates="processed_docs")
    cluster_memberships = relationship("ClusterMembership", back_populates="document")
    tickets = relationship("Ticket", back_populates="source_document")
    
    # Indexes
    __table_args__ = (
        Index('idx_processed_docs_type', 'feedback_type'),
        Index('idx_processed_docs_severity', 'severity_score'),
        Index('idx_processed_docs_component', 'component'),
        Index('idx_processed_docs_timestamp', 'timestamp'),
    )

# Feedback clusters
class Cluster(Base):
    __tablename__ = "clusters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    summary = Column(Text)
    
    # Cluster metadata
    feedback_type = Column(String(50))
    component = Column(String(100))
    avg_severity = Column(Float)
    member_count = Column(Integer, default=0)
    
    # Clustering metadata
    centroid_embedding = Column(Vector(1536))
    similarity_threshold = Column(Float, default=0.8)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    memberships = relationship("ClusterMembership", back_populates="cluster")
    tickets = relationship("Ticket", back_populates="cluster")
    
    # Indexes
    __table_args__ = (
        Index('idx_clusters_type', 'feedback_type'),
        Index('idx_clusters_component', 'component'),
        Index('idx_clusters_severity', 'avg_severity'),
    )

# Many-to-many relationship between documents and clusters
class ClusterMembership(Base):
    __tablename__ = "cluster_memberships"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id = Column(UUID(as_uuid=True), ForeignKey('clusters.id'), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey('processed_documents.id'), nullable=False)
    
    # Membership metadata
    similarity_score = Column(Float, nullable=False)
    is_representative = Column(Boolean, default=False)  # Representative document for cluster
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    cluster = relationship("Cluster", back_populates="memberships")
    document = relationship("ProcessedDocument", back_populates="cluster_memberships")
    
    # Indexes
    __table_args__ = (
        Index('idx_cluster_memberships_cluster', 'cluster_id'),
        Index('idx_cluster_memberships_document', 'document_id'),
        Index('idx_cluster_memberships_similarity', 'similarity_score'),
    )

# Prioritization scores and decisions
class PrioritizationScore(Base):
    __tablename__ = "prioritization_scores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('processed_documents.id'), nullable=False)
    cluster_id = Column(UUID(as_uuid=True), ForeignKey('clusters.id'))
    
    # Scoring components
    severity_score = Column(Float, nullable=False)  # 0-1
    reach_score = Column(Float, nullable=False)  # 0-1
    recency_score = Column(Float, nullable=False)  # 0-1
    persona_weight = Column(Float, nullable=False)  # 0-1
    
    # Final scores
    priority_score = Column(Float, nullable=False)  # 0-1
    priority_level = Column(Integer, nullable=False)  # 1-5
    
    # Revenue impact
    is_revenue_critical = Column(Boolean, default=False)
    revenue_impact_multiplier = Column(Float, default=1.0)
    
    # Scoring metadata
    scoring_version = Column(String(50))  # Track scoring algorithm version
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("ProcessedDocument")
    cluster = relationship("Cluster")
    
    # Indexes
    __table_args__ = (
        Index('idx_prioritization_priority', 'priority_level'),
        Index('idx_prioritization_score', 'priority_score'),
        Index('idx_prioritization_document', 'document_id'),
    )

# Generated tickets (Jira/GitHub)
class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_document_id = Column(UUID(as_uuid=True), ForeignKey('processed_documents.id'))
    cluster_id = Column(UUID(as_uuid=True), ForeignKey('clusters.id'))
    
    # External ticket info
    external_id = Column(String(255), nullable=False)  # Jira/GitHub ticket ID
    external_url = Column(Text, nullable=False)
    platform = Column(String(20), nullable=False)  # 'jira' or 'github'
    
    # Ticket content
    title = Column(Text, nullable=False)
    description = Column(Text)
    acceptance_criteria = Column(Text)
    repro_steps = Column(Text)
    
    # Status and priority
    status = Column(String(20), default=TicketStatus.OPEN)
    priority = Column(Integer)  # 1-5
    labels = Column(JSON)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced_at = Column(DateTime)
    
    # Relationships
    source_document = relationship("ProcessedDocument", back_populates="tickets")
    cluster = relationship("Cluster", back_populates="tickets")
    feedback_loop_data = relationship("FeedbackLoopData", back_populates="ticket")
    
    # Indexes
    __table_args__ = (
        Index('idx_tickets_external', 'platform', 'external_id'),
        Index('idx_tickets_status', 'status'),
        Index('idx_tickets_priority', 'priority'),
    )

# Learning and feedback loop data
class FeedbackLoopData(Base):
    __tablename__ = "feedback_loop_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey('tickets.id'), nullable=False)
    
    # Engineer feedback
    engineer_label = Column(String(50))  # 'fixed', 'wont_fix', 'duplicate', etc.
    engineer_notes = Column(Text)
    actual_severity = Column(Float)  # Engineer's assessment
    
    # Resolution data
    resolution_time_hours = Column(Float)
    effort_estimate = Column(String(20))  # 'small', 'medium', 'large'
    actual_effort = Column(String(20))
    
    # Learning metadata
    was_prioritized_correctly = Column(Boolean)
    scoring_accuracy = Column(Float)  # How well our scoring predicted reality
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ticket = relationship("Ticket", back_populates="feedback_loop_data")
    
    # Indexes
    __table_args__ = (
        Index('idx_feedback_loop_ticket', 'ticket_id'),
        Index('idx_feedback_loop_label', 'engineer_label'),
        Index('idx_feedback_loop_accuracy', 'scoring_accuracy'),
    )

# Agent execution logs and health monitoring
class AgentExecution(Base):
    __tablename__ = "agent_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_name = Column(String(100), nullable=False)
    execution_id = Column(String(255), nullable=False)  # Unique execution identifier
    
    # Execution metadata
    status = Column(String(20), nullable=False)  # 'running', 'completed', 'failed'
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    
    # Processing stats
    items_processed = Column(Integer, default=0)
    items_successful = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text)
    error_details = Column(JSON)
    
    # Performance metrics
    memory_usage_mb = Column(Float)
    cpu_usage_percent = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_agent_executions_agent', 'agent_name'),
        Index('idx_agent_executions_status', 'status'),
        Index('idx_agent_executions_started', 'started_at'),
    )

# System configuration and learning weights
class SystemConfig(Base):
    __tablename__ = "system_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_key = Column(String(100), nullable=False, unique=True)
    config_value = Column(JSON, nullable=False)
    description = Column(Text)
    
    # Versioning
    version = Column(String(50))
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_system_config_key', 'config_key'),
        Index('idx_system_config_active', 'is_active'),
    )

# Digest and report generation
class DigestReport(Base):
    __tablename__ = "digest_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_type = Column(String(50), nullable=False)  # 'hourly', 'deep_dive'
    
    # Report content
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    
    # Report metadata
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    top_clusters = Column(JSON)  # Array of cluster IDs and summaries
    
    # Delivery
    delivery_status = Column(String(20), default='pending')  # 'pending', 'sent', 'failed'
    delivery_method = Column(String(20))  # 'slack', 'email'
    delivery_recipients = Column(JSON)
    delivered_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_digest_reports_type', 'report_type'),
        Index('idx_digest_reports_period', 'period_start', 'period_end'),
        Index('idx_digest_reports_delivery', 'delivery_status'),
    )

# Scheduled jobs for workflow automation
class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    workflow_name = Column(String(100), nullable=False)
    
    # Schedule configuration
    schedule_type = Column(String(20), nullable=False)  # 'cron', 'interval', 'once'
    schedule_value = Column(String(255), nullable=False)  # cron expression or interval
    timezone = Column(String(50), default='UTC')
    
    # Execution settings
    enabled = Column(Boolean, default=True)
    max_concurrent = Column(Integer, default=1)
    timeout = Column(Integer)  # seconds
    
    # Configuration
    config = Column(JSON)  # Additional configuration
    
    # Status
    status = Column(String(20), default='active')  # 'active', 'paused', 'disabled'
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_scheduled_jobs_workflow', 'workflow_name'),
        Index('idx_scheduled_jobs_enabled', 'enabled'),
        Index('idx_scheduled_jobs_status', 'status'),
    )

# Job execution history
class JobExecution(Base):
    __tablename__ = "job_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey('scheduled_jobs.id'), nullable=False)
    execution_id = Column(String(255), nullable=False, unique=True)
    
    # Execution details
    workflow_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # 'pending', 'running', 'completed', 'failed', 'cancelled'
    
    # Timing
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    
    # Results
    items_processed = Column(Integer, default=0)
    items_successful = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text)
    error_details = Column(JSON)
    
    # Next run (for recurring jobs)
    next_run = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    job = relationship("ScheduledJob", backref="executions")
    
    # Indexes
    __table_args__ = (
        Index('idx_job_executions_job', 'job_id'),
        Index('idx_job_executions_status', 'status'),
        Index('idx_job_executions_started', 'started_at'),
        Index('idx_job_executions_workflow', 'workflow_name'),
    )
