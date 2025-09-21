"""
Database migrations for Product Feedback Miner.

This module handles database schema migrations and versioning.
"""

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext
from sqlalchemy import create_engine
import os
from pathlib import Path

from config.settings import config
from database.models import Base

def get_alembic_config():
    """Get Alembic configuration."""
    project_root = Path(__file__).parent.parent.parent
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    return alembic_cfg

def create_migration(message: str):
    """Create a new migration."""
    alembic_cfg = get_alembic_config()
    command.revision(alembic_cfg, message=message, autogenerate=True)

def upgrade_database(revision: str = "head"):
    """Upgrade database to specified revision."""
    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, revision)

def downgrade_database(revision: str):
    """Downgrade database to specified revision."""
    alembic_cfg = get_alembic_config()
    command.downgrade(alembic_cfg, revision)

def get_current_revision():
    """Get current database revision."""
    alembic_cfg = get_alembic_config()
    script = ScriptDirectory.from_config(alembic_cfg)
    
    def get_current_rev(rev, context):
        return script.get_current_head()
    
    with EnvironmentContext(
        alembic_cfg,
        script,
        fn=get_current_rev,
        as_sql=False,
        starting_rev=None,
        destination_rev=None
    ):
        return get_current_rev(None, None)
