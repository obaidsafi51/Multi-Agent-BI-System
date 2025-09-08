import pytest
import requests
from backend.schema_management.client import BackendMCPClient

@ pytest.fixture
def client(monkeypatch):
    # create a test client pointing to a fake MCP server
    return BackendMCPClient(url="http://localhost:1234")

def test_health_check_success(client, requests_mock):
    requests_mock.get("http://localhost:1234/health", json={"status": "ok"}, status_code=200)
    assert client.health_check_sync() is True


def test_health_check_failure(client, requests_mock):
    requests_mock.get("http://localhost:1234/health", status_code=500)
    assert client.health_check_sync() is False


def test_get_schema_returns_data(client, requests_mock):
    sample_schema = {"tables": [{"name": "users", "columns": []}]}
    requests_mock.get("http://localhost:1234/schema", json=sample_schema)
    schema = client.discover_schema()
    assert isinstance(schema, dict)
    assert schema["tables"][0]["name"] == "users"
