import time
import pytest
from backend.schema_management.manager import SchemaCacheManager

class DummyClient:
    def __init__(self, schema):
        self.schema = schema
    def discover_schema(self):
        return self.schema

@pytest.fixture
def cache_manager():
    return SchemaCacheManager(client=DummyClient({"tables": []}), ttl=0.05)

def test_initial_fetch_and_cache(cache_manager):
    first = cache_manager.get_schema()
    second = cache_manager.get_schema()
    assert first is second

def test_cache_expiration(cache_manager):
    first = cache_manager.get_schema()
    time.sleep(0.06)
    second = cache_manager.get_schema()
    assert second is not first
