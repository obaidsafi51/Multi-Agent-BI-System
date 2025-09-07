"""Tests for main module."""

import argparse
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

from tidb_mcp_server.main import (
    main, 
    setup_logging, 
    parse_arguments, 
    validate_config_and_connection,
    main_async
)
from tidb_mcp_server.exceptions import ConfigurationError, DatabaseConnectionError


class TestSetupLogging:
    """Test logging setup."""
    
    def test_setup_logging_info_json(self):
        """Test logging setup with INFO level and JSON format."""
        setup_logging("INFO", "json")
        # Just verify it doesn't raise an exception
        # More detailed logging tests would require checking actual log output
    
    def test_setup_logging_debug_text(self):
        """Test logging setup with DEBUG level and text format."""
        setup_logging("DEBUG", "text")
        # Just verify it doesn't raise an exception


class TestParseArguments:
    """Test command-line argument parsing."""
    
    def test_parse_arguments_default(self):
        """Test parsing with no arguments."""
        with patch('sys.argv', ['tidb-mcp-server']):
            args = parse_arguments()
            assert args.log_level is None
            assert args.log_format is None
            assert args.validate_config is False
            assert args.check_connection is False
    
    def test_parse_arguments_log_level(self):
        """Test parsing with log level argument."""
        with patch('sys.argv', ['tidb-mcp-server', '--log-level', 'DEBUG']):
            args = parse_arguments()
            assert args.log_level == 'DEBUG'
    
    def test_parse_arguments_log_format(self):
        """Test parsing with log format argument."""
        with patch('sys.argv', ['tidb-mcp-server', '--log-format', 'json']):
            args = parse_arguments()
            assert args.log_format == 'json'
    
    def test_parse_arguments_validate_config(self):
        """Test parsing with validate config flag."""
        with patch('sys.argv', ['tidb-mcp-server', '--validate-config']):
            args = parse_arguments()
            assert args.validate_config is True
    
    def test_parse_arguments_check_connection(self):
        """Test parsing with check connection flag."""
        with patch('sys.argv', ['tidb-mcp-server', '--check-connection']):
            args = parse_arguments()
            assert args.check_connection is True


class TestValidateConfigAndConnection:
    """Test configuration validation and connection testing."""
    
    @pytest.mark.asyncio
    async def test_validate_config_success(self):
        """Test successful configuration validation."""
        mock_config = MagicMock()
        mock_config.validate_configuration.return_value = None
        
        with patch('tidb_mcp_server.query_executor.QueryExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.test_connection.return_value = None
            mock_executor_class.return_value = mock_executor
            
            result = await validate_config_and_connection(mock_config)
            assert result == 0
            mock_config.validate_configuration.assert_called_once()
            mock_executor.test_connection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_config_configuration_error(self):
        """Test configuration validation error."""
        mock_config = MagicMock()
        mock_config.validate_configuration.side_effect = ConfigurationError("Invalid config")
        
        result = await validate_config_and_connection(mock_config)
        assert result == 1
    
    @pytest.mark.asyncio
    async def test_validate_config_database_error(self):
        """Test database connection error."""
        mock_config = MagicMock()
        mock_config.validate_configuration.return_value = None
        
        with patch('tidb_mcp_server.query_executor.QueryExecutor') as mock_executor_class:
            mock_executor = AsyncMock()
            mock_executor.test_connection.side_effect = DatabaseConnectionError("Connection failed")
            mock_executor_class.return_value = mock_executor
            
            result = await validate_config_and_connection(mock_config)
            assert result == 2


class TestMainAsync:
    """Test async main function."""
    
    @pytest.mark.asyncio
    async def test_main_async_success(self):
        """Test successful async main execution."""
        mock_config = MagicMock()
        mock_config.validate_configuration.return_value = None
        mock_config.mcp_server_version = "0.1.0"
        mock_config.tidb_host = "test-host"
        mock_config.tidb_port = 4000
        mock_config.log_level = "INFO"
        
        with patch('tidb_mcp_server.main.TiDBMCPServer') as mock_server_class:
            mock_server = AsyncMock()
            mock_server.start.return_value = None
            mock_server.shutdown.return_value = None
            mock_server_class.return_value = mock_server
            
            result = await main_async(mock_config)
            assert result == 0
            mock_server.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_main_async_configuration_error(self):
        """Test async main with configuration error."""
        mock_config = MagicMock()
        mock_config.validate_configuration.side_effect = ConfigurationError("Invalid config")
        
        result = await main_async(mock_config)
        assert result == 1
    
    @pytest.mark.asyncio
    async def test_main_async_database_error(self):
        """Test async main with database error."""
        mock_config = MagicMock()
        mock_config.validate_configuration.return_value = None
        mock_config.mcp_server_version = "0.1.0"
        mock_config.tidb_host = "test-host"
        mock_config.tidb_port = 4000
        mock_config.log_level = "INFO"
        
        with patch('tidb_mcp_server.main.TiDBMCPServer') as mock_server_class:
            mock_server_class.side_effect = DatabaseConnectionError("Connection failed")
            
            result = await main_async(mock_config)
            assert result == 2


class TestMain:
    """Test main function."""
    
    @patch('tidb_mcp_server.main.parse_arguments')
    @patch('tidb_mcp_server.main.load_config')
    @patch('tidb_mcp_server.main.setup_logging')
    @patch('tidb_mcp_server.main.main_async')
    def test_main_success(self, mock_main_async, mock_setup_logging, mock_load_config, mock_parse_args):
        """Test successful main execution."""
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.log_format = None
        mock_args.validate_config = False
        mock_args.check_connection = False
        mock_parse_args.return_value = mock_args
        
        mock_config = MagicMock()
        mock_config.log_level = "INFO"
        mock_config.log_format = "text"
        mock_load_config.return_value = mock_config
        
        with patch('asyncio.run') as mock_asyncio_run:
            mock_asyncio_run.return_value = 0
            
            result = main()
            assert result == 0
            mock_setup_logging.assert_called_once_with("INFO", "text")
            mock_asyncio_run.assert_called_once()
    
    @patch('tidb_mcp_server.main.parse_arguments')
    @patch('tidb_mcp_server.main.load_config')
    @patch('tidb_mcp_server.main.setup_logging')
    @patch('tidb_mcp_server.main.validate_config_and_connection')
    def test_main_validate_config(self, mock_validate, mock_setup_logging, mock_load_config, mock_parse_args):
        """Test main with validate config flag."""
        mock_args = MagicMock()
        mock_args.log_level = None
        mock_args.log_format = None
        mock_args.validate_config = True
        mock_args.check_connection = False
        mock_parse_args.return_value = mock_args
        
        mock_config = MagicMock()
        mock_config.log_level = "INFO"
        mock_config.log_format = "text"
        mock_load_config.return_value = mock_config
        
        with patch('asyncio.run') as mock_asyncio_run:
            mock_asyncio_run.return_value = 0
            
            result = main()
            assert result == 0
            mock_asyncio_run.assert_called_once()
    
    @patch('tidb_mcp_server.main.parse_arguments')
    def test_main_keyboard_interrupt(self, mock_parse_args):
        """Test main with keyboard interrupt."""
        mock_parse_args.side_effect = KeyboardInterrupt()
        
        with patch('builtins.print') as mock_print:
            result = main()
            assert result == 130
            mock_print.assert_called_once()
    
    @patch('tidb_mcp_server.main.parse_arguments')
    def test_main_unexpected_error(self, mock_parse_args):
        """Test main with unexpected error."""
        mock_parse_args.side_effect = RuntimeError("Unexpected error")
        
        with patch('builtins.print') as mock_print:
            result = main()
            assert result == 1
            mock_print.assert_called_once()