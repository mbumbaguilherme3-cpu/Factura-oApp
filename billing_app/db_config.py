"""
Database Configuration and Initialization
Provides SQLAlchemy db instance for ORM models
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import logging

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base with updated config"""
    pass


# SQLAlchemy database instance
db = SQLAlchemy(model_class=Base)


def init_db():
    """Initialize database tables"""
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise
