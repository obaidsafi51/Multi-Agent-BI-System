"""
Unit tests for data models.

Tests all data model validation, serialization, and deserialization functionality.
"""

import pytest
from typing import Dict, Any

from tidb_mcp_server.models import (
    DatabaseInfo,
    TableInfo,
    ColumnInfo,
    IndexInfo,
    TableSchema,
    QueryResult
)


class TestDatabaseInfo:
    """Test cases for DatabaseInfo model."""
    
    def test_creation_with_valid_data(self):
        """Test creating DatabaseInfo with valid data."""
        db_info = DatabaseInfo(
            name="test_db",
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            accessible=True
        )
        
        assert db_info.name == "test_db"
        assert db_info.charset == "utf8mb4"
        assert db_info.collation == "utf8mb4_unicode_ci"
        assert db_info.accessible is True
    
    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        db_info = DatabaseInfo(
            name="test_db",
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            accessible=True
        )
        
        result = db_info.to_dict()
        expected = {
            'name': 'test_db',
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'accessible': True
        }
        
        assert result == expected
    
    def test_from_dict_deserialization(self):
        """Test deserialization from dictionary."""
        data = {
            'name': 'test_db',
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'accessible': True
        }
        
        db_info = DatabaseInfo.from_dict(data)
        
        assert db_info.name == "test_db"
        assert db_info.charset == "utf8mb4"
        assert db_info.collation == "utf8mb4_unicode_ci"
        assert db_info.accessible is True
    
    def test_round_trip_serialization(self):
        """Test that serialization and deserialization are consistent."""
        original = DatabaseInfo(
            name="test_db",
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            accessible=False
        )
        
        serialized = original.to_dict()
        deserialized = DatabaseInfo.from_dict(serialized)
        
        assert original == deserialized


class TestTableInfo:
    """Test cases for TableInfo model."""
    
    def test_creation_with_required_fields(self):
        """Test creating TableInfo with only required fields."""
        table_info = TableInfo(
            name="users",
            type="BASE TABLE",
            engine="InnoDB"
        )
        
        assert table_info.name == "users"
        assert table_info.type == "BASE TABLE"
        assert table_info.engine == "InnoDB"
        assert table_info.rows is None
        assert table_info.size_mb is None
        assert table_info.comment == ""
    
    def test_creation_with_all_fields(self):
        """Test creating TableInfo with all fields."""
        table_info = TableInfo(
            name="users",
            type="BASE TABLE",
            engine="InnoDB",
            rows=1000,
            size_mb=15.5,
            comment="User information table"
        )
        
        assert table_info.name == "users"
        assert table_info.type == "BASE TABLE"
        assert table_info.engine == "InnoDB"
        assert table_info.rows == 1000
        assert table_info.size_mb == 15.5
        assert table_info.comment == "User information table"
    
    def test_serialization_with_optional_fields(self):
        """Test serialization with optional fields."""
        table_info = TableInfo(
            name="users",
            type="BASE TABLE",
            engine="InnoDB",
            rows=1000,
            size_mb=15.5,
            comment="User table"
        )
        
        result = table_info.to_dict()
        expected = {
            'name': 'users',
            'type': 'BASE TABLE',
            'engine': 'InnoDB',
            'rows': 1000,
            'size_mb': 15.5,
            'comment': 'User table'
        }
        
        assert result == expected


class TestColumnInfo:
    """Test cases for ColumnInfo model."""
    
    def test_creation_with_required_fields(self):
        """Test creating ColumnInfo with required fields."""
        column_info = ColumnInfo(
            name="id",
            data_type="int",
            is_nullable=False
        )
        
        assert column_info.name == "id"
        assert column_info.data_type == "int"
        assert column_info.is_nullable is False
        assert column_info.default_value is None
        assert column_info.is_primary_key is False
        assert column_info.is_foreign_key is False
        assert column_info.comment == ""
    
    def test_creation_with_all_fields(self):
        """Test creating ColumnInfo with all fields."""
        column_info = ColumnInfo(
            name="user_id",
            data_type="int",
            is_nullable=False,
            default_value="0",
            is_primary_key=True,
            is_foreign_key=False,
            comment="Primary key"
        )
        
        assert column_info.name == "user_id"
        assert column_info.data_type == "int"
        assert column_info.is_nullable is False
        assert column_info.default_value == "0"
        assert column_info.is_primary_key is True
        assert column_info.is_foreign_key is False
        assert column_info.comment == "Primary key"
    
    def test_foreign_key_column(self):
        """Test creating a foreign key column."""
        column_info = ColumnInfo(
            name="department_id",
            data_type="int",
            is_nullable=True,
            is_foreign_key=True,
            comment="References departments.id"
        )
        
        assert column_info.is_foreign_key is True
        assert column_info.is_primary_key is False


class TestIndexInfo:
    """Test cases for IndexInfo model."""
    
    def test_creation_single_column_index(self):
        """Test creating single column index."""
        index_info = IndexInfo(
            name="idx_email",
            columns=["email"],
            is_unique=True,
            index_type="BTREE"
        )
        
        assert index_info.name == "idx_email"
        assert index_info.columns == ["email"]
        assert index_info.is_unique is True
        assert index_info.index_type == "BTREE"
    
    def test_creation_multi_column_index(self):
        """Test creating multi-column index."""
        index_info = IndexInfo(
            name="idx_name_dept",
            columns=["last_name", "first_name", "department_id"],
            is_unique=False,
            index_type="BTREE"
        )
        
        assert index_info.name == "idx_name_dept"
        assert index_info.columns == ["last_name", "first_name", "department_id"]
        assert index_info.is_unique is False
        assert index_info.index_type == "BTREE"
    
    def test_serialization(self):
        """Test index serialization."""
        index_info = IndexInfo(
            name="idx_composite",
            columns=["col1", "col2"],
            is_unique=True,
            index_type="HASH"
        )
        
        result = index_info.to_dict()
        expected = {
            'name': 'idx_composite',
            'columns': ['col1', 'col2'],
            'is_unique': True,
            'index_type': 'HASH'
        }
        
        assert result == expected


class TestTableSchema:
    """Test cases for TableSchema model."""
    
    def test_creation_complete_schema(self):
        """Test creating complete table schema."""
        columns = [
            ColumnInfo("id", "int", False, None, True, False, "Primary key"),
            ColumnInfo("name", "varchar(100)", False, None, False, False, "User name"),
            ColumnInfo("email", "varchar(255)", False, None, False, False, "Email address")
        ]
        
        indexes = [
            IndexInfo("PRIMARY", ["id"], True, "BTREE"),
            IndexInfo("idx_email", ["email"], True, "BTREE")
        ]
        
        schema = TableSchema(
            database="test_db",
            table="users",
            columns=columns,
            indexes=indexes,
            primary_keys=["id"],
            foreign_keys=[]
        )
        
        assert schema.database == "test_db"
        assert schema.table == "users"
        assert len(schema.columns) == 3
        assert len(schema.indexes) == 2
        assert schema.primary_keys == ["id"]
        assert schema.foreign_keys == []
    
    def test_serialization_with_nested_objects(self):
        """Test serialization with nested column and index objects."""
        columns = [
            ColumnInfo("id", "int", False, None, True, False, "Primary key")
        ]
        
        indexes = [
            IndexInfo("PRIMARY", ["id"], True, "BTREE")
        ]
        
        schema = TableSchema(
            database="test_db",
            table="users",
            columns=columns,
            indexes=indexes,
            primary_keys=["id"],
            foreign_keys=[]
        )
        
        result = schema.to_dict()
        
        assert result['database'] == "test_db"
        assert result['table'] == "users"
        assert len(result['columns']) == 1
        assert result['columns'][0]['name'] == "id"
        assert len(result['indexes']) == 1
        assert result['indexes'][0]['name'] == "PRIMARY"
    
    def test_deserialization_with_nested_objects(self):
        """Test deserialization with nested objects."""
        data = {
            'database': 'test_db',
            'table': 'users',
            'columns': [
                {
                    'name': 'id',
                    'data_type': 'int',
                    'is_nullable': False,
                    'default_value': None,
                    'is_primary_key': True,
                    'is_foreign_key': False,
                    'comment': 'Primary key'
                }
            ],
            'indexes': [
                {
                    'name': 'PRIMARY',
                    'columns': ['id'],
                    'is_unique': True,
                    'index_type': 'BTREE'
                }
            ],
            'primary_keys': ['id'],
            'foreign_keys': []
        }
        
        schema = TableSchema.from_dict(data)
        
        assert schema.database == "test_db"
        assert schema.table == "users"
        assert len(schema.columns) == 1
        assert schema.columns[0].name == "id"
        assert len(schema.indexes) == 1
        assert schema.indexes[0].name == "PRIMARY"


class TestQueryResult:
    """Test cases for QueryResult model."""
    
    def test_successful_query_result(self):
        """Test creating successful query result."""
        result = QueryResult(
            columns=["id", "name", "email"],
            rows=[
                {"id": 1, "name": "John", "email": "john@example.com"},
                {"id": 2, "name": "Jane", "email": "jane@example.com"}
            ],
            row_count=2,
            execution_time_ms=150.5
        )
        
        assert result.columns == ["id", "name", "email"]
        assert len(result.rows) == 2
        assert result.row_count == 2
        assert result.execution_time_ms == 150.5
        assert result.truncated is False
        assert result.error is None
        assert result.is_successful() is True
    
    def test_failed_query_result(self):
        """Test creating failed query result."""
        result = QueryResult(
            columns=[],
            rows=[],
            row_count=0,
            execution_time_ms=50.0,
            error="Syntax error in SQL query"
        )
        
        assert result.columns == []
        assert result.rows == []
        assert result.row_count == 0
        assert result.error == "Syntax error in SQL query"
        assert result.is_successful() is False
    
    def test_truncated_query_result(self):
        """Test creating truncated query result."""
        result = QueryResult(
            columns=["id"],
            rows=[{"id": i} for i in range(1000)],
            row_count=1000,
            execution_time_ms=2500.0,
            truncated=True
        )
        
        assert len(result.rows) == 1000
        assert result.truncated is True
        assert result.is_successful() is True
    
    def test_execution_time_formatting(self):
        """Test execution time formatting."""
        # Test milliseconds
        result_ms = QueryResult(
            columns=["id"],
            rows=[],
            row_count=0,
            execution_time_ms=150.5
        )
        assert result_ms.get_formatted_execution_time() == "150.50ms"
        
        # Test seconds
        result_s = QueryResult(
            columns=["id"],
            rows=[],
            row_count=0,
            execution_time_ms=2500.0
        )
        assert result_s.get_formatted_execution_time() == "2.50s"
    
    def test_serialization_complete_result(self):
        """Test serialization of complete query result."""
        result = QueryResult(
            columns=["id", "name"],
            rows=[{"id": 1, "name": "Test"}],
            row_count=1,
            execution_time_ms=100.0,
            truncated=False,
            error=None
        )
        
        serialized = result.to_dict()
        expected = {
            'columns': ['id', 'name'],
            'rows': [{'id': 1, 'name': 'Test'}],
            'row_count': 1,
            'execution_time_ms': 100.0,
            'truncated': False,
            'error': None
        }
        
        assert serialized == expected
    
    def test_round_trip_serialization(self):
        """Test round-trip serialization for QueryResult."""
        original = QueryResult(
            columns=["id", "name"],
            rows=[{"id": 1, "name": "Test"}],
            row_count=1,
            execution_time_ms=100.0,
            truncated=True,
            error="Some error"
        )
        
        serialized = original.to_dict()
        deserialized = QueryResult.from_dict(serialized)
        
        assert original == deserialized


class TestModelValidation:
    """Test cases for model validation and edge cases."""
    
    def test_empty_collections(self):
        """Test models with empty collections."""
        schema = TableSchema(
            database="test_db",
            table="empty_table",
            columns=[],
            indexes=[],
            primary_keys=[],
            foreign_keys=[]
        )
        
        assert len(schema.columns) == 0
        assert len(schema.indexes) == 0
        assert len(schema.primary_keys) == 0
        assert len(schema.foreign_keys) == 0
    
    def test_none_values_handling(self):
        """Test handling of None values in optional fields."""
        table_info = TableInfo(
            name="test_table",
            type="BASE TABLE",
            engine="InnoDB",
            rows=None,
            size_mb=None,
            comment=""
        )
        
        serialized = table_info.to_dict()
        assert serialized['rows'] is None
        assert serialized['size_mb'] is None
        
        deserialized = TableInfo.from_dict(serialized)
        assert deserialized.rows is None
        assert deserialized.size_mb is None
    
    def test_complex_foreign_keys(self):
        """Test complex foreign key relationships."""
        foreign_keys = [
            {
                "column": "department_id",
                "referenced_table": "departments",
                "referenced_column": "id"
            },
            {
                "column": "manager_id", 
                "referenced_table": "employees",
                "referenced_column": "id"
            }
        ]
        
        schema = TableSchema(
            database="hr_db",
            table="employees",
            columns=[],
            indexes=[],
            primary_keys=["id"],
            foreign_keys=foreign_keys
        )
        
        assert len(schema.foreign_keys) == 2
        assert schema.foreign_keys[0]["column"] == "department_id"
        assert schema.foreign_keys[1]["referenced_table"] == "employees"

class TestSampleDataResult:
    """Test cases for SampleDataResult model."""
    
    def test_creation_with_required_fields(self):
        """Test SampleDataResult creation with required fields."""
        from tidb_mcp_server.models import SampleDataResult
        
        result = SampleDataResult(
            database='test_db',
            table='users',
            columns=['id', 'name', 'email'],
            rows=[{'id': 1, 'name': 'John', 'email': 'john@example.com'}],
            row_count=1,
            total_table_rows=100,
            execution_time_ms=50.0,
            sampling_method='LIMIT_ORDER_BY'
        )
        
        assert result.database == 'test_db'
        assert result.table == 'users'
        assert result.columns == ['id', 'name', 'email']
        assert result.row_count == 1
        assert result.total_table_rows == 100
        assert result.execution_time_ms == 50.0
        assert result.sampling_method == 'LIMIT_ORDER_BY'
        assert result.masked_columns == []  # Default empty list
        assert result.error is None
    
    def test_creation_with_masking(self):
        """Test SampleDataResult creation with column masking."""
        from tidb_mcp_server.models import SampleDataResult
        
        result = SampleDataResult(
            database='test_db',
            table='users',
            columns=['id', 'name', 'email', 'phone'],
            rows=[{'id': 1, 'name': 'John', 'email': '***@***.***', 'phone': '***-***-****'}],
            row_count=1,
            total_table_rows=100,
            execution_time_ms=75.0,
            sampling_method='TABLESAMPLE',
            masked_columns=['email', 'phone']
        )
        
        assert result.masked_columns == ['email', 'phone']
        assert result.rows[0]['email'] == '***@***.***'
        assert result.rows[0]['phone'] == '***-***-****'
    
    def test_creation_with_error(self):
        """Test SampleDataResult creation with error."""
        from tidb_mcp_server.models import SampleDataResult
        
        result = SampleDataResult(
            database='test_db',
            table='nonexistent',
            columns=[],
            rows=[],
            row_count=0,
            total_table_rows=None,
            execution_time_ms=25.0,
            sampling_method='ERROR',
            error='Table does not exist'
        )
        
        assert not result.is_successful()
        assert result.error == 'Table does not exist'
        assert result.row_count == 0
        assert result.total_table_rows is None
    
    def test_execution_time_formatting(self):
        """Test execution time formatting for different durations."""
        from tidb_mcp_server.models import SampleDataResult
        
        # Fast query (milliseconds)
        result_fast = SampleDataResult(
            database='test_db', table='users', columns=[], rows=[], row_count=0,
            total_table_rows=0, execution_time_ms=150.5, sampling_method='LIMIT'
        )
        assert result_fast.get_formatted_execution_time() == "150.50ms"
        
        # Slow query (seconds)
        result_slow = SampleDataResult(
            database='test_db', table='users', columns=[], rows=[], row_count=0,
            total_table_rows=0, execution_time_ms=2500.0, sampling_method='TABLESAMPLE'
        )
        assert result_slow.get_formatted_execution_time() == "2.50s"
    
    def test_serialization(self):
        """Test SampleDataResult serialization and deserialization."""
        from tidb_mcp_server.models import SampleDataResult
        
        original = SampleDataResult(
            database='test_db',
            table='products',
            columns=['id', 'name', 'price'],
            rows=[
                {'id': 1, 'name': 'Product A', 'price': 19.99},
                {'id': 2, 'name': 'Product B', 'price': 29.99}
            ],
            row_count=2,
            total_table_rows=1000,
            execution_time_ms=125.0,
            sampling_method='LIMIT_ORDER_BY',
            masked_columns=['price']
        )
        
        # Test serialization
        result_dict = original.to_dict()
        assert result_dict['database'] == 'test_db'
        assert result_dict['table'] == 'products'
        assert result_dict['row_count'] == 2
        assert result_dict['masked_columns'] == ['price']
        
        # Test deserialization
        reconstructed = SampleDataResult.from_dict(result_dict)
        assert reconstructed.database == original.database
        assert reconstructed.table == original.table
        assert reconstructed.columns == original.columns
        assert reconstructed.rows == original.rows
        assert reconstructed.masked_columns == original.masked_columns
    
    def test_empty_result(self):
        """Test SampleDataResult for empty table."""
        from tidb_mcp_server.models import SampleDataResult
        
        result = SampleDataResult(
            database='test_db',
            table='empty_table',
            columns=['id', 'name'],
            rows=[],
            row_count=0,
            total_table_rows=0,
            execution_time_ms=10.0,
            sampling_method='LIMIT_EMPTY'
        )
        
        assert result.is_successful()
        assert result.row_count == 0
        assert result.rows == []
        assert result.total_table_rows == 0