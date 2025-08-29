"""
Environment variable loading utility for tests

This module provides a shared utility function for loading environment variables
from .env files, eliminating code duplication across test files.
"""

import os
from pathlib import Path
from typing import Optional


def load_environment_variables(env_file_path: Optional[Path] = None) -> None:
    """
    Load environment variables from .env file
    
    This function reads a .env file and sets environment variables for the current
    process. It handles missing files gracefully and parses the .env format correctly,
    ignoring comments and empty lines.
    
    Args:
        env_file_path: Optional path to .env file. If None, defaults to project root .env
        
    Example:
        # Load from default .env file in project root
        load_environment_variables()
        
        # Load from custom path
        load_environment_variables(Path("custom/.env"))
    """
    # Default to project root .env file if no path provided
    if env_file_path is None:
        # Navigate up from backend/tests/utils/ to project root
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent
        env_file_path = project_root / ".env"
    
    # Handle missing .env file gracefully
    if not env_file_path.exists():
        return
    
    try:
        with open(env_file_path, 'r', encoding='utf-8') as file:
            for line in file:
                # Strip whitespace from line
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Split on first '=' to handle values containing '='
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Set environment variable
                    if key:  # Only set if key is not empty
                        os.environ[key] = value
                        
    except (IOError, OSError):
        # Handle file read errors gracefully - continue execution
        pass