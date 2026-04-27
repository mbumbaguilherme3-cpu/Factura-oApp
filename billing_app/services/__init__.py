"""
Base service class with common operations.
"""

import logging
from typing import Any, Optional
from abc import ABC, abstractmethod

from billing_app.database import get_connection
from billing_app.exceptions import DatabaseError, ResourceNotFoundError


logger = logging.getLogger(__name__)


class BaseService(ABC):
    """Abstract base service class with common patterns."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_connection(self):
        """Get database connection."""
        try:
            return get_connection()
        except Exception as e:
            self.logger.error(f"Failed to get database connection: {e}")
            raise DatabaseError("Database connection failed", original_error=e)
    
    def execute_query(self, connection: Any, query: str, params: tuple = (), fetch_one: bool = False) -> Any:
        """Execute query with error handling."""
        try:
            if hasattr(connection, 'cursor'):  # PostgreSQL
                cursor = connection.cursor()
                cursor.execute(query, params)
                result = cursor.fetchone() if fetch_one else cursor.fetchall()
                cursor.close()
                return result
            else:  # SQLite
                cursor = connection.execute(query, params)
                result = cursor.fetchone() if fetch_one else cursor.fetchall()
                return result
        except Exception as e:
            self.logger.error(f"Query execution failed: {e}", extra={"query": query})
            raise DatabaseError(f"Query execution failed: {str(e)}", original_error=e)
    
    def execute_insert(self, connection: Any, query: str, params: tuple = ()) -> int:
        """Execute insert and return last ID."""
        try:
            if hasattr(connection, 'cursor'):  # PostgreSQL
                cursor = connection.cursor()
                cursor.execute(query, params)
                # For PostgreSQL with RETURNING
                result = cursor.fetchone()
                connection.commit()
                cursor.close()
                return result[0] if result else None
            else:  # SQLite
                cursor = connection.execute(query, params)
                connection.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Insert failed: {e}")
            raise DatabaseError(f"Insert failed: {str(e)}", original_error=e)
    
    def execute_update(self, connection: Any, query: str, params: tuple = ()) -> int:
        """Execute update and return affected rows."""
        try:
            if hasattr(connection, 'cursor'):  # PostgreSQL
                cursor = connection.cursor()
                cursor.execute(query, params)
                affected = cursor.rowcount
                connection.commit()
                cursor.close()
                return affected
            else:  # SQLite
                cursor = connection.execute(query, params)
                connection.commit()
                return cursor.rowcount
        except Exception as e:
            self.logger.error(f"Update failed: {e}")
            raise DatabaseError(f"Update failed: {str(e)}", original_error=e)
    
    def execute_delete(self, connection: Any, query: str, params: tuple = ()) -> int:
        """Execute delete and return affected rows."""
        return self.execute_update(connection, query, params)
    
    def get_by_id(self, connection: Any, table_name: str, id_value: int, id_column: str = "id") -> Optional[dict]:
        """Generic get by ID method."""
        query = f"SELECT * FROM {table_name} WHERE {id_column} = %s" if hasattr(connection, 'cursor') else f"SELECT * FROM {table_name} WHERE {id_column} = ?"
        params = (id_value,)
        
        row = self.execute_query(connection, query, params, fetch_one=True)
        if not row:
            raise ResourceNotFoundError(table_name.replace('_', ' ').title(), id_value)
        
        return self._row_to_dict(row)
    
    def _row_to_dict(self, row: Any) -> dict:
        """Convert database row to dictionary."""
        if isinstance(row, dict):
            return row
        # Handle both tuples and Row objects
        if hasattr(row, 'keys'):  # Row object (SQLite)
            return dict(zip(row.keys(), row))
        return {}
    
    def log_operation(self, operation: str, details: dict):
        """Log service operation."""
        self.logger.info(
            f"Operation: {operation}",
            extra={**details, "service": self.__class__.__name__}
        )
