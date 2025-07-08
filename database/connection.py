"""
Database connection and session management
"""
from sqlalchemy import create_engine, text, TIMESTAMP, TypeDecorator, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
import logging
from datetime import datetime
import re

from config import settings

logger = logging.getLogger(__name__)

# Python 3.6 compatibility: datetime parsing utility
def parse_iso_datetime(date_string):
    """
    Python 3.6 compatible ISO format datetime parsing
    Implements datetime.fromisoformat() functionality for Python 3.6
    """
    if hasattr(datetime, 'fromisoformat'):
        # Python 3.7+ has native support
        try:
            return datetime.fromisoformat(date_string)
        except ValueError:
            # Fall back to manual parsing
            pass
    
    # Python 3.6 compatibility implementation
    # Handle various ISO 8601 formats
    # Format: YYYY-MM-DDTHH:MM:SS[.ffffff]
    pattern = r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?$'
    match = re.match(pattern, date_string.strip())
    
    if match:
        year, month, day, hour, minute, second, microsecond_str = match.groups()
        
        # Parse components
        year = int(year)
        month = int(month)
        day = int(day)
        hour = int(hour)
        minute = int(minute)
        second = int(second)
        
        # Handle microseconds
        microsecond = 0
        if microsecond_str:
            # Pad or truncate to 6 digits (microseconds)
            microsecond_str = microsecond_str.ljust(6, '0')[:6]
            microsecond = int(microsecond_str)
        
        return datetime(year, month, day, hour, minute, second, microsecond)
    
    # Try alternative parsing methods for edge cases
    try:
        # Try strptime with different formats
        for fmt in ['%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
            try:
                return datetime.strptime(date_string.strip(), fmt)
            except ValueError:
                continue
    except:
        pass
    
    # Final fallback - return None instead of raising exception
    logger.warning(f"Could not parse datetime string: {date_string}")
    return None


class CompatibleTimestamp(TypeDecorator):
    """
    A timestamp type that's compatible with Python 3.6
    Handles datetime parsing without relying on fromisoformat()
    """
    impl = DateTime
    cache_ok = True
    
    def process_result_value(self, value, dialect):
        """Process value when reading from database"""
        if value is None:
            return value
        
        if isinstance(value, str):
            # Parse ISO format string using our compatibility function
            parsed = parse_iso_datetime(value)
            if parsed is not None:
                return parsed
            else:
                # If parsing fails, return as-is and let SQLAlchemy handle it
                logger.warning(f"Failed to parse datetime string: {value}")
                return value
        
        return value
    
    def process_bind_param(self, value, dialect):
        """Process value when writing to database"""
        if value is None:
            return value
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            # Parse string to datetime
            parsed = parse_iso_datetime(value)
            if parsed is not None:
                return parsed
            else:
                logger.warning(f"Failed to parse datetime string for binding: {value}")
                return value
        
        return value


# Create SQLAlchemy base
Base = declarative_base()

class Database:
    """Database connection manager"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def initialize(self):
        """Initialize database connection"""
        if self._initialized:
            return
            
        try:
            # Create engine with optimized connection pool settings
            # SQLite doesn't support pool_size, max_overflow, pool_timeout
            if settings.database_url.startswith('sqlite'):
                self.engine = create_engine(
                    settings.database_url,
                    echo=settings.debug,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                    echo_pool=False  # 生产环境关闭池日志
                )
            else:
                # MySQL and other databases support full pool configuration
                self.engine = create_engine(
                    settings.database_url,
                    echo=settings.debug,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                    pool_size=20,  # 增加连接池大小
                    max_overflow=30,  # 允许更多溢出连接
                    pool_timeout=30,  # 连接超时时间
                    echo_pool=False  # 生产环境关闭池日志
                )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            self._initialized = True
            logger.info("Database connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def create_tables(self):
        """Create all database tables"""
        if not self._initialized:
            self.initialize()
            
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def test_connection(self):
        """Test database connection"""
        if not self._initialized:
            self.initialize()
            
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                return result.fetchone() is not None
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with automatic cleanup"""
        if not self._initialized:
            self.initialize()
            
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


# Global database instance
db = Database()


def get_db_session() -> Generator[Session, None, None]:
    """Dependency for getting database session"""
    with db.get_session() as session:
        yield session