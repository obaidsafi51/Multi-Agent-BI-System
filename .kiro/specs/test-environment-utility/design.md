# Design Document

## Overview

The test environment utility will provide a centralized solution for loading environment variables from .env files across the test suite. This design eliminates code duplication by creating a shared utility module that can be imported by any test file needing environment variable loading functionality.

## Architecture

The solution follows a simple utility module pattern:

```
backend/tests/
├── __init__.py
├── utils/
│   ├── __init__.py
│   └── env_loader.py  # New shared utility
├── test_database_pytest.py  # Updated to use shared utility
└── test_database_connection.py  # Updated to use shared utility
```

## Components and Interfaces

### Environment Loader Utility (`backend/tests/utils/env_loader.py`)

**Primary Function:**

```python
def load_environment_variables(env_file_path: Optional[Path] = None) -> None:
    """
    Load environment variables from .env file

    Args:
        env_file_path: Optional path to .env file. If None, defaults to project root .env
    """
```

**Key Features:**

- Accepts optional custom .env file path for flexibility
- Defaults to project root .env file when no path provided
- Handles missing .env files gracefully
- Parses .env format correctly (ignores comments, empty lines)
- Sets variables in os.environ for process-wide availability

**Implementation Details:**

- Uses pathlib.Path for cross-platform file path handling
- Strips whitespace from lines before processing
- Skips comment lines (starting with #) and empty lines
- Splits on first '=' to handle values containing '=' characters
- No external dependencies beyond standard library

### Updated Test Files

**test_database_pytest.py Changes:**

- Remove local `load_environment_variables()` function
- Import shared utility: `from tests.utils.env_loader import load_environment_variables`
- Update `pytest_configure()` to use imported function
- Update module-level call to use imported function

**test_database_connection.py Changes:**

- Remove local environment loading logic from `main()` function
- Import shared utility: `from tests.utils.env_loader import load_environment_variables`
- Update `main()` function to use imported function

## Data Models

No complex data models are required. The utility works with:

- **Input:** File path (pathlib.Path or string)
- **Processing:** Text lines from .env file
- **Output:** Environment variables set in os.environ

## Error Handling

The utility implements graceful error handling:

1. **Missing .env file:** Continue execution without raising errors
2. **File read errors:** Log warning and continue (optional logging)
3. **Malformed lines:** Skip invalid lines and continue processing
4. **Permission errors:** Handle gracefully and continue

Error handling strategy prioritizes test execution continuity over strict validation.

## Testing Strategy

### Unit Tests

- Test with valid .env file containing various formats
- Test with missing .env file
- Test with malformed .env content
- Test with custom file path parameter
- Test environment variable setting verification

### Integration Tests

- Verify existing test files continue to work after refactoring
- Confirm environment variables are properly loaded in test context
- Validate pytest configuration still functions correctly

### Test Data Examples

```
# Valid .env content for testing
DATABASE_HOST=localhost
DATABASE_PORT=4000
# Comment line to ignore
EMPTY_VALUE=
VALUE_WITH_EQUALS=key=value=more
```

## Migration Strategy

1. **Create utility module** with shared function
2. **Update test files** to import and use shared utility
3. **Remove duplicated code** from individual test files
4. **Run test suite** to verify functionality is preserved
5. **Add unit tests** for the new utility function

This approach ensures zero downtime and maintains backward compatibility throughout the migration process.
