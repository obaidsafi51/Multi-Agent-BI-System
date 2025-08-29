"""
Unit tests for the shared environment loading utility

Tests cover various scenarios including valid .env files, missing files,
malformed content, custom paths, and environment variable verification.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from tests.utils.env_loader import load_environment_variables


class TestLoadEnvironmentVariables:
    """Test cases for the load_environment_variables function"""
    
    def setup_method(self):
        """Set up test environment before each test"""
        # Store original environment variables to restore later
        self.original_env = dict(os.environ)
        
    def teardown_method(self):
        """Clean up after each test"""
        # Restore original environment variables
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_valid_env_file_loading(self):
        """Test loading valid .env file with various formats"""
        # Create temporary .env file with valid content
        env_content = """# This is a comment
DATABASE_HOST=localhost
DATABASE_PORT=4000
DATABASE_NAME=test_db

# Another comment
API_KEY=secret123
EMPTY_VALUE=
VALUE_WITH_EQUALS=key=value=more
SPACED_VALUE= value with spaces 
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as temp_file:
            temp_file.write(env_content)
            temp_file_path = Path(temp_file.name)
        
        try:
            # Load environment variables from temporary file
            load_environment_variables(temp_file_path)
            
            # Verify environment variables are set correctly
            assert os.environ.get('DATABASE_HOST') == 'localhost'
            assert os.environ.get('DATABASE_PORT') == '4000'
            assert os.environ.get('DATABASE_NAME') == 'test_db'
            assert os.environ.get('API_KEY') == 'secret123'
            assert os.environ.get('EMPTY_VALUE') == ''
            assert os.environ.get('VALUE_WITH_EQUALS') == 'key=value=more'
            assert os.environ.get('SPACED_VALUE') == 'value with spaces'
            
        finally:
            # Clean up temporary file
            temp_file_path.unlink()
    
    def test_missing_env_file_handling(self):
        """Test graceful handling of missing .env file"""
        # Create path to non-existent file using cross-platform temporary directory
        temp_dir = Path(tempfile.gettempdir())
        non_existent_path = temp_dir / "non_existent_file.env"
        
        # Should not raise any exceptions
        load_environment_variables(non_existent_path)
        
        # Environment should remain unchanged (no new variables added)
        # This test passes if no exception is raised
        assert True
    
    def test_malformed_env_content(self):
        """Test handling of malformed .env content"""
        # Create temporary .env file with malformed content
        malformed_content = """# Valid comment
VALID_KEY=valid_value
invalid_line_without_equals
=value_without_key
KEY_WITHOUT_VALUE=
# Another comment
ANOTHER_VALID=test

malformed line with spaces but no equals
FINAL_VALID=final_value
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as temp_file:
            temp_file.write(malformed_content)
            temp_file_path = Path(temp_file.name)
        
        try:
            # Should handle malformed content gracefully
            load_environment_variables(temp_file_path)
            
            # Verify only valid lines were processed
            assert os.environ.get('VALID_KEY') == 'valid_value'
            assert os.environ.get('KEY_WITHOUT_VALUE') == ''
            assert os.environ.get('ANOTHER_VALID') == 'test'
            assert os.environ.get('FINAL_VALID') == 'final_value'
            
            # Verify malformed lines were ignored
            assert 'invalid_line_without_equals' not in os.environ
            assert '' not in os.environ  # Empty key should not be set
            
        finally:
            # Clean up temporary file
            temp_file_path.unlink()
    
    def test_custom_file_path_parameter(self):
        """Test using custom file path parameter"""
        # Create temporary directory and .env file
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_env_path = Path(temp_dir) / "custom.env"
            
            # Write test content to custom path
            env_content = """CUSTOM_VAR=custom_value
ANOTHER_CUSTOM=another_value"""
            
            with open(custom_env_path, 'w') as f:
                f.write(env_content)
            
            # Load from custom path
            load_environment_variables(custom_env_path)
            
            # Verify variables were loaded
            assert os.environ.get('CUSTOM_VAR') == 'custom_value'
            assert os.environ.get('ANOTHER_CUSTOM') == 'another_value'
    
    def test_environment_variables_properly_set(self):
        """Test that environment variables are properly set in os.environ"""
        # Create temporary .env file
        env_content = """TEST_VAR_1=value1
TEST_VAR_2=value2
TEST_VAR_3=value with spaces and symbols!@#"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as temp_file:
            temp_file.write(env_content)
            temp_file_path = Path(temp_file.name)
        
        try:
            # Store initial environment state
            initial_keys = set(os.environ.keys())
            
            # Load environment variables
            load_environment_variables(temp_file_path)
            
            # Verify new variables are in os.environ
            assert 'TEST_VAR_1' in os.environ
            assert 'TEST_VAR_2' in os.environ
            assert 'TEST_VAR_3' in os.environ
            
            # Verify values are correct
            assert os.environ['TEST_VAR_1'] == 'value1'
            assert os.environ['TEST_VAR_2'] == 'value2'
            assert os.environ['TEST_VAR_3'] == 'value with spaces and symbols!@#'
            
            # Verify variables are accessible via os.getenv()
            assert os.getenv('TEST_VAR_1') == 'value1'
            assert os.getenv('TEST_VAR_2') == 'value2'
            assert os.getenv('TEST_VAR_3') == 'value with spaces and symbols!@#'
            
        finally:
            # Clean up temporary file
            temp_file_path.unlink()
    
    def test_default_env_file_path(self):
        """Test that default path resolves to project root .env"""
        # Create a temporary .env file in a known location to test default behavior
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock project structure
            project_root = Path(temp_dir)
            backend_dir = project_root / "backend"
            tests_dir = backend_dir / "tests"
            utils_dir = tests_dir / "utils"
            utils_dir.mkdir(parents=True)
            
            # Create .env file in project root
            env_file = project_root / ".env"
            env_file.write_text("DEFAULT_TEST=default_value\n")
            
            # Mock __file__ to point to our temporary utils directory
            mock_file_path = utils_dir / "env_loader.py"
            
            with patch('tests.utils.env_loader.__file__', str(mock_file_path)):
                # Load environment variables (should use default path)
                load_environment_variables()
                
                # Verify the environment variable was loaded
                assert os.environ.get('DEFAULT_TEST') == 'default_value'
    
    def test_file_read_error_handling(self):
        """Test graceful handling of file read errors"""
        # Create a file path that will cause read errors
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as temp_file:
            temp_file.write("TEST_VAR=test_value")
            temp_file_path = Path(temp_file.name)
        
        try:
            # Mock open to raise IOError
            with patch('builtins.open', side_effect=IOError("Mocked read error")):
                # Should handle the error gracefully without raising exception
                load_environment_variables(temp_file_path)
                
                # Test passes if no exception is raised
                assert True
                
        finally:
            # Clean up temporary file
            temp_file_path.unlink()
    
    def test_empty_env_file(self):
        """Test handling of empty .env file"""
        # Create empty temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as temp_file:
            # Write nothing to create empty file
            temp_file_path = Path(temp_file.name)
        
        try:
            # Should handle empty file gracefully
            load_environment_variables(temp_file_path)
            
            # Test passes if no exception is raised
            assert True
            
        finally:
            # Clean up temporary file
            temp_file_path.unlink()
    
    def test_comments_and_empty_lines_ignored(self):
        """Test that comments and empty lines are properly ignored"""
        # Create .env file with only comments and empty lines
        env_content = """# This is a comment

# Another comment


# Final comment
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as temp_file:
            temp_file.write(env_content)
            temp_file_path = Path(temp_file.name)
        
        try:
            # Store initial environment state
            initial_env = dict(os.environ)
            
            # Load environment variables
            load_environment_variables(temp_file_path)
            
            # Environment should remain unchanged
            assert dict(os.environ) == initial_env
            
        finally:
            # Clean up temporary file
            temp_file_path.unlink()