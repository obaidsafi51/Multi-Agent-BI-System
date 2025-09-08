import pytest
from backend.schema_management.dynamic_validator import DynamicValidator

class DummyClient:
    def __init__(self, schema):
        self._schema = schema
    def discover_schema(self):
        return self._schema

@pytest.fixture
def validator():
    schema = {"tables": [{"name": "users", "columns": [{"name": "id", "type": "int"}]}]}
    return DynamicValidator(client=DummyClient(schema))

def test_validate_valid_record(validator):
    record = {"users": {"id": 123}}
    result = validator.validate(record)
    assert result.is_valid
    assert not result.errors

def test_validate_invalid_type(validator):
    record = {"users": {"id": "abc"}}
    result = validator.validate(record)
    assert not result.is_valid
    assert result.errors
