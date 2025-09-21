#!/usr/bin/env python3
"""
Database setup script for Product Feedback Miner.

This script initializes the database, creates tables, enables extensions,
and sets up initial configuration.
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import db_manager, create_tables, enable_pgvector, create_vector_indexes
from database.models import Base, SystemConfig
from config.settings import config
from utils.logging import setup_logging
import logging

logger = logging.getLogger(__name__)

async def setup_database(force_recreate: bool = False):
    """
    Set up the database with all required tables and extensions.
    
    Args:
        force_recreate: If True, drop existing tables before creating new ones
    """
    try:
        logger.info("Starting database setup...")
        
        # Test database connection
        if not db_manager.health_check():
            logger.error("Cannot connect to database. Please check your configuration.")
            return False
        
        logger.info("Database connection successful")
        
        # Drop tables if force recreate
        if force_recreate:
            logger.warning("Force recreate enabled - dropping existing tables")
            db_manager.drop_tables()
        
        # Create all tables
        logger.info("Creating database tables...")
        create_tables()
        logger.info("Database tables created successfully")
        
        # Enable pgvector extension
        logger.info("Enabling pgvector extension...")
        enable_pgvector()
        logger.info("pgvector extension enabled")
        
        # Create vector indexes
        logger.info("Creating vector indexes...")
        create_vector_indexes()
        logger.info("Vector indexes created successfully")
        
        # Insert initial system configuration
        await insert_initial_config()
        
        logger.info("Database setup completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return False

async def insert_initial_config():
    """Insert initial system configuration."""
    try:
        with db_manager.get_session() as session:
            # Check if config already exists
            existing_config = session.query(SystemConfig).filter(
                SystemConfig.config_key == "initial_setup"
            ).first()
            
            if existing_config:
                logger.info("Initial configuration already exists")
                return
            
            # Insert initial configuration
            initial_configs = [
                SystemConfig(
                    config_key="initial_setup",
                    config_value={"completed": True, "version": "1.0.0"},
                    description="Initial database setup completion marker"
                ),
                SystemConfig(
                    config_key="prioritizer_weights",
                    config_value={
                        "severity": 0.35,
                        "reach": 0.25,
                        "recency": 0.20,
                        "persona_weight": 0.20
                    },
                    description="Default prioritization weights"
                ),
                SystemConfig(
                    config_key="revenue_critical_components",
                    config_value=[
                        "login", "authentication", "checkout", "payment",
                        "api", "core", "database", "security"
                    ],
                    description="Components considered revenue-critical"
                ),
                SystemConfig(
                    config_key="clustering_threshold",
                    config_value=0.8,
                    description="Similarity threshold for clustering"
                ),
                SystemConfig(
                    config_key="actioner_priority_threshold",
                    config_value=0.7,
                    description="Minimum priority score to create tickets"
                )
            ]
            
            for config_item in initial_configs:
                session.add(config_item)
            
            session.commit()
            logger.info("Initial configuration inserted")
            
    except Exception as e:
        logger.error(f"Failed to insert initial configuration: {e}")
        raise

async def verify_setup():
    """Verify that the database setup was successful."""
    try:
        logger.info("Verifying database setup...")
        
        # Check database health
        if not db_manager.health_check():
            logger.error("Database health check failed")
            return False
        
        # Check if tables exist
        with db_manager.get_session() as session:
            # Test a simple query on each major table
            tables_to_check = [
                "raw_feedback",
                "processed_documents", 
                "clusters",
                "cluster_memberships",
                "prioritization_scores",
                "tickets",
                "feedback_loop_data",
                "agent_executions",
                "system_config",
                "digest_reports"
            ]
            
            for table in tables_to_check:
                result = session.execute(f"SELECT COUNT(*) FROM {table}")
                count = result.scalar()
                logger.info(f"Table {table}: {count} records")
        
        # Check pgvector extension
        with db_manager.get_session() as session:
            result = session.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            if not result.fetchone():
                logger.error("pgvector extension not found")
                return False
        
        logger.info("Database setup verification completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database setup verification failed: {e}")
        return False

async def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(description="Setup Product Feedback Miner database")
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Drop existing tables before creating new ones"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing setup without making changes"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level=args.log_level)
    
    if args.verify_only:
        success = await verify_setup()
    else:
        success = await setup_database(force_recreate=args.force_recreate)
        if success:
            success = await verify_setup()
    
    if success:
        logger.info("Database setup completed successfully!")
        sys.exit(0)
    else:
        logger.error("Database setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
