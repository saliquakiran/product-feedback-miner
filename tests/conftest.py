"""
Pytest configuration for Product Feedback Miner tests.

This module sets up test fixtures and configuration for running tests
with PostgreSQL database.
"""

import pytest
import os
import tempfile
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.models import Base
from config.database import DatabaseManager

# Test database configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/product_feedback_miner_test"
)

@pytest.fixture(scope="session")
def test_database_url():
    """Get the test database URL."""
    return TEST_DATABASE_URL

@pytest.fixture(scope="session")
def test_engine(test_database_url):
    """Create test database engine."""
    engine = create_engine(
        test_database_url,
        poolclass=None,  # No connection pooling for tests
        echo=False
    )
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Clean up after all tests
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    
    yield session
    
    # Rollback any changes after each test
    session.rollback()
    session.close()

@pytest.fixture(scope="session")
def test_db_manager(test_database_url):
    """Create test database manager."""
    # Override the database URL for testing
    original_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_database_url
    
    # Create a new database manager for testing
    db_manager = DatabaseManager()
    
    yield db_manager
    
    # Restore original environment
    if original_url:
        os.environ["DATABASE_URL"] = original_url
    elif "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]

@pytest.fixture(autouse=True)
def clean_database(test_engine):
    """Clean database before each test."""
    # This runs before each test
    with test_engine.connect() as conn:
        # Truncate all tables but keep the structure
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f"TRUNCATE TABLE {table.name} RESTART IDENTITY CASCADE"))
        conn.commit()
    
    yield
    
    # This runs after each test (cleanup)
    pass
