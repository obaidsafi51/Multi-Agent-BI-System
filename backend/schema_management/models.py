"""
Data models for MCP schema management.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class DatabaseInfo:
    """Information about a database."""
    name: str
    charset: str
    collation: str
    accessible: bool
    table_count: Optional[int] = None


@dataclass
class IndexInfo:
    """Information about a database index."""
    name: str
    columns: List[str]
    is_unique: bool
    is_primary: bool
    index_type: str
    comment: Optional[str] = None


@dataclass
class ForeignKeyInfo:
    """Information about a foreign key constraint."""
    name: str
    column: str
    referenced_table: str
    referenced_column: str
    on_delete: str
    on_update: str


@dataclass
class ConstraintInfo:
    """Information about table constraints."""
    name: str
    constraint_type: str
    columns: List[str]
    definition: str
    is_deferrable: bool = False


@dataclass
class ColumnInfo:
    """Information about a table column."""
    name: str
    data_type: str
    is_nullable: bool
    default_value: Optional[str]
    is_primary_key: bool
    is_foreign_key: bool
    comment: Optional[str] = None
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    is_auto_increment: bool = False
    character_set: Optional[str] = None
    collation: Optional[str] = None


@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    type: str
    engine: str
    rows: int
    size_mb: float
    comment: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class TableSchema:
    """Complete schema information for a table."""
    database: str
    table: str
    columns: List[ColumnInfo]
    indexes: List[IndexInfo]
    primary_keys: List[str]
    foreign_keys: List[ForeignKeyInfo]
    constraints: List[ConstraintInfo]
    table_info: Optional[TableInfo] = None


@dataclass
class ValidationError:
    """Validation error information."""
    field: str
    message: str
    severity: ValidationSeverity
    error_code: Optional[str] = None
    suggested_value: Optional[Any] = None


@dataclass
class ValidationWarning:
    """Validation warning information."""
    field: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of data validation against schema."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationWarning]
    validated_fields: List[str]
    validation_time_ms: int = 0


@dataclass
class SchemaDiscoveryResult:
    """Result of schema discovery operation."""
    databases: List[DatabaseInfo]
    discovery_time_ms: int
    cached: bool = False
    error: Optional[str] = None


@dataclass
class DetailedTableSchema:
    """Detailed table schema with additional metadata."""
    table_schema: TableSchema
    sample_data: Optional[List[Dict[str, Any]]] = None
    statistics: Optional[Dict[str, Any]] = None
    relationships: Optional[List[Dict[str, Any]]] = None
    discovery_time_ms: int = 0


@dataclass
class QueryValidationResult:
    """Result of SQL query validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    affected_tables: List[str]
    estimated_rows: Optional[int] = None
    execution_plan: Optional[Dict[str, Any]] = None


@dataclass
class CompatibilityResult:
    """Result of schema compatibility check."""
    is_compatible: bool
    missing_tables: List[str]
    missing_columns: List[str]
    type_mismatches: List[Dict[str, Any]]
    constraint_differences: List[Dict[str, Any]]
    recommendations: List[str]


@dataclass
class CacheStats:
    """Statistics about schema cache performance."""
    total_entries: int
    hit_rate: float
    miss_rate: float
    eviction_count: int
    memory_usage_mb: float
    oldest_entry_age_seconds: int
    newest_entry_age_seconds: int


@dataclass
class SemanticMapping:
    """Represents a semantic mapping between a business term and schema element."""
    business_term: str
    schema_element_type: str  # 'table', 'column', 'index'
    schema_element_path: str  # e.g., 'database.table.column'
    confidence_score: float
    similarity_type: str  # 'semantic', 'fuzzy', 'exact', 'learned'
    context_match: bool
    metadata: Dict[str, Any]
    created_at: datetime


@dataclass
class BusinessTerm:
    """Represents a business term with its variants and context."""
    primary_term: str
    synonyms: List[str]
    category: str  # e.g., 'financial', 'operational', 'customer'
    description: Optional[str]
    context_keywords: List[str]
    usage_frequency: int = 0


@dataclass
class SchemaElement:
    """Enhanced schema element with semantic metadata."""
    element_type: str  # 'table', 'column', 'index'
    full_path: str
    name: str
    description: Optional[str]
    semantic_tags: List[str]
    business_concepts: List[str]
    data_type: Optional[str]
    sample_values: Optional[List[str]]
    usage_patterns: Dict[str, Any]


@dataclass
class QueryIntent:
    """Represents the intent extracted from a natural language query."""
    metric_type: str
    filters: Dict[str, Any]
    time_period: Optional[str]
    aggregation_type: str  # 'sum', 'count', 'avg', 'max', 'min'
    group_by: List[str]
    order_by: Optional[str]
    limit: Optional[int]
    confidence: float
    parsed_entities: Dict[str, Any]


@dataclass
class QueryContext:
    """Context information for query building."""
    user_id: str
    session_id: str
    query_history: List[str]
    available_schemas: List[str]
    user_preferences: Dict[str, Any]
    business_context: Optional[str]


@dataclass
class QueryResult:
    """Result of intelligent query building."""
    sql: str
    parameters: Dict[str, Any]
    estimated_rows: Optional[int]
    optimization_hints: List[str]
    alternative_queries: List[str]
    confidence_score: float
    processing_time_ms: int
    used_mappings: List[SemanticMapping]


@dataclass
class SchemaInfo:
    """Complete schema information containing databases and tables."""
    databases: List[DatabaseInfo]
    tables: List[TableInfo]
    version: str
    discovery_timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


# Serialization and deserialization utilities
class SchemaModelEncoder(json.JSONEncoder):
    """Custom JSON encoder for schema models."""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return asdict(obj)
        return super().default(obj)


def serialize_schema_model(model: Any) -> str:
    """
    Serialize a schema model to JSON string.
    
    Args:
        model: Schema model instance
        
    Returns:
        JSON string representation
    """
    return json.dumps(model, cls=SchemaModelEncoder, indent=2)


def deserialize_database_info(data: Dict[str, Any]) -> DatabaseInfo:
    """
    Deserialize DatabaseInfo from dictionary.
    
    Args:
        data: Dictionary containing database info
        
    Returns:
        DatabaseInfo instance
    """
    return DatabaseInfo(
        name=data['name'],
        charset=data['charset'],
        collation=data['collation'],
        accessible=data['accessible'],
        table_count=data.get('table_count')
    )


def deserialize_table_info(data: Dict[str, Any]) -> TableInfo:
    """
    Deserialize TableInfo from dictionary.
    
    Args:
        data: Dictionary containing table info
        
    Returns:
        TableInfo instance
    """
    created_at = None
    updated_at = None
    
    if data.get('created_at'):
        created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
    if data.get('updated_at'):
        updated_at = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))
    
    return TableInfo(
        name=data['name'],
        type=data['type'],
        engine=data['engine'],
        rows=data['rows'],
        size_mb=data['size_mb'],
        comment=data.get('comment'),
        created_at=created_at,
        updated_at=updated_at
    )


def deserialize_column_info(data: Dict[str, Any]) -> ColumnInfo:
    """
    Deserialize ColumnInfo from dictionary.
    
    Args:
        data: Dictionary containing column info
        
    Returns:
        ColumnInfo instance
    """
    return ColumnInfo(
        name=data['name'],
        data_type=data['data_type'],
        is_nullable=data['is_nullable'],
        default_value=data.get('default_value'),
        is_primary_key=data.get('is_primary_key', False),
        is_foreign_key=data.get('is_foreign_key', False),
        comment=data.get('comment'),
        max_length=data.get('max_length'),
        precision=data.get('precision'),
        scale=data.get('scale'),
        is_auto_increment=data.get('is_auto_increment', False),
        character_set=data.get('character_set'),
        collation=data.get('collation')
    )


def deserialize_table_schema(data: Dict[str, Any]) -> TableSchema:
    """
    Deserialize TableSchema from dictionary.
    
    Args:
        data: Dictionary containing table schema
        
    Returns:
        TableSchema instance
    """
    columns = [deserialize_column_info(col) for col in data.get('columns', [])]
    
    indexes = []
    for idx_data in data.get('indexes', []):
        indexes.append(IndexInfo(
            name=idx_data['name'],
            columns=idx_data['columns'],
            is_unique=idx_data.get('is_unique', False),
            is_primary=idx_data.get('is_primary', False),
            index_type=idx_data.get('index_type', 'BTREE'),
            comment=idx_data.get('comment')
        ))
    
    foreign_keys = []
    for fk_data in data.get('foreign_keys', []):
        foreign_keys.append(ForeignKeyInfo(
            name=fk_data['name'],
            column=fk_data['column'],
            referenced_table=fk_data['referenced_table'],
            referenced_column=fk_data['referenced_column'],
            on_delete=fk_data.get('on_delete', 'RESTRICT'),
            on_update=fk_data.get('on_update', 'RESTRICT')
        ))
    
    constraints = []
    for const_data in data.get('constraints', []):
        constraints.append(ConstraintInfo(
            name=const_data['name'],
            constraint_type=const_data['constraint_type'],
            columns=const_data['columns'],
            definition=const_data['definition'],
            is_deferrable=const_data.get('is_deferrable', False)
        ))
    
    table_info = None
    if data.get('table_info'):
        table_info = deserialize_table_info(data['table_info'])
    
    return TableSchema(
        database=data['database'],
        table=data['table'],
        columns=columns,
        indexes=indexes,
        primary_keys=data.get('primary_keys', []),
        foreign_keys=foreign_keys,
        constraints=constraints,
        table_info=table_info
    )