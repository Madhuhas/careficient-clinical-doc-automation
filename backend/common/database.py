"""
Database utilities and connection management.
Supports multiple database backends with a unified interface.
"""

from typing import Dict, List, Any, Optional, Type, TypeVar, Generic
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
import logging

try:
    import psycopg2
    from psycopg2.pool import SimpleConnectionPool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    import sqlite3
    SQLITE3_AVAILABLE = True
except ImportError:
    SQLITE3_AVAILABLE = False

try:
    import pymongo
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False


logger = logging.getLogger(__name__)

T = TypeVar('T')


class DatabaseType(str, Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"


class DatabaseConnection(ABC):
    """Abstract base class for database connections."""
    
    @abstractmethod
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """Execute a query."""
        pass
    
    @abstractmethod
    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict]:
        """Fetch a single result."""
        pass
    
    @abstractmethod
    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        """Fetch all results."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close connection."""
        pass


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL database connection."""
    
    def __init__(self, dsn: str):
        """
        Initialize PostgreSQL connection.
        
        Args:
            dsn: PostgreSQL connection string
        """
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError("psycopg2 not installed")
        
        try:
            self.conn = psycopg2.connect(dsn)
            self.cursor = self.conn.cursor()
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """Execute a query."""
        try:
            self.cursor.execute(query, params or ())
            self.conn.commit()
            return self.cursor
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Query execution failed: {e}")
            raise
    
    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict]:
        """Fetch a single result."""
        self.cursor.execute(query, params or ())
        row = self.cursor.fetchone()
        if row:
            columns = [desc[0] for desc in self.cursor.description]
            return dict(zip(columns, row))
        return None
    
    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        """Fetch all results."""
        self.cursor.execute(query, params or ())
        rows = self.cursor.fetchall()
        columns = [desc[0] for desc in self.cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def close(self) -> None:
        """Close connection."""
        self.cursor.close()
        self.conn.close()
        logger.info("Closed PostgreSQL connection")


class SQLiteConnection(DatabaseConnection):
    """SQLite database connection."""
    
    def __init__(self, db_path: str):
        """
        Initialize SQLite connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        if not SQLITE3_AVAILABLE:
            raise RuntimeError("sqlite3 not available")
        
        try:
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"Connected to SQLite: {db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            raise
    
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """Execute a query."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params or ())
            self.conn.commit()
            return cursor
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Query execution failed: {e}")
            raise
    
    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict]:
        """Fetch a single result."""
        cursor = self.conn.cursor()
        cursor.execute(query, params or ())
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        """Fetch all results."""
        cursor = self.conn.cursor()
        cursor.execute(query, params or ())
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def close(self) -> None:
        """Close connection."""
        self.conn.close()
        logger.info("Closed SQLite connection")


class MongoDBConnection(DatabaseConnection):
    """MongoDB database connection."""
    
    def __init__(self, connection_string: str, database: str):
        """
        Initialize MongoDB connection.
        
        Args:
            connection_string: MongoDB connection string
            database: Database name
        """
        if not PYMONGO_AVAILABLE:
            raise RuntimeError("pymongo not installed")
        
        try:
            client = pymongo.MongoClient(connection_string)
            self.db = client[database]
            logger.info(f"Connected to MongoDB: {database}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """Not implemented for MongoDB."""
        raise NotImplementedError("Use collection methods instead")
    
    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[Dict]:
        """Not implemented for MongoDB."""
        raise NotImplementedError("Use collection methods instead")
    
    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[Dict]:
        """Not implemented for MongoDB."""
        raise NotImplementedError("Use collection methods instead")
    
    def close(self) -> None:
        """Close connection."""
        self.db.client.close()
        logger.info("Closed MongoDB connection")


class DatabaseFactory:
    """Factory for creating database connections."""
    
    @staticmethod
    def create_connection(
        db_type: DatabaseType,
        connection_string: str,
        **kwargs
    ) -> DatabaseConnection:
        """
        Create a database connection.
        
        Args:
            db_type: Type of database
            connection_string: Connection string
            **kwargs: Additional arguments
        
        Returns:
            Database connection
        """
        if db_type == DatabaseType.POSTGRESQL:
            return PostgreSQLConnection(connection_string)
        elif db_type == DatabaseType.SQLITE:
            return SQLiteConnection(connection_string)
        elif db_type == DatabaseType.MONGODB:
            database = kwargs.get("database", "careficient")
            return MongoDBConnection(connection_string, database)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")


class QueryBuilder:
    """Simple SQL query builder."""
    
    def __init__(self):
        self.select_clause = []
        self.from_clause = None
        self.where_clauses = []
        self.order_by_clause = None
        self.limit_value = None
        self.offset_value = None
    
    def select(self, *columns: str) -> "QueryBuilder":
        """Add SELECT clause."""
        self.select_clause = list(columns) if columns else ["*"]
        return self
    
    def from_table(self, table: str) -> "QueryBuilder":
        """Add FROM clause."""
        self.from_clause = table
        return self
    
    def where(self, condition: str, *params) -> "QueryBuilder":
        """Add WHERE clause."""
        self.where_clauses.append((condition, params))
        return self
    
    def order_by(self, column: str, direction: str = "ASC") -> "QueryBuilder":
        """Add ORDER BY clause."""
        self.order_by_clause = f"{column} {direction}"
        return self
    
    def limit(self, limit: int) -> "QueryBuilder":
        """Add LIMIT clause."""
        self.limit_value = limit
        return self
    
    def offset(self, offset: int) -> "QueryBuilder":
        """Add OFFSET clause."""
        self.offset_value = offset
        return self
    
    def build(self) -> tuple[str, list]:
        """Build query and return (query_string, params)."""
        if not self.from_clause:
            raise ValueError("FROM clause required")
        
        query = f"SELECT {', '.join(self.select_clause)} FROM {self.from_clause}"
        params = []
        
        if self.where_clauses:
            where_parts = []
            for condition, cond_params in self.where_clauses:
                where_parts.append(condition)
                params.extend(cond_params)
            query += " WHERE " + " AND ".join(where_parts)
        
        if self.order_by_clause:
            query += f" ORDER BY {self.order_by_clause}"
        
        if self.limit_value is not None:
            query += f" LIMIT {self.limit_value}"
        
        if self.offset_value is not None:
            query += f" OFFSET {self.offset_value}"
        
        return query, params


# Database schema for reference
DATABASE_SCHEMAS = {
    "documents": """
        CREATE TABLE IF NOT EXISTS documents (
            id UUID PRIMARY KEY,
            filename VARCHAR(255),
            document_type VARCHAR(50),
            file_type VARCHAR(20),
            source VARCHAR(20),
            patient_id VARCHAR(50),
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            metadata JSONB,
            INDEX idx_patient_id (patient_id),
            INDEX idx_created_at (created_at)
        )
    """,
    "extractions": """
        CREATE TABLE IF NOT EXISTS extractions (
            id UUID PRIMARY KEY,
            document_id UUID,
            extraction_type VARCHAR(50),
            vitals JSONB,
            medications JSONB,
            symptoms JSONB,
            assessments JSONB,
            chief_complaint TEXT,
            plan TEXT,
            confidence FLOAT,
            created_at TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(id),
            INDEX idx_document_id (document_id)
        )
    """,
    "oasis_prefills": """
        CREATE TABLE IF NOT EXISTS oasis_prefills (
            id UUID PRIMARY KEY,
            extraction_id UUID,
            form_version VARCHAR(10),
            form_data JSONB,
            validation_status VARCHAR(20),
            created_at TIMESTAMP,
            FOREIGN KEY (extraction_id) REFERENCES extractions(id),
            INDEX idx_extraction_id (extraction_id)
        )
    """
}
