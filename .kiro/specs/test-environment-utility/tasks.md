# Implementation Plan

- [ ] 1. Create shared utility module structure

  - Create `backend/tests/utils/` directory if it doesn't exist
  - Create `backend/tests/utils/__init__.py` file
  - Create `backend/tests/utils/env_loader.py` with the shared environment loading function
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.1, 3.2_

- [ ] 2. Implement environment loading utility function

  - Write `load_environment_variables()` function with optional path parameter
  - Implement .env file parsing logic (handle comments, empty lines, key=value format)
  - Add proper error handling for missing files and malformed content
  - Include comprehensive docstring documentation
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.2, 3.3_

- [ ] 3. Update test_database_pytest.py to use shared utility

  - Remove the local `load_environment_variables()` function
  - Add import statement for shared utility function
  - Update `pytest_configure()` function to use imported utility
  - Update module-level call to use imported utility
  - _Requirements: 2.1, 2.3, 2.4_

- [ ] 4. Update test_database_connection.py to use shared utility

  - Remove local environment loading logic from `main()` function
  - Add import statement for shared utility function
  - Update `main()` function to call shared utility instead of local implementation
  - _Requirements: 2.2, 2.3, 2.4_

- [ ] 5. Create unit tests for the shared utility

  - Write test cases for valid .env file loading
  - Write test cases for missing .env file handling
  - Write test cases for malformed .env content
  - Write test cases for custom file path parameter
  - Write test cases to verify environment variables are properly set
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ] 6. Verify integration and run existing tests
  - Run the existing test suite to ensure functionality is preserved
  - Verify that both updated test files load environment variables correctly
  - Confirm that pytest configuration still works as expected
  - _Requirements: 2.3, 2.4_
