#!/usr/bin/env python3
"""
Tests for database setup.

This module tests database setup functionality:
- Database model creation
- Database constraints
- Database health checks
"""

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database.models import Base

# Test database URL
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def test_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()

class TestDatabaseModelCreation:
    """Tests for database model creation."""
    
    def test_database_models_creation(self, test_engine):
        """Test that all database models can be created."""
        assert test_engine is not None
        
        # Test that we can query the metadata using inspect
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            'raw_feedback', 'processed_documents', 'clusters',
            'cluster_memberships', 'prioritization_scores', 'tickets',
            'feedback_loop_data', 'agent_executions', 'system_config',
            'digest_reports'
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found in database"
    
    def test_database_tables_have_columns(self, test_engine):
        """Test that database tables have expected columns."""
        inspector = inspect(test_engine)
        
        # Test raw_feedback table
        raw_feedback_columns = [col['name'] for col in inspector.get_columns('raw_feedback')]
        expected_columns = ['id', 'source_type', 'source_id', 'url', 'title', 'content', 'author', 'timestamp', 'raw_metadata']
        for col in expected_columns:
            assert col in raw_feedback_columns, f"Column {col} not found in raw_feedback table"
        
        # Test processed_documents table
        processed_docs_columns = [col['name'] for col in inspector.get_columns('processed_documents')]
        expected_columns = ['id', 'raw_feedback_id', 'title', 'body', 'author', 'timestamp', 'url', 'feedback_type', 'severity_score', 'component', 'confidence_score']
        for col in expected_columns:
            assert col in processed_docs_columns, f"Column {col} not found in processed_documents table"
    
    def test_database_foreign_keys(self, test_engine):
        """Test that foreign key relationships are properly defined."""
        inspector = inspect(test_engine)
        
        # Test foreign key from processed_documents to raw_feedback
        fks = inspector.get_foreign_keys('processed_documents')
        raw_feedback_fk = None
        for fk in fks:
            if fk['referred_table'] == 'raw_feedback':
                raw_feedback_fk = fk
                break
        
        assert raw_feedback_fk is not None, "Foreign key from processed_documents to raw_feedback not found"
        assert 'raw_feedback_id' in raw_feedback_fk['constrained_columns']
        assert 'id' in raw_feedback_fk['referred_columns']

class TestDatabaseConstraints:
    """Tests for database constraints."""
    
    def test_database_constraints_work(self, test_session):
        """Test that database constraints work properly."""
        from database.models import RawFeedback, ProcessedDocument, SourceType
        from datetime import datetime
        
        # Test foreign key constraints
        raw_feedback = RawFeedback(
            source_type=SourceType.GITHUB_ISSUE,
            source_id="12345",
            url="https://github.com/user/repo/issues/123",
            content="Test content",
            timestamp=datetime.utcnow()
        )
        test_session.add(raw_feedback)
        test_session.commit()
        
        # Test that we can create a ProcessedDocument with valid foreign key
        processed_doc = ProcessedDocument(
            raw_feedback_id=raw_feedback.id,
            title="Test Document",
            body="Test body",
            author="testuser",
            timestamp=datetime.utcnow(),
            url="https://github.com/user/repo/issues/123"
        )
        test_session.add(processed_doc)
        test_session.commit()
        
        assert processed_doc.id is not None
        assert processed_doc.raw_feedback_id == raw_feedback.id
        assert processed_doc.raw_feedback == raw_feedback
    
    def test_database_unique_constraints(self, test_session):
        """Test that unique constraints work properly."""
        from database.models import RawFeedback, SourceType
        from datetime import datetime
        
        # Create first RawFeedback
        feedback1 = RawFeedback(
            source_type=SourceType.GITHUB_ISSUE,
            source_id="12345",
            url="https://github.com/user/repo/issues/123",
            content="Test content",
            timestamp=datetime.utcnow()
        )
        test_session.add(feedback1)
        test_session.commit()
        
        # Try to create second RawFeedback with same source_id and source_type
        feedback2 = RawFeedback(
            source_type=SourceType.GITHUB_ISSUE,
            source_id="12345",  # Same source_id
            url="https://github.com/user/repo/issues/124",
            content="Test content 2",
            timestamp=datetime.utcnow()
        )
        test_session.add(feedback2)
        
        # This should raise an IntegrityError due to unique constraint
        with pytest.raises(Exception):  # Could be IntegrityError or similar
            test_session.commit()

class TestDatabaseHealth:
    """Tests for database health checks."""
    
    def test_database_connection_works(self, test_engine):
        """Test that database connection works."""
        try:
            with test_engine.connect() as conn:
                result = conn.execute("SELECT 1")
                assert result.fetchone()[0] == 1
        except Exception as e:
            pytest.fail(f"Database connection failed: {e}")
    
    def test_database_can_execute_queries(self, test_session):
        """Test that database can execute queries."""
        from database.models import RawFeedback, SourceType
        from datetime import datetime
        
        # Create a test record
        feedback = RawFeedback(
            source_type=SourceType.GITHUB_ISSUE,
            source_id="12345",
            url="https://github.com/user/repo/issues/123",
            content="Test content",
            timestamp=datetime.utcnow()
        )
        test_session.add(feedback)
        test_session.commit()
        
        # Query the record
        result = test_session.query(RawFeedback).filter_by(source_id="12345").first()
        assert result is not None
        assert result.source_id == "12345"
    
    def test_database_transactions_work(self, test_session):
        """Test that database transactions work properly."""
        from database.models import RawFeedback, SourceType
        from datetime import datetime
        
        # Start transaction
        feedback = RawFeedback(
            source_type=SourceType.GITHUB_ISSUE,
            source_id="12345",
            url="https://github.com/user/repo/issues/123",
            content="Test content",
            timestamp=datetime.utcnow()
        )
        test_session.add(feedback)
        
        # Commit transaction
        test_session.commit()
        
        # Verify record exists
        result = test_session.query(RawFeedback).filter_by(source_id="12345").first()
        assert result is not None
        
        # Test rollback
        feedback2 = RawFeedback(
            source_type=SourceType.GITHUB_ISSUE,
            source_id="67890",
            url="https://github.com/user/repo/issues/456",
            content="Test content 2",
            timestamp=datetime.utcnow()
        )
        test_session.add(feedback2)
        test_session.rollback()
        
        # Verify rollback worked
        result2 = test_session.query(RawFeedback).filter_by(source_id="67890").first()
        assert result2 is None

class TestDatabasePerformance:
    """Tests for database performance."""
    
    def test_database_can_handle_multiple_records(self, test_session):
        """Test that database can handle multiple records."""
        from database.models import RawFeedback, SourceType
        from datetime import datetime
        
        # Create multiple records
        for i in range(10):
            feedback = RawFeedback(
                source_type=SourceType.GITHUB_ISSUE,
                source_id=f"1234{i}",
                url=f"https://github.com/user/repo/issues/{i}",
                content=f"Test content {i}",
                timestamp=datetime.utcnow()
            )
            test_session.add(feedback)
        
        test_session.commit()
        
        # Query all records
        results = test_session.query(RawFeedback).all()
        assert len(results) == 10
        
        # Query specific record
        result = test_session.query(RawFeedback).filter_by(source_id="12340").first()
        assert result is not None
        assert result.content == "Test content 0"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
