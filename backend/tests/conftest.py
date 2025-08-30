"""
Pytest configuration file for the backend tests.

This file contains pytest hooks and configuration that apply to all test modules.
"""

from tests.utils.env_loader import load_environment_variables


def pytest_configure():
    """Configure pytest with environment variables"""
    load_environment_variables()