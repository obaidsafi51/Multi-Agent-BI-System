"""
Cache module for Data Agent

This module provides caching functionality to improve performance
and reduce redundant operations.
"""

from .manager import (
    CacheManager,
    QueryCache,
    SchemaCache,
    get_cache_manager,
    close_cache_manager
)

__all__ = [
    'CacheManager',
    'QueryCache', 
    'SchemaCache',
    'get_cache_manager',
    'close_cache_manager'
]
