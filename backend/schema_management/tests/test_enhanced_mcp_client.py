import pytest
from backend.schema_management.client import BackendMCPClient, EnhancedMCPClient


def test_enhanced_client_subclass():
    assert issubclass(EnhancedMCPClient, BackendMCPClient)


def test_enhanced_client_health_and_schema(requests_mock):
    url = "http://localhost:1234"
    client = EnhancedMCPClient(url=url)
    requests_mock.get(f"{url}/health", json={"status": "ok"}, status_code=200)
    assert client.health_check_sync() is True
    sample = {"tables": [{"name": "test", "columns": []}]}
    requests_mock.get(f"{url}/schema", json=sample)
    data = client.discover_schema_sync()
    assert data["tables"][0]["name"] == "test"
