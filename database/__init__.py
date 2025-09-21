"""
Database package for Product Feedback Miner.

This package provides database models, connections, and utilities.
"""

from .models import Base
from config.database import get_session, create_tables, drop_tables, enable_pgvector, create_vector_indexes, health_check

__all__ = [
    'Base',
    'get_session',
    'create_tables', 
    'drop_tables',
    'enable_pgvector',
    'create_vector_indexes',
    'health_check'
]
