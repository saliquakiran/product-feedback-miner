"""
Database configuration and connection management for Product Feedback Miner.

This module handles database connections, session management, and provides
utilities for working with PostgreSQL and pgvector.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator, Optional
import logging

from .settings import config
from database.models import Base

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize the database engine with proper configuration."""
        database_url = self._build_database_url()
        
        # Create engine with connection pooling
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=config.database.pool_size,
            max_overflow=config.database.max_overflow,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,   # Recycle connections every hour
            echo=config.database.echo,
            future=True
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info(f"Database engine initialized for {config.database.host}:{config.database.port}")
    
    def _build_database_url(self) -> str:
        """Build the database URL from configuration."""
        return (
            f"postgresql://{config.database.username}:{config.database.password}"
            f"@{config.database.host}:{config.database.port}/{config.database.database}"
        )
    
    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    def enable_pgvector_extension(self):
        """Enable the pgvector extension for vector operations."""
        try:
            with self.get_session() as session:
                session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                session.commit()
                logger.info("pgvector extension enabled")
        except Exception as e:
            logger.error(f"Failed to enable pgvector extension: {e}")
            raise
    
    def create_vector_indexes(self):
        """Create vector indexes for efficient similarity search."""
        try:
            with self.get_session() as session:
                # Create vector index for processed documents embeddings
                session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_processed_docs_embedding_cosine 
                    ON processed_documents USING ivfflat (embedding vector_cosine_ops) 
                    WITH (lists = 100)
                """))
                
                # Create vector index for cluster centroids
                session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_clusters_centroid_cosine 
                    ON clusters USING ivfflat (centroid_embedding vector_cosine_ops) 
                    WITH (lists = 100)
                """))
                
                session.commit()
                logger.info("Vector indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to create vector indexes: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_dependency(self) -> Generator[Session, None, None]:
        """Dependency for FastAPI or similar frameworks."""
        return self.get_session()
    
    def health_check(self) -> bool:
        """Check if the database is healthy and accessible."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def get_connection_info(self) -> dict:
        """Get database connection information for monitoring."""
        return {
            "host": config.database.host,
            "port": config.database.port,
            "database": config.database.database,
            "pool_size": config.database.pool_size,
            "max_overflow": config.database.max_overflow,
            "healthy": self.health_check()
        }

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions
def get_session() -> Generator[Session, None, None]:
    """Get a database session."""
    return db_manager.get_session()

def create_tables():
    """Create all database tables."""
    db_manager.create_tables()

def drop_tables():
    """Drop all database tables."""
    db_manager.drop_tables()

def enable_pgvector():
    """Enable pgvector extension."""
    db_manager.enable_pgvector_extension()

def create_vector_indexes():
    """Create vector indexes."""
    db_manager.create_vector_indexes()

def health_check() -> bool:
    """Check database health."""
    return db_manager.health_check()
