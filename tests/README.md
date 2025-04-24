# Testing Framework

This directory contains the comprehensive testing framework for the LPU Knowledge Assistant project. This README provides detailed information about the test structure, how to run tests, and how to add new tests.

## Table of Contents

- [Test Structure](#test-structure)
- [Environment Setup](#environment-setup)
- [Running Tests](#running-tests)
- [Code Coverage](#code-coverage)
- [Test Configuration](#test-configuration)
- [Test Markers](#test-markers)
- [Test Fixtures](#test-fixtures)
- [Writing New Tests](#writing-new-tests)
- [Troubleshooting](#troubleshooting)
- [Continuous Integration](#continuous-integration)

## Test Structure

The test suite is organized into two main categories:

```
tests/
├── conftest.py           # Shared test fixtures and configuration
├── unit/                 # Unit tests for individual components
│   ├── backend/          # Tests for backend components
│   └── streamlit/        # Tests for frontend components
└── integration/          # Integration tests for end-to-end functionality
    ├── test_chat_api.py  # Tests for chat API
    ├── test_http_lpu.py  # Tests for HTTP endpoints
    └── ...               # Other integration tests
```

### Unit Tests

Unit tests focus on testing individual components in isolation. They are:
- Fast to run
- Independent of external services
- Focused on specific functionality

### Integration Tests

Integration tests verify that different components work together correctly. They:
- Test end-to-end functionality
- Require external services (Redis, running server)
- Simulate real user interactions

## Environment Setup

### Prerequisites

1. Activate your virtual environment:
   ```bash
   source agentenv/bin/activate  # On Linux/Mac
   # OR
   .\agentenv\Scripts\activate  # On Windows
   ```

2. Install the test dependencies:
   ```bash
   pip install -r requirements-test.txt
   ```

3. For integration tests, ensure:
   - Redis server is running
   - Backend server is running on the configured port (default: 8000)

### Environment Configuration

Tests use environment variables for configuration. The main variables are:

- `SERVER_HOST`: Host for the backend server (default: "localhost")
- `PORT`: Port for the backend server (default: "8000")

These can be set in a `.env` file or directly in your environment.

## Running Tests

### Using the Test Script (Recommended)

The `run_tests.sh` script provides a convenient way to run tests:

```bash
# Run unit tests (default)
./run_tests.sh

# Run unit tests explicitly
./run_tests.sh unit

# Run integration tests
./run_tests.sh integration

# Run all tests
./run_tests.sh all

# Generate coverage report
./run_tests.sh coverage
```

### Using pytest Directly

#### Running All Tests

```bash
python -m pytest
```

#### Running Unit Tests

```bash
python -m pytest tests/unit -v
```

#### Running Integration Tests

```bash
python -m pytest tests/integration -v
```

#### Running a Specific Test File

```bash
python -m pytest tests/integration/test_websocket_client.py -v
```

#### Running a Specific Test Function

```bash
python -m pytest tests/integration/test_websocket_client.py::test_websocket -v
```

## Code Coverage

### Running Tests with Coverage

Code coverage measures how much of your code is executed during tests. It helps identify untested code paths.

```bash
python -m pytest tests --cov=backend --cov=streamlit --cov-report=term --cov-report=html
```

Or use the test script:

```bash
./run_tests.sh coverage
```

### Understanding Coverage Reports

The coverage report is generated in two formats:

1. **Terminal Report**: Shows a summary in the console
2. **HTML Report**: Detailed interactive report in `htmlcov/index.html`

#### Terminal Report Example

```
----------- coverage: platform linux, python 3.11.11-final-0 -----------
Name                                 Stmts   Miss  Cover
--------------------------------------------------------
backend/__init__.py                     0      0   100%
backend/config.py                      45     10    78%
backend/main_fastapi.py               120     35    71%
backend/memory.py                      42      5    88%
backend/redis_memory.py                62      8    87%
backend/special_queries.py             25      2    92%
streamlit/__init__.py                   0      0   100%
streamlit/app.py                       85     25    71%
streamlit/config.py                    30      5    83%
--------------------------------------------------------
TOTAL                                 409     90    78%
```

#### HTML Report

The HTML report provides a detailed view of coverage for each file, highlighting:

- **Green lines**: Executed during tests
- **Red lines**: Not executed during tests
- **Yellow lines**: Partially executed (e.g., only one branch of an if statement)

To view the HTML report:

```bash
open htmlcov/index.html  # On macOS
# OR
xdg-open htmlcov/index.html  # On Linux
# OR
start htmlcov/index.html  # On Windows
```

### Improving Coverage

1. **Identify low-coverage areas**: Look for files with low coverage percentages
2. **Add tests for uncovered code**: Focus on red lines in the HTML report
3. **Test edge cases**: Ensure all branches of conditional statements are tested
4. **Set coverage targets**: Aim for at least 80% coverage for critical components

## Test Configuration

### conftest.py

The `conftest.py` file contains shared fixtures and configuration for all tests. Key configurations include:

- Server URL and WebSocket URL derived from environment variables
- Redis client configuration
- Test data and fixtures

### pytest.ini

The `pytest.ini` file contains global pytest configuration, including:

- Registered markers
- Test discovery patterns
- Default options

## Test Markers

Test markers are used to categorize tests and control which tests are run. The main markers are:

- `unit`: Unit tests
- `integration`: Integration tests
- `redis`: Tests that require Redis
- `websocket`: Tests that require WebSocket server
- `http`: Tests that require HTTP server
- `slow`: Slow tests
- `skip_if_no_server`: Tests that should be skipped if the server is not running

To run tests with a specific marker:

```bash
python -m pytest -m "websocket" -v
```

To skip tests with a specific marker:

```bash
python -m pytest -m "not slow" -v
```

## Test Fixtures

Fixtures are reusable components that set up the test environment. Key fixtures include:

- `websocket`: A WebSocket client connected to the server
- `redis_client`: A Redis client for testing
- `session_id`: A unique session ID for testing
- `query`: Test queries for integration tests
- `personal_info`: Test personal information
- `institution_id`: Test institution ID

To use a fixture in a test:

```python
def test_function(websocket, session_id):
    # Test code using the websocket and session_id fixtures
    pass
```

## Writing New Tests

### Creating a New Test File

1. Create a new file in the appropriate directory (unit/ or integration/)
2. Name the file with the prefix `test_` (e.g., `test_new_feature.py`)
3. Import the necessary modules and fixtures

### Writing Test Functions

1. Name functions with the prefix `test_` (e.g., `def test_new_feature():`)
2. Add appropriate markers using decorators
3. Use fixtures as function parameters
4. Write assertions to verify expected behavior

Example:

```python
import pytest

@pytest.mark.integration
@pytest.mark.websocket
@pytest.mark.skip_if_no_server
def test_new_feature(websocket, session_id):
    # Test code
    assert result == expected
```

### Best Practices

1. **Keep tests independent**: Each test should run in isolation
2. **Use environment variables**: Avoid hardcoding configuration values
3. **Clear test data**: Clean up any test data created during the test
4. **Use descriptive names**: Test names should describe what they're testing
5. **Follow AAA pattern**: Arrange, Act, Assert

## Troubleshooting

### Common Issues

#### Integration Tests Failing

- Ensure the backend server is running on the configured port
- Check that Redis is running and accessible
- Verify environment variables are set correctly

#### WebSocket Tests Failing

- Ensure the WebSocket endpoint is available at `/chat`
- Check that the server is handling WebSocket connections correctly
- Verify the WebSocket URL is correct (default: `ws://localhost:8000/chat`)

#### Redis Tests Failing

- Ensure Redis is running on the default port (6379)
- Check Redis connection settings in the configuration

### Debugging Tips

1. Run tests with increased verbosity:
   ```bash
   python -m pytest -vv
   ```

2. Print debug information in tests:
   ```python
   print(f"Debug info: {variable}")
   ```

3. Use pytest's built-in debugger:
   ```bash
   python -m pytest --pdb
   ```

4. Run a specific failing test:
   ```bash
   python -m pytest path/to/test_file.py::test_function -v
   ```

## Continuous Integration

### Automated Testing

The test suite is designed to be run in a CI/CD pipeline. Key features for CI integration:

1. **Automatic test discovery**: All files named `test_*.py` are automatically discovered
2. **Exit codes**: Tests return non-zero exit code on failure for CI pipeline integration
3. **JUnit XML reports**: Generate reports for CI systems with `--junitxml=report.xml`
4. **Environment variable support**: Tests can be configured via environment variables

### Example CI Configuration

```yaml
# Example GitHub Actions workflow
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run unit tests
        run: python -m pytest tests/unit -v --junitxml=unit-report.xml
      - name: Start backend server
        run: python backend/main_fastapi.py &
      - name: Wait for server to start
        run: sleep 5
      - name: Run integration tests
        run: python -m pytest tests/integration -v -m "skip_if_no_server" --junitxml=integration-report.xml
      - name: Upload test reports
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: '*-report.xml'
```

### Best Practices for CI

1. **Run unit tests first**: They're faster and catch basic issues early
2. **Separate test stages**: Run unit and integration tests in separate stages
3. **Use test markers**: Skip tests that require external services if they're not available
4. **Cache dependencies**: Speed up CI runs by caching pip packages
5. **Parallelize tests**: Run tests in parallel to speed up the CI pipeline
