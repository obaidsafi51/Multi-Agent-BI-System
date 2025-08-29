"""
Pytest-compatible tests for pure PyMySQL database implementation
"""

import pytest
import sys
import os
from pathlib import Path
from decimal import Decimal
from datetime import date

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database.connection import (
    DatabaseManager,
    DatabaseConfig,
    get_database,
    tidb_connection,
    test_tidb_connection,
    execute_query,
    execute_many
)
from database.validation import DataValidator, FinancialDataValidator, ValidationError


class TestDatabaseConfig:
    """Test database configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = DatabaseConfig()
        
        assert config.port == 4000
        assert config.user == "root"
        assert config.autocommit is True
        assert config.query_timeout == 30
        assert config.retry_attempts == 3
    
    def test_pymysql_config_generation(self):
        """Test PyMySQL configuration generation"""
        config = DatabaseConfig()
        pymysql_config = config.pymysql_config
        
        assert "host" in pymysql_config
        assert "port" in pymysql_config
        assert "user" in pymysql_config
        assert "database" in pymysql_config
        assert "autocommit" in pymysql_config
        assert "cursorclass" in pymysql_config
        assert "charset" in pymysql_config


class TestDatabaseConnection:
    """Test database connection functionality"""
    
    def test_tidb_connection_health(self):
        """Test TiDB connection health check"""
        result = test_tidb_connection()
        assert result is True, "TiDB connection should be healthy"
    
    def test_context_manager_connection(self):
        """Test context manager connection"""
        with tidb_connection() as conn:
            assert conn is not None
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                assert result["test"] == 1
    
    def test_database_manager_health_check(self):
        """Test DatabaseManager health check"""
        db = DatabaseManager()
        result = db.health_check()
        assert result is True, "DatabaseManager health check should pass"
    
    def test_database_manager_query_execution(self):
        """Test DatabaseManager query execution"""
        db = DatabaseManager()
        
        # Test simple query
        result = db.execute_query("SELECT 42 as answer", fetch_one=True)
        assert result is not None
        assert result["answer"] == 42
        
        # Test query with parameters
        result = db.execute_query(
            "SELECT %s as param_value", 
            ("test_param",), 
            fetch_one=True
        )
        assert result["param_value"] == "test_param"
    
    def test_global_database_functions(self):
        """Test global database convenience functions"""
        # Test get_database
        db = get_database()
        assert isinstance(db, DatabaseManager)
        
        # Test global execute_query
        result = execute_query("SELECT 'global_test' as test_value", fetch_one=True)
        assert result["test_value"] == "global_test"


class TestCRUDOperations:
    """Test CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        # Setup: Create test table
        db = get_database()
        db.execute_query("""
            CREATE TABLE IF NOT EXISTS pytest_test_table (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100),
                value DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        yield
        
        # Teardown: Drop test table
        db.execute_query("DROP TABLE IF EXISTS pytest_test_table")
    
    def test_insert_operation(self):
        """Test insert operation"""
        db = get_database()
        
        rows_affected = db.execute_query(
            "INSERT INTO pytest_test_table (name, value) VALUES (%s, %s)",
            ("Test Item", Decimal("123.45"))
        )
        assert rows_affected == 1
    
    def test_select_operation(self):
        """Test select operation"""
        db = get_database()
        
        # Insert test data
        db.execute_query(
            "INSERT INTO pytest_test_table (name, value) VALUES (%s, %s)",
            ("Select Test", Decimal("99.99"))
        )
        
        # Select the data
        result = db.execute_query(
            "SELECT name, value FROM pytest_test_table WHERE name = %s",
            ("Select Test",),
            fetch_one=True
        )
        
        assert result is not None
        assert result["name"] == "Select Test"
        assert result["value"] == Decimal("99.99")
    
    def test_update_operation(self):
        """Test update operation"""
        db = get_database()
        
        # Insert test data
        db.execute_query(
            "INSERT INTO pytest_test_table (name, value) VALUES (%s, %s)",
            ("Update Test", Decimal("100.00"))
        )
        
        # Update the data
        rows_affected = db.execute_query(
            "UPDATE pytest_test_table SET value = %s WHERE name = %s",
            (Decimal("200.00"), "Update Test")
        )
        assert rows_affected == 1
        
        # Verify the update
        result = db.execute_query(
            "SELECT value FROM pytest_test_table WHERE name = %s",
            ("Update Test",),
            fetch_one=True
        )
        assert result["value"] == Decimal("200.00")
    
    def test_delete_operation(self):
        """Test delete operation"""
        db = get_database()
        
        # Insert test data
        db.execute_query(
            "INSERT INTO pytest_test_table (name, value) VALUES (%s, %s)",
            ("Delete Test", Decimal("50.00"))
        )
        
        # Delete the data
        rows_affected = db.execute_query(
            "DELETE FROM pytest_test_table WHERE name = %s",
            ("Delete Test",)
        )
        assert rows_affected == 1
        
        # Verify deletion
        result = db.execute_query(
            "SELECT COUNT(*) as count FROM pytest_test_table WHERE name = %s",
            ("Delete Test",),
            fetch_one=True
        )
        assert result["count"] == 0
    
    def test_execute_many_operation(self):
        """Test execute many operation"""
        db = get_database()
        
        test_data = [
            ("Item 1", Decimal("10.00")),
            ("Item 2", Decimal("20.00")),
            ("Item 3", Decimal("30.00"))
        ]
        
        rows_affected = db.execute_many(
            "INSERT INTO pytest_test_table (name, value) VALUES (%s, %s)",
            test_data
        )
        assert rows_affected == 3
        
        # Verify all records were inserted
        results = db.execute_query("SELECT COUNT(*) as count FROM pytest_test_table")
        assert results[0]["count"] == 3


class TestTransactions:
    """Test transaction functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for transaction tests"""
        db = get_database()
        db.execute_query("""
            CREATE TABLE IF NOT EXISTS pytest_transaction_test (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100),
                value INT
            )
        """)
        
        yield
        
        db.execute_query("DROP TABLE IF EXISTS pytest_transaction_test")
    
    def test_successful_transaction(self):
        """Test successful transaction execution"""
        db = get_database()
        
        queries = [
            ("INSERT INTO pytest_transaction_test (name, value) VALUES (%s, %s)", ("Item A", 100)),
            ("INSERT INTO pytest_transaction_test (name, value) VALUES (%s, %s)", ("Item B", 200)),
            ("UPDATE pytest_transaction_test SET value = value + %s WHERE name = %s", (50, "Item A"))
        ]
        
        success = db.execute_transaction(queries)
        assert success is True
        
        # Verify transaction results
        results = db.execute_query("SELECT * FROM pytest_transaction_test ORDER BY name")
        assert len(results) == 2
        assert results[0]["name"] == "Item A"
        assert results[0]["value"] == 150  # 100 + 50
        assert results[1]["name"] == "Item B"
        assert results[1]["value"] == 200


class TestDataValidation:
    """Test data validation functionality"""
    
    def test_validate_decimal_valid(self):
        """Test valid decimal validation"""
        result = DataValidator.validate_decimal("123.45", "test_field")
        assert result == Decimal("123.45")
        
        result = DataValidator.validate_decimal(None, "test_field")
        assert result is None
    
    def test_validate_decimal_invalid(self):
        """Test invalid decimal validation"""
        with pytest.raises(ValidationError) as exc_info:
            DataValidator.validate_decimal("invalid", "test_field")
        assert exc_info.value.field == "test_field"
    
    def test_validate_date_valid(self):
        """Test valid date validation"""
        result = DataValidator.validate_date("2024-01-15", "test_date")
        assert result == date(2024, 1, 15)
        
        result = DataValidator.validate_date(None, "test_date")
        assert result is None
    
    def test_validate_string_valid(self):
        """Test valid string validation"""
        result = DataValidator.validate_string("  test string  ", "test_field")
        assert result == "test string"
    
    def test_validate_percentage_valid(self):
        """Test valid percentage validation"""
        result = DataValidator.validate_percentage("50.5", "test_percentage")
        assert result == Decimal("50.5")
    
    def test_validate_percentage_invalid(self):
        """Test invalid percentage validation"""
        with pytest.raises(ValidationError):
            DataValidator.validate_percentage("150", "test_percentage")
    
    def test_financial_overview_validation(self):
        """Test financial overview data validation"""
        data = {
            'period_date': '2024-01-31',
            'period_type': 'monthly',
            'revenue': '1000000.00',
            'gross_profit': '400000.00'
        }
        
        result = FinancialDataValidator.validate_financial_overview(data)
        
        assert result['period_date'] == date(2024, 1, 31)
        assert result['period_type'] == 'monthly'
        assert result['revenue'] == Decimal('1000000.00')
        assert result['gross_profit'] == Decimal('400000.00')


def load_environment_variables():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent.parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value


# Load environment variables for tests
def pytest_configure():
    """Configure pytest with environment variables"""
    load_environment_variables()


# Load environment variables immediately when module is imported
load_environment_variables()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])