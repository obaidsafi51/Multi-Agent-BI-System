"""Test fixtures and sample data for TiDB MCP Server tests."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from typing import Dict, List, Any, Optional

from tidb_mcp_server.config import ServerConfig


class MockDatabase:
    """Mock database with sample schema and data."""
    
    def __init__(self):
        self.tables = {
            "users": {
                "columns": [
                    {"name": "id", "type": "INT", "nullable": False, "key": "PRI"},
                    {"name": "username", "type": "VARCHAR(50)", "nullable": False, "key": "UNI"},
                    {"name": "email", "type": "VARCHAR(100)", "nullable": False, "key": ""},
                    {"name": "created_at", "type": "TIMESTAMP", "nullable": False, "key": ""},
                    {"name": "is_active", "type": "BOOLEAN", "nullable": False, "key": ""}
                ],
                "data": [
                    (1, "john_doe", "john@example.com", "2024-01-01 10:00:00", True),
                    (2, "jane_smith", "jane@example.com", "2024-01-02 11:00:00", True),
                    (3, "bob_wilson", "bob@example.com", "2024-01-03 12:00:00", False),
                    (4, "alice_brown", "alice@example.com", "2024-01-04 13:00:00", True),
                    (5, "charlie_davis", "charlie@example.com", "2024-01-05 14:00:00", True)
                ],
                "indexes": [
                    {"name": "PRIMARY", "columns": ["id"], "unique": True},
                    {"name": "idx_username", "columns": ["username"], "unique": True},
                    {"name": "idx_email", "columns": ["email"], "unique": False}
                ]
            },
            "orders": {
                "columns": [
                    {"name": "id", "type": "INT", "nullable": False, "key": "PRI"},
                    {"name": "user_id", "type": "INT", "nullable": False, "key": "MUL"},
                    {"name": "product_name", "type": "VARCHAR(100)", "nullable": False, "key": ""},
                    {"name": "quantity", "type": "INT", "nullable": False, "key": ""},
                    {"name": "price", "type": "DECIMAL(10,2)", "nullable": False, "key": ""},
                    {"name": "order_date", "type": "DATE", "nullable": False, "key": ""}
                ],
                "data": [
                    (1, 1, "Laptop", 1, 999.99, "2024-01-10"),
                    (2, 1, "Mouse", 2, 25.50, "2024-01-10"),
                    (3, 2, "Keyboard", 1, 75.00, "2024-01-11"),
                    (4, 3, "Monitor", 1, 299.99, "2024-01-12"),
                    (5, 4, "Headphones", 1, 150.00, "2024-01-13"),
                    (6, 1, "Webcam", 1, 89.99, "2024-01-14"),
                    (7, 5, "Tablet", 1, 399.99, "2024-01-15")
                ],
                "indexes": [
                    {"name": "PRIMARY", "columns": ["id"], "unique": True},
                    {"name": "idx_user_id", "columns": ["user_id"], "unique": False},
                    {"name": "idx_order_date", "columns": ["order_date"], "unique": False}
                ]
            },
            "products": {
                "columns": [
                    {"name": "id", "type": "INT", "nullable": False, "key": "PRI"},
                    {"name": "name", "type": "VARCHAR(100)", "nullable": False, "key": ""},
                    {"name": "category", "type": "VARCHAR(50)", "nullable": False, "key": "MUL"},
                    {"name": "price", "type": "DECIMAL(10,2)", "nullable": False, "key": ""},
                    {"name": "stock_quantity", "type": "INT", "nullable": False, "key": ""},
                    {"name": "description", "type": "TEXT", "nullable": True, "key": ""}
                ],
                "data": [
                    (1, "Laptop Pro", "Electronics", 999.99, 50, "High-performance laptop"),
                    (2, "Wireless Mouse", "Electronics", 25.50, 200, "Ergonomic wireless mouse"),
                    (3, "Mechanical Keyboard", "Electronics", 75.00, 100, "RGB mechanical keyboard"),
                    (4, "4K Monitor", "Electronics", 299.99, 75, "27-inch 4K display"),
                    (5, "Noise-Canceling Headphones", "Electronics", 150.00, 120, "Premium headphones"),
                    (6, "HD Webcam", "Electronics", 89.99, 80, "1080p webcam with microphone"),
                    (7, "Gaming Tablet", "Electronics", 399.99, 30, "High-performance gaming tablet")
                ],
                "indexes": [
                    {"name": "PRIMARY", "columns": ["id"], "unique": True},
                    {"name": "idx_category", "columns": ["category"], "unique": False},
                    {"name": "idx_name", "columns": ["name"], "unique": False}
                ]
            }
        }
        
        self.views = {
            "user_order_summary": {
                "definition": """
                SELECT 
                    u.id,
                    u.username,
                    u.email,
                    COUNT(o.id) as total_orders,
                    SUM(o.price * o.quantity) as total_spent
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id
                GROUP BY u.id, u.username, u.email
                """,
                "columns": [
                    {"name": "id", "type": "INT"},
                    {"name": "username", "type": "VARCHAR(50)"},
                    {"name": "email", "type": "VARCHAR(100)"},
                    {"name": "total_orders", "type": "BIGINT"},
                    {"name": "total_spent", "type": "DECIMAL(32,2)"}
                ]
            }
        }
    
    def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get schema information for a table."""
        return self.tables.get(table_name)
    
    def get_table_data(self, table_name: str) -> Optional[List[tuple]]:
        """Get data for a table."""
        table = self.tables.get(table_name)
        return table["data"] if table else None
    
    def execute_query(self, query: str) -> Dict[str, Any]:
        """Simulate query execution."""
        query_lower = query.lower().strip()
        
        # Handle SHOW TABLES
        if "show tables" in query_lower:
            return {
                "columns": ["Tables_in_test_db"],
                "rows": [(name,) for name in self.tables.keys()],
                "row_count": len(self.tables)
            }
        
        # Handle DESCRIBE table
        if query_lower.startswith("describe ") or query_lower.startswith("desc "):
            table_name = query.split()[-1].strip("`'\"")
            table = self.tables.get(table_name)
            if table:
                return {
                    "columns": ["Field", "Type", "Null", "Key", "Default", "Extra"],
                    "rows": [
                        (col["name"], col["type"], "YES" if col["nullable"] else "NO", 
                         col["key"], None, "")
                        for col in table["columns"]
                    ],
                    "row_count": len(table["columns"])
                }
        
        # Handle SELECT * FROM table
        if "select * from" in query_lower:
            table_name = query_lower.split("from")[-1].strip().split()[0].strip("`'\"")
            table = self.tables.get(table_name)
            if table:
                return {
                    "columns": [col["name"] for col in table["columns"]],
                    "rows": table["data"],
                    "row_count": len(table["data"])
                }
        
        # Handle COUNT queries
        if "count(*)" in query_lower and "from" in query_lower:
            table_name = query_lower.split("from")[-1].strip().split()[0].strip("`'\"")
            table = self.tables.get(table_name)
            if table:
                return {
                    "columns": ["count(*)"],
                    "rows": [(len(table["data"]),)],
                    "row_count": 1
                }
        
        # Default response for unknown queries
        return {
            "columns": ["result"],
            "rows": [("Query executed successfully",)],
            "row_count": 1
        }


@pytest.fixture
def mock_database():
    """Provide a mock database instance."""
    return MockDatabase()


@pytest.fixture
def sample_config():
    """Provide a sample configuration for testing."""
    config = MagicMock(spec=ServerConfig)
    config.tidb_host = "test-host.tidbcloud.com"
    config.tidb_port = 4000
    config.tidb_user = "test_user"
    config.tidb_password = "test_password"
    config.tidb_database = "test_database"
    config.tidb_ssl_ca = None
    config.mcp_server_name = "tidb-mcp-server"
    config.mcp_server_version = "0.1.0"
    config.log_level = "INFO"
    config.log_format = "text"
    config.cache_ttl = 300
    config.cache_max_size = 1000
    config.rate_limit_requests = 100
    config.rate_limit_window = 60
    return config


@pytest.fixture
def sample_query_results():
    """Provide sample query results for testing."""
    return {
        "simple_select": {
            "columns": ["id", "name", "email"],
            "rows": [
                (1, "John Doe", "john@example.com"),
                (2, "Jane Smith", "jane@example.com")
            ],
            "row_count": 2
        },
        "aggregation": {
            "columns": ["category", "total_products", "avg_price"],
            "rows": [
                ("Electronics", 10, 125.50),
                ("Books", 25, 15.99),
                ("Clothing", 15, 45.00)
            ],
            "row_count": 3
        },
        "empty_result": {
            "columns": ["id", "name"],
            "rows": [],
            "row_count": 0
        },
        "large_result": {
            "columns": ["id", "value"],
            "rows": [(i, f"value_{i}") for i in range(1000)],
            "row_count": 1000
        }
    }


@pytest.fixture
def sample_schema_info():
    """Provide sample schema information for testing."""
    return {
        "tables": [
            {
                "name": "users",
                "type": "BASE TABLE",
                "engine": "InnoDB",
                "rows": 1000,
                "data_length": 65536,
                "index_length": 32768
            },
            {
                "name": "orders",
                "type": "BASE TABLE", 
                "engine": "InnoDB",
                "rows": 5000,
                "data_length": 327680,
                "index_length": 98304
            },
            {
                "name": "products",
                "type": "BASE TABLE",
                "engine": "InnoDB", 
                "rows": 500,
                "data_length": 32768,
                "index_length": 16384
            }
        ],
        "views": [
            {
                "name": "user_order_summary",
                "type": "VIEW"
            }
        ],
        "columns": {
            "users": [
                {"name": "id", "type": "int", "nullable": False, "key": "PRI"},
                {"name": "username", "type": "varchar(50)", "nullable": False, "key": "UNI"},
                {"name": "email", "type": "varchar(100)", "nullable": False, "key": ""},
                {"name": "created_at", "type": "timestamp", "nullable": False, "key": ""}
            ],
            "orders": [
                {"name": "id", "type": "int", "nullable": False, "key": "PRI"},
                {"name": "user_id", "type": "int", "nullable": False, "key": "MUL"},
                {"name": "product_name", "type": "varchar(100)", "nullable": False, "key": ""},
                {"name": "quantity", "type": "int", "nullable": False, "key": ""},
                {"name": "price", "type": "decimal(10,2)", "nullable": False, "key": ""},
                {"name": "order_date", "type": "date", "nullable": False, "key": ""}
            ]
        },
        "indexes": {
            "users": [
                {"name": "PRIMARY", "columns": ["id"], "unique": True},
                {"name": "idx_username", "columns": ["username"], "unique": True},
                {"name": "idx_email", "columns": ["email"], "unique": False}
            ],
            "orders": [
                {"name": "PRIMARY", "columns": ["id"], "unique": True},
                {"name": "idx_user_id", "columns": ["user_id"], "unique": False},
                {"name": "idx_order_date", "columns": ["order_date"], "unique": False}
            ]
        }
    }


@pytest.fixture
def sample_mcp_tools():
    """Provide sample MCP tool definitions for testing."""
    return [
        {
            "name": "execute_query",
            "description": "Execute a SQL query against the TiDB database",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of rows to return",
                        "default": 1000
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "describe_table",
            "description": "Get detailed information about a table structure",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to describe"
                    },
                    "include_indexes": {
                        "type": "boolean",
                        "description": "Include index information",
                        "default": False
                    }
                },
                "required": ["table_name"]
            }
        },
        {
            "name": "list_tables",
            "description": "List all tables and views in the database",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "schema_name": {
                        "type": "string",
                        "description": "Schema name to filter by",
                        "default": None
                    },
                    "table_type": {
                        "type": "string",
                        "enum": ["TABLE", "VIEW", "ALL"],
                        "description": "Type of objects to list",
                        "default": "ALL"
                    }
                }
            }
        },
        {
            "name": "explain_query",
            "description": "Get the execution plan for a SQL query",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to explain"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["TRADITIONAL", "JSON", "TREE"],
                        "description": "Output format for the execution plan",
                        "default": "TRADITIONAL"
                    }
                },
                "required": ["query"]
            }
        }
    ]


@pytest.fixture
def mock_connection_factory():
    """Factory for creating mock database connections."""
    def create_mock_connection(mock_database: MockDatabase):
        mock_connection = AsyncMock()
        mock_cursor = AsyncMock()
        
        def mock_execute(query):
            result = mock_database.execute_query(query)
            mock_cursor.fetchall.return_value = result["rows"]
            mock_cursor.description = [(col,) for col in result["columns"]]
            mock_cursor.rowcount = result["row_count"]
        
        mock_cursor.execute.side_effect = mock_execute
        mock_connection.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_connection.cursor.return_value.__aexit__.return_value = None
        
        return mock_connection
    
    return create_mock_connection


@pytest.fixture
def sample_error_scenarios():
    """Provide sample error scenarios for testing."""
    return {
        "connection_error": {
            "exception": "pymysql.err.OperationalError",
            "message": "(2003, \"Can't connect to MySQL server on 'localhost' ([Errno 111] Connection refused)\")",
            "expected_code": "DATABASE_CONNECTION_ERROR"
        },
        "syntax_error": {
            "exception": "pymysql.err.ProgrammingError", 
            "message": "(1064, \"You have an error in your SQL syntax\")",
            "expected_code": "QUERY_SYNTAX_ERROR"
        },
        "permission_error": {
            "exception": "pymysql.err.OperationalError",
            "message": "(1142, \"SELECT command denied to user 'test'@'localhost' for table 'users'\")",
            "expected_code": "PERMISSION_DENIED"
        },
        "table_not_found": {
            "exception": "pymysql.err.ProgrammingError",
            "message": "(1146, \"Table 'test_db.nonexistent_table' doesn't exist\")",
            "expected_code": "TABLE_NOT_FOUND"
        },
        "timeout_error": {
            "exception": "pymysql.err.OperationalError",
            "message": "(2013, 'Lost connection to MySQL server during query')",
            "expected_code": "QUERY_TIMEOUT"
        }
    }


class MockMCPClient:
    """Mock MCP client for testing server responses."""
    
    def __init__(self, server):
        self.server = server
        self.session_id = "test_session_123"
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the server."""
        return await self.server.call_tool(tool_name, arguments)
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools."""
        return await self.server.list_tools()
    
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get server capabilities."""
        return self.server.get_capabilities()


@pytest.fixture
def mock_mcp_client(sample_config):
    """Provide a mock MCP client for testing."""
    from tidb_mcp_server.mcp_server import TiDBMCPServer
    
    with patch('tidb_mcp_server.mcp_server.QueryExecutor'):
        server = TiDBMCPServer(sample_config)
        return MockMCPClient(server)