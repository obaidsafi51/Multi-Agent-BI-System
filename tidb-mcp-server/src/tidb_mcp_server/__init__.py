"""TiDB MCP Server package."""

__version__ = "0.1.0"

# Export main data models for easy importing
from .models import (
    DatabaseInfo,
    TableInfo,
    ColumnInfo,
    IndexInfo,
    TableSchema,
    QueryResult,
    DatabaseList,
    TableList,
    ColumnList,
    IndexList,
)

__all__ = [
    "DatabaseInfo",
    "TableInfo", 
    "ColumnInfo",
    "IndexInfo",
    "TableSchema",
    "QueryResult",
    "DatabaseList",
    "TableList",
    "ColumnList",
    "IndexList",
]