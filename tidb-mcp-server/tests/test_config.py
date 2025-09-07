"""Tests for configuration management."""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from tidb_mcp_server.config import (
    ServerConfig,
    DatabaseConfig,
    MCPServerConfig,
    CacheConfig,
    SecurityConfig,
    load_config,
)
from tidb_mcp_server.exceptions import ConfigurationError


class TestDatabaseConfig:
    """Test DatabaseConfig validation."""
    
    def test_valid_config(self):
        """Test valid database configuration."""
        config = DatabaseConfig(
            host="localhost",
            port=4000,
            user="test_user",
            password="test_password"
        )
        assert config.host == "localhost"
        assert config.port == 4000
        assert config.user == "test_user"
        assert config.password == "test_password"
    
    def test_invalid_port(self):
        """Test invalid port validation."""
        with pytest.raises(ValidationError):
            DatabaseConfig(
                host="localhost",
                port=70000,  # Invalid port
                user="test_user",
                password="test_password"
            )
    
    def test_invalid_timeout(self):
        """Test invalid timeout validation."""
        with pytest.raises(ValidationError):
            DatabaseConfig(
                host="localhost",
                port=4000,
                user="test_user",
                password="test_password",
                connect_timeout=-1  # Invalid timeout
            )


class TestMCPServerConfig:
    """Test MCPServerConfig validation."""
    
    def test_valid_config(self):
        """Test valid MCP server configuration."""
        config = MCPServerConfig(
            name="test-server",
            version="1.0.0",
            max_connections=5,
            request_timeout=60
        )
        assert config.name == "test-server"
        assert config.version == "1.0.0"
        assert config.max_connections == 5
        assert config.request_timeout == 60
    
    def test_invalid_max_connections(self):
        """Test invalid max connections validation."""
        with pytest.raises(ValidationError):
            MCPServerConfig(max_connections=0)


class TestCacheConfig:
    """Test CacheConfig validation."""
    
    def test_valid_config(self):
        """Test valid cache configuration."""
        config = CacheConfig(
            enabled=True,
            ttl_seconds=600,
            max_size=500
        )
        assert config.enabled is True
        assert config.ttl_seconds == 600
        assert config.max_size == 500
    
    def test_invalid_ttl(self):
        """Test invalid TTL validation."""
        with pytest.raises(ValidationError):
            CacheConfig(ttl_seconds=0)


class TestSecurityConfig:
    """Test SecurityConfig validation."""
    
    def test_valid_config(self):
        """Test valid security configuration."""
        config = SecurityConfig(
            max_query_timeout=45,
            max_sample_rows=50,
            rate_limit_requests_per_minute=120
        )
        assert config.max_query_timeout == 45
        assert config.max_sample_rows == 50
        assert config.rate_limit_requests_per_minute == 120
    
    def test_invalid_query_timeout(self):
        """Test invalid query timeout validation."""
        with pytest.raises(ValidationError):
            SecurityConfig(max_query_timeout=500)  # Too high
    
    def test_invalid_sample_rows(self):
        """Test invalid sample rows validation."""
        with pytest.raises(ValidationError):
            SecurityConfig(max_sample_rows=2000)  # Too high


class TestServerConfig:
    """Test ServerConfig validation and loading."""
    
    @patch.dict(os.environ, {
        'TIDB_HOST': 'test-host.com',
        'TIDB_USER': 'test_user',
        'TIDB_PASSWORD': 'test_password',
    })
    def test_valid_server_config(self):
        """Test valid server configuration from environment."""
        config = ServerConfig()
        assert config.tidb_host == 'test-host.com'
        assert config.tidb_user == 'test_user'
        assert config.tidb_password == 'test_password'
        assert config.tidb_port == 4000  # Default value
    
    @patch.dict(os.environ, {
        'TIDB_HOST': 'test-host.com',
        'TIDB_USER': 'test_user',
        'TIDB_PASSWORD': 'test_password',
        'LOG_LEVEL': 'DEBUG',
        'LOG_FORMAT': 'text'
    })
    def test_log_configuration(self):
        """Test log configuration validation."""
        config = ServerConfig()
        assert config.log_level == 'DEBUG'
        assert config.log_format == 'text'
    
    @patch.dict(os.environ, {
        'TIDB_HOST': 'test-host.com',
        'TIDB_USER': 'test_user',
        'TIDB_PASSWORD': 'test_password',
        'LOG_LEVEL': 'INVALID'
    })
    def test_invalid_log_level(self):
        """Test invalid log level validation."""
        with pytest.raises(ValidationError):
            ServerConfig()
    
    @patch.dict(os.environ, {
        'TIDB_HOST': 'test-host.com',
        'TIDB_USER': 'test_user',
        'TIDB_PASSWORD': 'test_password',
    })
    def test_get_config_objects(self):
        """Test getting configuration objects."""
        config = ServerConfig()
        
        db_config = config.get_database_config()
        assert isinstance(db_config, DatabaseConfig)
        assert db_config.host == 'test-host.com'
        
        mcp_config = config.get_mcp_server_config()
        assert isinstance(mcp_config, MCPServerConfig)
        
        cache_config = config.get_cache_config()
        assert isinstance(cache_config, CacheConfig)
        
        security_config = config.get_security_config()
        assert isinstance(security_config, SecurityConfig)
    
    @patch.dict(os.environ, {
        'TIDB_HOST': '',  # Empty host
        'TIDB_USER': 'test_user',
        'TIDB_PASSWORD': 'test_password',
    })
    def test_validation_failure(self):
        """Test configuration validation failure."""
        config = ServerConfig()
        with pytest.raises(ValueError, match="Configuration validation failed"):
            config.validate_configuration()
    
    @patch.dict(os.environ, {
        'TIDB_HOST': 'test-host.com',
        'TIDB_USER': 'test_user',
        'TIDB_PASSWORD': 'test_password',
        'MCP_REQUEST_TIMEOUT': '10',
        'MAX_QUERY_TIMEOUT': '20'
    })
    def test_timeout_relationship_validation(self):
        """Test timeout relationship validation."""
        config = ServerConfig()
        with pytest.raises(ValueError, match="MCP request timeout must be"):
            config.validate_configuration()


class TestLoadConfig:
    """Test load_config function."""
    
    @patch.dict(os.environ, {
        'TIDB_HOST': 'test-host.com',
        'TIDB_USER': 'test_user',
        'TIDB_PASSWORD': 'test_password',
    })
    def test_successful_load(self):
        """Test successful configuration loading."""
        config = load_config()
        assert isinstance(config, ServerConfig)
        assert config.tidb_host == 'test-host.com'
    
    @patch.dict(os.environ, {}, clear=True)
    def test_failed_load(self):
        """Test failed configuration loading."""
        with pytest.raises(ValueError, match="Failed to load configuration"):
            load_config()