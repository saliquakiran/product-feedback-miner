"""
Database package for Product Feedback Miner.

This package provides database models, connections, and utilities.
"""

from .models import Base

# Import database functions directly to avoid circular imports
def get_session():
    """Get a database session."""
    from config.database import get_session as _get_session
    return _get_session()

def create_tables():
    """Create all database tables."""
    from config.database import create_tables as _create_tables
    return _create_tables()

def drop_tables():
    """Drop all database tables."""
    from config.database import drop_tables as _drop_tables
    return _drop_tables()

def enable_pgvector():
    """Enable pgvector extension."""
    from config.database import enable_pgvector as _enable_pgvector
    return _enable_pgvector()

def create_vector_indexes():
    """Create vector indexes."""
    from config.database import create_vector_indexes as _create_vector_indexes
    return _create_vector_indexes()

def health_check():
    """Check database health."""
    from config.database import health_check as _health_check
    return _health_check()

__all__ = [
    'Base',
    'get_session',
    'create_tables', 
    'drop_tables',
    'enable_pgvector',
    'create_vector_indexes',
    'health_check'
]
