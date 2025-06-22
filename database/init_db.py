#!/usr/bin/env python3
"""
Database initialization script
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.connection import db
from database.models import Base
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize database and create tables"""
    try:
        logger.info("Initializing database...")
        
        # Initialize database connection
        db.initialize()
        
        # Test connection
        if not db.test_connection():
            logger.error("Database connection test failed")
            return False
        
        logger.info("Database connection successful")
        
        # Create tables
        db.create_tables()
        logger.info("Database tables created successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    success = init_database()
    if success:
        logger.info("Database initialization completed successfully")
        sys.exit(0)
    else:
        logger.error("Database initialization failed")
        sys.exit(1)