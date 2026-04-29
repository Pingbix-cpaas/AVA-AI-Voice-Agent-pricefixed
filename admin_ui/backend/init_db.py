#!/usr/bin/env python3
"""
Database initialization and migration script.
"""

import os
import sys
from alembic.config import Config
from alembic import command
from database import init_db

def init_database():
    """Initialize database and run migrations"""
    print("Initializing database...")

    # Initialize tables (in case migrations haven't been run)
    init_db()

    # Run Alembic migrations
    print("Running database migrations...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    print("Database initialization complete!")

if __name__ == "__main__":
    init_database()