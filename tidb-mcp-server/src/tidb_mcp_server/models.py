"""
Data models for TiDB MCP Server.

This module contains all data models used for representing database schema information,
query results, and other data structures used in the MCP server.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class DatabaseInfo:
    """Information about a database."""
    
    name: str
    charset: str
    collation: str
    accessible: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP response formatting."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseInfo':
        """Create instance from dictionary."""
        return cls(**data)


@dataclass
class TableInfo:
    """Information about a database table."""
    
    name: str
    type: str  # 'BASE TABLE', 'VIEW', etc.
    engine: str
    rows: Optional[int] = None
    size_mb: Optional[float] = None
    comment: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP response formatting."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TableInfo':
        """Create instance from dictionary."""
        return cls(**data)


@dataclass
class ColumnInfo:
    """Information about a table column."""
    
    name: str
    data_type: str
    is_nullable: bool
    default_value: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    comment: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP response formatting."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ColumnInfo':
        """Create instance from dictionary."""
        return cls(**data)


@dataclass
class IndexInfo:
    """Information about a table index."""
    
    name: str
    columns: List[str]
    is_unique: bool
    index_type: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP response formatting."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IndexInfo':
        """Create instance from dictionary."""
        return cls(**data)


@dataclass
class TableSchema:
    """Complete schema information for a table."""
    
    database: str
    table: str
    columns: List[ColumnInfo]
    indexes: List[IndexInfo]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, str]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP response formatting."""
        return {
            'database': self.database,
            'table': self.table,
            'columns': [col.to_dict() for col in self.columns],
            'indexes': [idx.to_dict() for idx in self.indexes],
            'primary_keys': self.primary_keys,
            'foreign_keys': self.foreign_keys
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TableSchema':
        """Create instance from dictionary."""
        return cls(
            database=data['database'],
            table=data['table'],
            columns=[ColumnInfo.from_dict(col) for col in data['columns']],
            indexes=[IndexInfo.from_dict(idx) for idx in data['indexes']],
            primary_keys=data['primary_keys'],
            foreign_keys=data['foreign_keys']
        )


@dataclass
class QueryResult:
    """Result of a SQL query execution."""
    
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    truncated: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP response formatting."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueryResult':
        """Create instance from dictionary."""
        return cls(**data)
    
    def is_successful(self) -> bool:
        """Check if the query execution was successful."""
        return self.error is None
    
    def get_formatted_execution_time(self) -> str:
        """Get formatted execution time string."""
        if self.execution_time_ms < 1000:
            return f"{self.execution_time_ms:.2f}ms"
        else:
            return f"{self.execution_time_ms / 1000:.2f}s"


@dataclass
class SampleDataResult:
    """Result of sample data retrieval from a table."""
    
    database: str
    table: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    total_table_rows: Optional[int]
    execution_time_ms: float
    sampling_method: str  # 'TABLESAMPLE', 'LIMIT_ORDER_BY', 'LIMIT_RANDOM'
    masked_columns: List[str] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        """Initialize masked_columns if None."""
        if self.masked_columns is None:
            self.masked_columns = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MCP response formatting."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SampleDataResult':
        """Create instance from dictionary."""
        return cls(**data)
    
    def is_successful(self) -> bool:
        """Check if the sample data retrieval was successful."""
        return self.error is None
    
    def get_formatted_execution_time(self) -> str:
        """Get formatted execution time string."""
        if self.execution_time_ms < 1000:
            return f"{self.execution_time_ms:.2f}ms"
        else:
            return f"{self.execution_time_ms / 1000:.2f}s"


# Type aliases for better code readability
DatabaseList = List[DatabaseInfo]
TableList = List[TableInfo]
ColumnList = List[ColumnInfo]
IndexList = List[IndexInfo]