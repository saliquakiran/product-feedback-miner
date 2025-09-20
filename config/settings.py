import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False

@dataclass
class ExaConfig:
    api_key: str
    base_url: str = "https://api.exa.ai"
    timeout: int = 30
    max_retries: int = 3
    rate_limit_per_minute: int = 60

@dataclass
class GitHubConfig:
    token: str
    base_url: str = "https://api.github.com"
    timeout: int = 30
    max_retries: int = 3
    rate_limit_per_minute: int = 5000

@dataclass
class HackerNewsConfig:
    base_url: str = "https://hacker-news.firebaseio.com/v0"
    timeout: int = 30
    max_retries: int = 3

@dataclass
class TwitterConfig:
    bearer_token: str
    base_url: str = "https://api.twitter.com/2"
    timeout: int = 30
    max_retries: int = 3
    rate_limit_per_minute: int = 300

@dataclass
class RedditConfig:
    client_id: str
    client_secret: str
    base_url: str = "https://oauth.reddit.com"
    user_agent: str = "Product-Feedback-Miner/1.0"
    timeout: int = 30
    max_retries: int = 3

@dataclass
class JiraConfig:
    base_url: str
    username: str
    api_token: str
    project_key: str
    timeout: int = 30
    max_retries: int = 3

@dataclass
class SlackConfig:
    webhook_url: str
    channel: str
    username: str = "Product Feedback Bot"

@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    username: str
    password: str
    from_email: str
    to_emails: list

@dataclass
class AgentConfig:
    # Ingestor settings
    ingestor_interval_minutes: int = 10
    ingestor_batch_size: int = 100
    ingestor_max_workers: int = 5
    
    # Normalizer settings
    normalizer_batch_size: int = 50
    normalizer_max_workers: int = 3
    
    # Classifier settings
    classifier_batch_size: int = 20
    classifier_timeout: int = 60
    
    # Clusterer settings
    clusterer_similarity_threshold: float = 0.8
    clusterer_min_cluster_size: int = 2
    clusterer_batch_size: int = 100
    
    # Prioritizer settings
    prioritizer_weights: Dict[str, float] = None
    prioritizer_revenue_components: list = None
    
    # Actioner settings
    actioner_priority_threshold: float = 0.7
    actioner_max_tickets_per_hour: int = 10
    
    # Digestor settings
    digestor_hourly_enabled: bool = True
    digestor_deep_dive_interval_hours: int = 4
    
    # Feedback loop settings
    feedback_loop_retrain_interval_hours: int = 24
    feedback_loop_min_samples: int = 100

@dataclass
class MonitoringConfig:
    enable_metrics: bool = True
    metrics_port: int = 8000
    health_check_interval: int = 30
    alert_webhook_url: Optional[str] = None
    log_level: str = "INFO"

@dataclass
class AppConfig:
    environment: Environment
    debug: bool
    database: DatabaseConfig
    exa: ExaConfig
    github: GitHubConfig
    hackernews: HackerNewsConfig
    twitter: Optional[TwitterConfig]
    reddit: Optional[RedditConfig]
    jira: Optional[JiraConfig]
    slack: Optional[SlackConfig]
    email: Optional[EmailConfig]
    agents: AgentConfig
    monitoring: MonitoringConfig

def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    
    # Default agent weights
    default_weights = {
        "severity": 0.35,
        "reach": 0.25,
        "recency": 0.20,
        "persona_weight": 0.20
    }
    
    # Default revenue-critical components
    default_revenue_components = [
        "login", "authentication", "checkout", "payment", 
        "api", "core", "database", "security"
    ]
    
    # Database configuration
    database = DatabaseConfig(
        host=os.getenv("DATABASE_HOST", "localhost"),
        port=int(os.getenv("DATABASE_PORT", "5432")),
        database=os.getenv("DATABASE_NAME", "product_feedback_miner"),
        username=os.getenv("DATABASE_USER", "postgres"),
        password=os.getenv("DATABASE_PASSWORD", "password"),
        pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "20")),
        echo=os.getenv("DATABASE_ECHO", "false").lower() == "true"
    )
    
    # External API configurations
    exa = ExaConfig(
        api_key=os.getenv("EXA_API_KEY", ""),
        base_url=os.getenv("EXA_BASE_URL", "https://api.exa.ai"),
        timeout=int(os.getenv("EXA_TIMEOUT", "30")),
        max_retries=int(os.getenv("EXA_MAX_RETRIES", "3")),
        rate_limit_per_minute=int(os.getenv("EXA_RATE_LIMIT", "60"))
    )
    
    github = GitHubConfig(
        token=os.getenv("GITHUB_TOKEN", ""),
        base_url=os.getenv("GITHUB_BASE_URL", "https://api.github.com"),
        timeout=int(os.getenv("GITHUB_TIMEOUT", "30")),
        max_retries=int(os.getenv("GITHUB_MAX_RETRIES", "3")),
        rate_limit_per_minute=int(os.getenv("GITHUB_RATE_LIMIT", "5000"))
    )
    
    hackernews = HackerNewsConfig(
        base_url=os.getenv("HACKERNEWS_BASE_URL", "https://hacker-news.firebaseio.com/v0"),
        timeout=int(os.getenv("HACKERNEWS_TIMEOUT", "30")),
        max_retries=int(os.getenv("HACKERNEWS_MAX_RETRIES", "3"))
    )
    
    # Twitter configuration
    twitter = None
    if os.getenv("TWITTER_BEARER_TOKEN"):
        twitter = TwitterConfig(
            bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
            base_url=os.getenv("TWITTER_BASE_URL", "https://api.twitter.com/2"),
            timeout=int(os.getenv("TWITTER_TIMEOUT", "30")),
            max_retries=int(os.getenv("TWITTER_MAX_RETRIES", "3")),
            rate_limit_per_minute=int(os.getenv("TWITTER_RATE_LIMIT", "300"))
        )
    
    # Reddit configuration
    reddit = None
    if os.getenv("REDDIT_CLIENT_ID") and os.getenv("REDDIT_CLIENT_SECRET"):
        reddit = RedditConfig(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            base_url=os.getenv("REDDIT_BASE_URL", "https://oauth.reddit.com"),
            user_agent=os.getenv("REDDIT_USER_AGENT", "Product-Feedback-Miner/1.0"),
            timeout=int(os.getenv("REDDIT_TIMEOUT", "30")),
            max_retries=int(os.getenv("REDDIT_MAX_RETRIES", "3"))
        )
    
    # Optional integrations
    jira = None
    if os.getenv("JIRA_BASE_URL"):
        jira = JiraConfig(
            base_url=os.getenv("JIRA_BASE_URL"),
            username=os.getenv("JIRA_USERNAME", ""),
            api_token=os.getenv("JIRA_API_TOKEN", ""),
            project_key=os.getenv("JIRA_PROJECT_KEY", ""),
            timeout=int(os.getenv("JIRA_TIMEOUT", "30")),
            max_retries=int(os.getenv("JIRA_MAX_RETRIES", "3"))
        )
    
    slack = None
    if os.getenv("SLACK_WEBHOOK_URL"):
        slack = SlackConfig(
            webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
            channel=os.getenv("SLACK_CHANNEL", "#product-feedback"),
            username=os.getenv("SLACK_USERNAME", "Product Feedback Bot")
        )
    
    email = None
    if os.getenv("SMTP_HOST"):
        email = EmailConfig(
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            username=os.getenv("SMTP_USERNAME", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            from_email=os.getenv("FROM_EMAIL", ""),
            to_emails=os.getenv("TO_EMAILS", "").split(",") if os.getenv("TO_EMAILS") else []
        )
    
    # Agent configuration
    agents = AgentConfig(
        ingestor_interval_minutes=int(os.getenv("INGESTOR_INTERVAL_MINUTES", "10")),
        ingestor_batch_size=int(os.getenv("INGESTOR_BATCH_SIZE", "100")),
        ingestor_max_workers=int(os.getenv("INGESTOR_MAX_WORKERS", "5")),
        
        normalizer_batch_size=int(os.getenv("NORMALIZER_BATCH_SIZE", "50")),
        normalizer_max_workers=int(os.getenv("NORMALIZER_MAX_WORKERS", "3")),
        
        classifier_batch_size=int(os.getenv("CLASSIFIER_BATCH_SIZE", "20")),
        classifier_timeout=int(os.getenv("CLASSIFIER_TIMEOUT", "60")),
        
        clusterer_similarity_threshold=float(os.getenv("CLUSTERER_SIMILARITY_THRESHOLD", "0.8")),
        clusterer_min_cluster_size=int(os.getenv("CLUSTERER_MIN_CLUSTER_SIZE", "2")),
        clusterer_batch_size=int(os.getenv("CLUSTERER_BATCH_SIZE", "100")),
        
        prioritizer_weights=default_weights,
        prioritizer_revenue_components=default_revenue_components,
        
        actioner_priority_threshold=float(os.getenv("ACTIONER_PRIORITY_THRESHOLD", "0.7")),
        actioner_max_tickets_per_hour=int(os.getenv("ACTIONER_MAX_TICKETS_PER_HOUR", "10")),
        
        digestor_hourly_enabled=os.getenv("DIGESTOR_HOURLY_ENABLED", "true").lower() == "true",
        digestor_deep_dive_interval_hours=int(os.getenv("DIGESTOR_DEEP_DIVE_INTERVAL_HOURS", "4")),
        
        feedback_loop_retrain_interval_hours=int(os.getenv("FEEDBACK_LOOP_RETRAIN_INTERVAL_HOURS", "24")),
        feedback_loop_min_samples=int(os.getenv("FEEDBACK_LOOP_MIN_SAMPLES", "100"))
    )
    
    # Monitoring configuration
    monitoring = MonitoringConfig(
        enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true",
        metrics_port=int(os.getenv("METRICS_PORT", "8000")),
        health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
        alert_webhook_url=os.getenv("ALERT_WEBHOOK_URL"),
        log_level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    return AppConfig(
        environment=Environment(os.getenv("ENVIRONMENT", "development")),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        database=database,
        exa=exa,
        github=github,
        hackernews=hackernews,
        twitter=twitter,
        reddit=reddit,
        jira=jira,
        slack=slack,
        email=email,
        agents=agents,
        monitoring=monitoring
    )

# Global config instance
config = load_config()
