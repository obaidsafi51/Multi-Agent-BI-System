"""
Unit tests for SchemaInspector class.

Tests schema discovery functionality with mocked database responses.
"""

import pytest
from unittest.mock import Mock, patch
from tidb_mcp_server.schema_inspector import SchemaInspector
from tidb_mcp_server.models import DatabaseInfo, TableInfo, TableSchema, ColumnInfo, IndexInfo, SampleDataResult
from tidb_mcp_server.cache_manager import CacheManager


class TestSchemaInspector:
    """Test cases for SchemaInspector class."""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        return Mock()
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Create a mock cache manager."""
        return Mock(spec=CacheManager)
    
    @pytest.fixture
    def schema_inspector(self, mock_db_manager, mock_cache_manager):
        """Create a SchemaInspector instance with mocked dependencies."""
        return SchemaInspector(db_manager=mock_db_manager, cache_manager=mock_cache_manager)
    
    def test_init_with_dependencies(self, mock_db_manager, mock_cache_manager):
        """Test SchemaInspector initialization with provided dependencies."""
        inspector = SchemaInspector(db_manager=mock_db_manager, cache_manager=mock_cache_manager)
        
        assert inspector.db_manager is mock_db_manager
        assert inspector.cache_manager is mock_cache_manager
    
    def test_init_without_dependencies(self):
        """Test SchemaInspector initialization creates default dependencies."""
        with patch('tidb_mcp_server.schema_inspector.DatabaseManager') as mock_db_class, \
             patch('tidb_mcp_server.schema_inspector.CacheManager') as mock_cache_class:
            
            inspector = SchemaInspector()
            
            mock_db_class.assert_called_once()
            mock_cache_class.assert_called_once_with(default_ttl=300)   
    def test_get_databases_from_cache(self, schema_inspector, mock_cache_manager):
        """Test get_databases returns cached results when available."""
        # Setup
        cached_databases = [
            DatabaseInfo(name='test_db', charset='utf8mb4', collation='utf8mb4_general_ci', accessible=True)
        ]
        mock_cache_manager.get.return_value = cached_databases
        
        # Execute
        result = schema_inspector.get_databases()
        
        # Verify
        assert result == cached_databases
        mock_cache_manager.get.assert_called_once()
        schema_inspector.db_manager.execute_query.assert_not_called()
    
    def test_get_databases_from_database(self, schema_inspector, mock_db_manager, mock_cache_manager):
        """Test get_databases queries database when cache is empty."""
        # Setup
        mock_cache_manager.get.return_value = None
        mock_db_results = [
            {
                'name': 'test_db',
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_general_ci'
            },
            {
                'name': 'prod_db',
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci'
            }
        ]
        mock_db_manager.execute_query.return_value = mock_db_results
        
        # Mock database access test
        with patch.object(schema_inspector, '_test_database_access') as mock_test_access:
            mock_test_access.side_effect = [True, False]  # First accessible, second not
            
            # Execute
            result = schema_inspector.get_databases()
        
        # Verify
        assert len(result) == 2
        assert result[0].name == 'test_db'
        assert result[0].accessible is True
        assert result[1].name == 'prod_db'
        assert result[1].accessible is False
        
        # Verify database query was called
        mock_db_manager.execute_query.assert_called_once()
        
        # Verify caching
        mock_cache_manager.set.assert_called_once()
    
    def test_get_databases_handles_database_error(self, schema_inspector, mock_db_manager, mock_cache_manager):
        """Test get_databases handles database errors properly."""
        # Setup
        mock_cache_manager.get.return_value = None
        mock_db_manager.execute_query.side_effect = Exception("Database connection failed")
        
        # Execute & Verify
        with pytest.raises(Exception, match="Database connection failed"):
            schema_inspector.get_databases()    
    def test_get_tables_from_cache(self, schema_inspector, mock_cache_manager):
        """Test get_tables returns cached results when available."""
        # Setup
        database = 'test_db'
        cached_tables = [
            TableInfo(name='users', type='BASE TABLE', engine='InnoDB', rows=100, size_mb=1.5, comment='User table')
        ]
        mock_cache_manager.get.return_value = cached_tables
        
        # Execute
        result = schema_inspector.get_tables(database)
        
        # Verify
        assert result == cached_tables
        mock_cache_manager.get.assert_called_once()
        schema_inspector.db_manager.execute_query.assert_not_called()
    
    def test_get_tables_from_database(self, schema_inspector, mock_db_manager, mock_cache_manager):
        """Test get_tables queries database when cache is empty."""
        # Setup
        database = 'test_db'
        mock_cache_manager.get.return_value = None
        mock_db_results = [
            {
                'name': 'users',
                'type': 'BASE TABLE',
                'engine': 'InnoDB',
                'rows': 100,
                'size_mb': 1.5,
                'comment': 'User table'
            },
            {
                'name': 'orders',
                'type': 'BASE TABLE',
                'engine': 'InnoDB',
                'rows': 500,
                'size_mb': 3.2,
                'comment': None
            }
        ]
        mock_db_manager.execute_query.return_value = mock_db_results
        
        # Execute
        result = schema_inspector.get_tables(database)
        
        # Verify
        assert len(result) == 2
        assert result[0].name == 'users'
        assert result[0].comment == 'User table'
        assert result[1].name == 'orders'
        assert result[1].comment == ''  # None converted to empty string
        
        # Verify database query was called with correct parameters
        mock_db_manager.execute_query.assert_called_once()
        call_args = mock_db_manager.execute_query.call_args
        assert call_args[1]['params'] == (database,)
        assert call_args[1]['fetch_all'] is True
        
        # Verify caching
        mock_cache_manager.set.assert_called_once() 
    def test_get_table_schema_from_cache(self, schema_inspector, mock_cache_manager):
        """Test get_table_schema returns cached results when available."""
        # Setup
        database = 'test_db'
        table = 'users'
        cached_schema = TableSchema(
            database=database,
            table=table,
            columns=[ColumnInfo(name='id', data_type='int', is_nullable=False)],
            indexes=[IndexInfo(name='PRIMARY', columns=['id'], is_unique=True, index_type='BTREE')],
            primary_keys=['id'],
            foreign_keys=[]
        )
        mock_cache_manager.get.return_value = cached_schema
        
        # Execute
        result = schema_inspector.get_table_schema(database, table)
        
        # Verify
        assert result == cached_schema
        mock_cache_manager.get.assert_called_once()
    def test_get_table_schema_from_database(self, schema_inspector, mock_cache_manager):
        """Test get_table_schema queries database when cache is empty."""
        # Setup
        database = 'test_db'
        table = 'users'
        mock_cache_manager.get.return_value = None
        
        with patch.object(schema_inspector, '_get_column_info') as mock_get_columns, \
             patch.object(schema_inspector, '_get_index_info') as mock_get_indexes, \
             patch.object(schema_inspector, '_get_key_constraints') as mock_get_keys:
            
            # Setup mock returns
            mock_columns = [
                ColumnInfo(name='id', data_type='int', is_nullable=False),
                ColumnInfo(name='email', data_type='varchar', is_nullable=False),
                ColumnInfo(name='name', data_type='varchar', is_nullable=True)
            ]
            mock_indexes = [
                IndexInfo(name='PRIMARY', columns=['id'], is_unique=True, index_type='BTREE'),
                IndexInfo(name='idx_email', columns=['email'], is_unique=True, index_type='BTREE')
            ]
            mock_primary_keys = ['id']
            mock_foreign_keys = []
            
            mock_get_columns.return_value = mock_columns
            mock_get_indexes.return_value = mock_indexes
            mock_get_keys.return_value = (mock_primary_keys, mock_foreign_keys)
            
            # Execute
            result = schema_inspector.get_table_schema(database, table)
        
        # Verify
        assert result.database == database
        assert result.table == table
        assert len(result.columns) == 3
        assert result.columns[0].is_primary_key is True
        assert result.columns[1].is_primary_key is False
        assert len(result.indexes) == 2
        assert result.primary_keys == ['id']
        assert result.foreign_keys == []
        
        # Verify helper methods were called
        mock_get_columns.assert_called_once_with(database, table)
        mock_get_indexes.assert_called_once_with(database, table)
        mock_get_keys.assert_called_once_with(database, table)
        
        # Verify caching
        mock_cache_manager.set.assert_called_once() 
    def test_get_column_info(self, schema_inspector, mock_db_manager):
        """Test _get_column_info retrieves column information correctly."""
        # Setup
        database = 'test_db'
        table = 'users'
        mock_db_results = [
            {
                'name': 'id',
                'data_type': 'int',
                'is_nullable': 'NO',
                'default_value': None,
                'comment': 'Primary key'
            },
            {
                'name': 'email',
                'data_type': 'varchar',
                'is_nullable': 'NO',
                'default_value': None,
                'comment': 'User email address'
            },
            {
                'name': 'created_at',
                'data_type': 'timestamp',
                'is_nullable': 'YES',
                'default_value': 'CURRENT_TIMESTAMP',
                'comment': None
            }
        ]
        mock_db_manager.execute_query.return_value = mock_db_results
        
        # Execute
        result = schema_inspector._get_column_info(database, table)
        
        # Verify
        assert len(result) == 3
        
        # First column
        assert result[0].name == 'id'
        assert result[0].data_type == 'int'
        assert result[0].is_nullable is False
        assert result[0].default_value is None
        assert result[0].comment == 'Primary key'
        
        # Second column
        assert result[1].name == 'email'
        assert result[1].data_type == 'varchar'
        assert result[1].is_nullable is False
        assert result[1].comment == 'User email address'
        
        # Third column
        assert result[2].name == 'created_at'
        assert result[2].is_nullable is True
        assert result[2].default_value == 'CURRENT_TIMESTAMP'
        assert result[2].comment == ''  # None converted to empty string
    
    def test_get_column_info_handles_database_error(self, schema_inspector, mock_db_manager):
        """Test _get_column_info handles database errors properly."""
        # Setup
        database = 'test_db'
        table = 'users'
        mock_db_manager.execute_query.side_effect = Exception("Column query failed")
        
        # Execute & Verify
        with pytest.raises(Exception, match="Column query failed"):
            schema_inspector._get_column_info(database, table) 
    def test_get_key_constraints(self, schema_inspector, mock_db_manager):
        """Test _get_key_constraints retrieves primary and foreign key information correctly."""
        # Setup
        database = 'test_db'
        table = 'orders'
        
        # Mock results for multiple queries
        pk_results = [
            {'COLUMN_NAME': 'id'},
            {'COLUMN_NAME': 'order_number'}
        ]
        fk_results = [
            {
                'column_name': 'user_id',
                'constraint_name': 'fk_orders_user',
                'referenced_database': 'test_db',
                'referenced_table': 'users',
                'referenced_column': 'id'
            },
            {
                'column_name': 'product_id',
                'constraint_name': 'fk_orders_product',
                'referenced_database': 'test_db',
                'referenced_table': 'products',
                'referenced_column': 'id'
            }
        ]
        mock_db_manager.execute_query.side_effect = [pk_results, fk_results]
        
        # Execute
        primary_keys, foreign_keys = schema_inspector._get_key_constraints(database, table)
        
        # Verify primary keys
        assert len(primary_keys) == 2
        assert primary_keys == ['id', 'order_number']
        
        # Verify foreign keys
        assert len(foreign_keys) == 2
        
        # First foreign key
        assert foreign_keys[0]['column_name'] == 'user_id'
        assert foreign_keys[0]['constraint_name'] == 'fk_orders_user'
        assert foreign_keys[0]['referenced_table'] == 'users'
        assert foreign_keys[0]['referenced_column'] == 'id'
        
        # Second foreign key
        assert foreign_keys[1]['column_name'] == 'product_id'
        assert foreign_keys[1]['constraint_name'] == 'fk_orders_product'
        assert foreign_keys[1]['referenced_table'] == 'products'
        assert foreign_keys[1]['referenced_column'] == 'id'
        
        # Verify database queries
        assert mock_db_manager.execute_query.call_count == 2
        
        # Check primary key query
        pk_call = mock_db_manager.execute_query.call_args_list[0]
        assert pk_call[1]['params'] == (database, table)
        assert pk_call[1]['fetch_all'] is True
        
        # Check foreign key query
        fk_call = mock_db_manager.execute_query.call_args_list[1]
        assert fk_call[1]['params'] == (database, table)
        assert fk_call[1]['fetch_all'] is True    
    def test_test_database_access_success(self, schema_inspector, mock_db_manager):
        """Test _test_database_access returns True for accessible database."""
        # Setup
        database = 'test_db'
        mock_db_manager.execute_query.return_value = [{'1': 1}]
        
        # Execute
        result = schema_inspector._test_database_access(database)
        
        # Verify
        assert result is True
        mock_db_manager.execute_query.assert_called_once()
    
    def test_test_database_access_failure(self, schema_inspector, mock_db_manager):
        """Test _test_database_access returns False for inaccessible database."""
        # Setup
        database = 'test_db'
        mock_db_manager.execute_query.side_effect = Exception("Access denied")
        
        # Execute
        result = schema_inspector._test_database_access(database)
        
        # Verify
        assert result is False
    
    def test_invalidate_cache_specific_table(self, schema_inspector, mock_cache_manager):
        """Test invalidate_cache for specific table."""
        # Setup
        database = 'test_db'
        table = 'users'
        mock_cache_manager.invalidate.return_value = 1
        
        # Execute
        result = schema_inspector.invalidate_cache(database=database, table=table)
        
        # Verify
        assert result == 1
        mock_cache_manager.invalidate.assert_called_once()
    
    def test_invalidate_cache_database(self, schema_inspector, mock_cache_manager):
        """Test invalidate_cache for entire database."""
        # Setup
        database = 'test_db'
        mock_cache_manager.invalidate.return_value = 5
        
        # Execute
        result = schema_inspector.invalidate_cache(database=database)
        
        # Verify
        assert result == 15  # 3 patterns * 5 entries each
        assert mock_cache_manager.invalidate.call_count == 3
    
    def test_invalidate_cache_all(self, schema_inspector, mock_cache_manager):
        """Test invalidate_cache for all cached data."""
        # Setup
        mock_cache_manager.invalidate.return_value = 10
        
        # Execute
        result = schema_inspector.invalidate_cache()
        
        # Verify
        assert result == 40  # 4 patterns * 10 entries each
        assert mock_cache_manager.invalidate.call_count == 4
    
    def test_invalidate_cache_table_without_database_raises_error(self, schema_inspector):
        """Test invalidate_cache raises error when table specified without database."""
        # Execute & Verify
        with pytest.raises(ValueError, match="Database name is required when invalidating table cache"):
            schema_inspector.invalidate_cache(table='users')
    
    def test_get_cache_stats(self, schema_inspector, mock_cache_manager):
        """Test get_cache_stats returns cache statistics."""
        # Setup
        expected_stats = {'hits': 100, 'misses': 20, 'size': 50}
        mock_cache_manager.get_stats.return_value = expected_stats
        
        # Execute
        result = schema_inspector.get_cache_stats()
        
        # Verify
        assert result == expected_stats
        mock_cache_manager.get_stats.assert_called_once()

    # Sample Data Tests
    def test_get_sample_data_from_cache(self, schema_inspector, mock_cache_manager):
        """Test get_sample_data returns cached results when available."""
        # Setup
        database = 'test_db'
        table = 'users'
        limit = 10
        
        from tidb_mcp_server.models import SampleDataResult
        cached_result = SampleDataResult(
            database=database,
            table=table,
            columns=['id', 'name', 'email'],
            rows=[{'id': 1, 'name': 'John', 'email': 'john@example.com'}],
            row_count=1,
            total_table_rows=100,
            execution_time_ms=50.0,
            sampling_method='LIMIT_ORDER_BY',
            masked_columns=[]
        )
        mock_cache_manager.get.return_value = cached_result
        
        # Execute
        result = schema_inspector.get_sample_data(database, table, limit)
        
        # Verify
        assert result == cached_result
        mock_cache_manager.get.assert_called_once()
        schema_inspector.db_manager.execute_query.assert_not_called()

    def test_get_sample_data_invalid_limit(self, schema_inspector):
        """Test get_sample_data raises ValueError for invalid limit."""
        database = 'test_db'
        table = 'users'
        
        # Test limit too low
        with pytest.raises(ValueError, match="Sample limit must be between 1 and 100"):
            schema_inspector.get_sample_data(database, table, limit=0)
        
        # Test limit too high
        with pytest.raises(ValueError, match="Sample limit must be between 1 and 100"):
            schema_inspector.get_sample_data(database, table, limit=101)

    def test_get_sample_data_small_table(self, schema_inspector, mock_db_manager, mock_cache_manager):
        """Test get_sample_data with small table using ORDER BY strategy."""
        # Setup
        database = 'test_db'
        table = 'users'
        limit = 5
        
        mock_cache_manager.get.return_value = None
        
        # Mock table info query
        table_info_result = {'row_count': 50, 'size_mb': 0.5}
        
        # Mock column info
        from tidb_mcp_server.models import ColumnInfo
        column_info = [
            ColumnInfo(name='id', data_type='int', is_nullable=False),
            ColumnInfo(name='name', data_type='varchar', is_nullable=True),
            ColumnInfo(name='email', data_type='varchar', is_nullable=False)
        ]
        
        # Mock sample data query results
        sample_results = [
            {'id': 1, 'name': 'John', 'email': 'john@example.com'},
            {'id': 2, 'name': 'Jane', 'email': 'jane@example.com'}
        ]
        
        with patch.object(schema_inspector, '_get_table_row_count') as mock_get_count, \
             patch.object(schema_inspector, '_get_column_info') as mock_get_columns, \
             patch.object(schema_inspector, '_build_sample_query') as mock_build_query, \
             patch.object(schema_inspector, '_process_sample_rows') as mock_process_rows:
            
            mock_get_count.return_value = table_info_result
            mock_get_columns.return_value = column_info
            mock_build_query.return_value = ('LIMIT_ORDER_BY', 'SELECT * FROM test_db.users ORDER BY id LIMIT 5')
            mock_process_rows.return_value = sample_results
            mock_db_manager.execute_query.return_value = sample_results
            
            # Execute
            result = schema_inspector.get_sample_data(database, table, limit)
        
        # Verify
        assert result.database == database
        assert result.table == table
        assert result.columns == ['id', 'name', 'email']
        assert result.rows == sample_results
        assert result.row_count == 2
        assert result.total_table_rows == 50
        assert result.sampling_method == 'LIMIT_ORDER_BY'
        assert result.is_successful()
        
        # Verify caching (should cache since no masking)
        mock_cache_manager.set.assert_called_once()

    def test_get_sample_data_large_table_tablesample(self, schema_inspector, mock_db_manager, mock_cache_manager):
        """Test get_sample_data with large table using TABLESAMPLE strategy."""
        # Setup
        database = 'test_db'
        table = 'big_table'
        limit = 10
        
        mock_cache_manager.get.return_value = None
        
        # Mock table info query for large table
        table_info_result = {'row_count': 50000, 'size_mb': 100.0}
        
        # Mock column info
        from tidb_mcp_server.models import ColumnInfo
        column_info = [
            ColumnInfo(name='id', data_type='int', is_nullable=False),
            ColumnInfo(name='data', data_type='text', is_nullable=True)
        ]
        
        # Mock sample data query results
        sample_results = [{'id': i, 'data': f'data_{i}'} for i in range(1, 11)]
        
        with patch.object(schema_inspector, '_get_table_row_count') as mock_get_count, \
             patch.object(schema_inspector, '_get_column_info') as mock_get_columns, \
             patch.object(schema_inspector, '_build_sample_query') as mock_build_query, \
             patch.object(schema_inspector, '_process_sample_rows') as mock_process_rows:
            
            mock_get_count.return_value = table_info_result
            mock_get_columns.return_value = column_info
            mock_build_query.return_value = ('TABLESAMPLE', 'SELECT * FROM test_db.big_table TABLESAMPLE SYSTEM (0.1) LIMIT 10')
            mock_process_rows.return_value = sample_results
            mock_db_manager.execute_query.return_value = sample_results
            
            # Execute
            result = schema_inspector.get_sample_data(database, table, limit)
        
        # Verify
        assert result.sampling_method == 'TABLESAMPLE'
        assert result.row_count == 10
        assert result.total_table_rows == 50000

    def test_get_sample_data_with_column_masking(self, schema_inspector, mock_db_manager, mock_cache_manager):
        """Test get_sample_data with column masking for sensitive data."""
        # Setup
        database = 'test_db'
        table = 'users'
        limit = 5
        masked_columns = ['email', 'phone']
        
        mock_cache_manager.get.return_value = None
        
        # Mock dependencies
        table_info_result = {'row_count': 100, 'size_mb': 1.0}
        from tidb_mcp_server.models import ColumnInfo
        column_info = [
            ColumnInfo(name='id', data_type='int', is_nullable=False),
            ColumnInfo(name='name', data_type='varchar', is_nullable=True),
            ColumnInfo(name='email', data_type='varchar', is_nullable=False),
            ColumnInfo(name='phone', data_type='varchar', is_nullable=True)
        ]
        
        sample_results = [
            {'id': 1, 'name': 'John', 'email': 'john@example.com', 'phone': '1234567890'},
            {'id': 2, 'name': 'Jane', 'email': 'jane@example.com', 'phone': '0987654321'}
        ]
        
        processed_results = [
            {'id': 1, 'name': 'John', 'email': '***@***.***', 'phone': '***-***-****'},
            {'id': 2, 'name': 'Jane', 'email': '***@***.***', 'phone': '***-***-****'}
        ]
        
        with patch.object(schema_inspector, '_get_table_row_count') as mock_get_count, \
             patch.object(schema_inspector, '_get_column_info') as mock_get_columns, \
             patch.object(schema_inspector, '_build_sample_query') as mock_build_query, \
             patch.object(schema_inspector, '_process_sample_rows') as mock_process_rows:
            
            mock_get_count.return_value = table_info_result
            mock_get_columns.return_value = column_info
            mock_build_query.return_value = ('LIMIT_ORDER_BY', 'SELECT id, name, "***MASKED***" as email, "***MASKED***" as phone FROM test_db.users ORDER BY id LIMIT 5')
            mock_process_rows.return_value = processed_results
            mock_db_manager.execute_query.return_value = sample_results
            
            # Execute
            result = schema_inspector.get_sample_data(database, table, limit, masked_columns)
        
        # Verify
        assert result.masked_columns == masked_columns
        assert result.rows == processed_results
        
        # Verify no caching when masking is used
        mock_cache_manager.set.assert_not_called()

    def test_get_sample_data_empty_table(self, schema_inspector, mock_db_manager, mock_cache_manager):
        """Test get_sample_data with empty table."""
        # Setup
        database = 'test_db'
        table = 'empty_table'
        limit = 10
        
        mock_cache_manager.get.return_value = None
        
        # Mock empty table
        table_info_result = {'row_count': 0, 'size_mb': 0.0}
        from tidb_mcp_server.models import ColumnInfo
        column_info = [
            ColumnInfo(name='id', data_type='int', is_nullable=False),
            ColumnInfo(name='name', data_type='varchar', is_nullable=True)
        ]
        
        with patch.object(schema_inspector, '_get_table_row_count') as mock_get_count, \
             patch.object(schema_inspector, '_get_column_info') as mock_get_columns, \
             patch.object(schema_inspector, '_build_sample_query') as mock_build_query, \
             patch.object(schema_inspector, '_process_sample_rows') as mock_process_rows:
            
            mock_get_count.return_value = table_info_result
            mock_get_columns.return_value = column_info
            mock_build_query.return_value = ('LIMIT_EMPTY', 'SELECT id, name FROM test_db.empty_table LIMIT 10')
            mock_process_rows.return_value = []
            mock_db_manager.execute_query.return_value = []
            
            # Execute
            result = schema_inspector.get_sample_data(database, table, limit)
        
        # Verify
        assert result.row_count == 0
        assert result.rows == []
        assert result.total_table_rows == 0
        assert result.sampling_method == 'LIMIT_EMPTY'
        assert result.is_successful()

    def test_get_sample_data_database_error(self, schema_inspector, mock_db_manager, mock_cache_manager):
        """Test get_sample_data handles database errors properly."""
        # Setup
        database = 'test_db'
        table = 'users'
        limit = 10
        
        mock_cache_manager.get.return_value = None
        
        with patch.object(schema_inspector, '_get_table_row_count') as mock_get_count:
            mock_get_count.side_effect = Exception("Table does not exist")
            
            # Execute
            result = schema_inspector.get_sample_data(database, table, limit)
        
        # Verify error result
        assert not result.is_successful()
        assert result.error == "Table does not exist"
        assert result.row_count == 0
        assert result.rows == []
        assert result.sampling_method == 'ERROR'

    def test_build_sample_query_small_table(self, schema_inspector):
        """Test _build_sample_query for small table."""
        database = 'test_db'
        table = 'users'
        columns = ['id', 'name', 'email']
        limit = 5
        total_rows = 100
        masked_columns = []
        
        method, query = schema_inspector._build_sample_query(
            database, table, columns, limit, total_rows, masked_columns
        )
        
        assert method == 'LIMIT_ORDER_BY'
        assert 'ORDER BY' in query
        assert 'LIMIT 5' in query
        assert '`id`, `name`, `email`' in query

    def test_build_sample_query_large_table(self, schema_inspector):
        """Test _build_sample_query for large table."""
        database = 'test_db'
        table = 'big_table'
        columns = ['id', 'data']
        limit = 10
        total_rows = 50000
        masked_columns = []
        
        method, query = schema_inspector._build_sample_query(
            database, table, columns, limit, total_rows, masked_columns
        )
        
        assert method == 'TABLESAMPLE'
        assert 'TABLESAMPLE SYSTEM' in query
        assert 'LIMIT 10' in query

    def test_build_sample_query_with_masking(self, schema_inspector):
        """Test _build_sample_query with column masking."""
        database = 'test_db'
        table = 'users'
        columns = ['id', 'name', 'email', 'phone']
        limit = 5
        total_rows = 100
        masked_columns = ['email', 'phone']
        
        method, query = schema_inspector._build_sample_query(
            database, table, columns, limit, total_rows, masked_columns
        )
        
        assert "'***MASKED***' as `email`" in query
        assert "'***MASKED***' as `phone`" in query
        assert "`id`" in query
        assert "`name`" in query

    def test_build_sample_query_empty_table(self, schema_inspector):
        """Test _build_sample_query for empty table."""
        database = 'test_db'
        table = 'empty_table'
        columns = ['id', 'name']
        limit = 10
        total_rows = 0
        masked_columns = []
        
        method, query = schema_inspector._build_sample_query(
            database, table, columns, limit, total_rows, masked_columns
        )
        
        assert method == 'LIMIT_EMPTY'
        assert 'LIMIT 10' in query

    def test_process_sample_rows_no_masking(self, schema_inspector):
        """Test _process_sample_rows without masking."""
        from datetime import datetime
        
        raw_rows = [
            {'id': 1, 'name': 'John', 'created_at': datetime(2023, 1, 1, 12, 0, 0)},
            {'id': 2, 'name': 'Jane', 'created_at': datetime(2023, 1, 2, 12, 0, 0)}
        ]
        masked_columns = []
        
        result = schema_inspector._process_sample_rows(raw_rows, masked_columns)
        
        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[0]['name'] == 'John'
        assert result[0]['created_at'] == '2023-01-01T12:00:00'  # datetime converted to ISO string

    def test_process_sample_rows_with_masking(self, schema_inspector):
        """Test _process_sample_rows with column masking."""
        raw_rows = [
            {'id': 1, 'name': 'John', 'email': 'john@example.com'},
            {'id': 2, 'name': 'Jane', 'email': 'jane@example.com'}
        ]
        masked_columns = ['email']
        
        with patch.object(schema_inspector, '_mask_sensitive_value') as mock_mask:
            mock_mask.return_value = '***@***.***'
            
            result = schema_inspector._process_sample_rows(raw_rows, masked_columns)
        
        assert len(result) == 2
        assert result[0]['email'] == '***@***.***'
        assert result[1]['email'] == '***@***.***'
        assert mock_mask.call_count == 2

    def test_mask_sensitive_value_email(self, schema_inspector):
        """Test _mask_sensitive_value for email addresses."""
        result = schema_inspector._mask_sensitive_value('john@example.com')
        assert result == '***@***.***'

    def test_mask_sensitive_value_phone(self, schema_inspector):
        """Test _mask_sensitive_value for phone numbers."""
        result = schema_inspector._mask_sensitive_value('1234567890')
        assert result == '***-***-****'

    def test_mask_sensitive_value_long_string(self, schema_inspector):
        """Test _mask_sensitive_value for long strings."""
        result = schema_inspector._mask_sensitive_value('this_is_a_long_string')
        assert result == 'th***ng'

    def test_mask_sensitive_value_short_string(self, schema_inspector):
        """Test _mask_sensitive_value for short strings."""
        result = schema_inspector._mask_sensitive_value('short')
        assert result == '***MASKED***'

    def test_mask_sensitive_value_none(self, schema_inspector):
        """Test _mask_sensitive_value for None values."""
        result = schema_inspector._mask_sensitive_value(None)
        assert result is None

    def test_get_table_row_count(self, schema_inspector, mock_db_manager):
        """Test _get_table_row_count retrieves table statistics."""
        database = 'test_db'
        table = 'users'
        
        mock_result = {'row_count': 1000, 'size_mb': 5.5}
        mock_db_manager.execute_query.return_value = mock_result
        
        result = schema_inspector._get_table_row_count(database, table)
        
        assert result['row_count'] == 1000
        assert result['size_mb'] == 5.5
        
        # Verify query parameters
        call_args = mock_db_manager.execute_query.call_args
        assert call_args[1]['params'] == (database, table)
        assert call_args[1]['fetch_one'] is True

    def test_get_table_row_count_no_result(self, schema_inspector, mock_db_manager):
        """Test _get_table_row_count when table doesn't exist."""
        database = 'test_db'
        table = 'nonexistent'
        
        mock_db_manager.execute_query.return_value = None
        
        result = schema_inspector._get_table_row_count(database, table)
        
        assert result['row_count'] == 0
        assert result['size_mb'] == 0

    def test_get_table_row_count_null_values(self, schema_inspector, mock_db_manager):
        """Test _get_table_row_count handles null values from database."""
        database = 'test_db'
        table = 'users'
        
        mock_result = {'row_count': None, 'size_mb': None}
        mock_db_manager.execute_query.return_value = mock_result
        
        result = schema_inspector._get_table_row_count(database, table)
        
        assert result['row_count'] == 0
        assert result['size_mb'] == 0