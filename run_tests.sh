#!/bin/bash

# Default test type is unit
TEST_TYPE=${1:-unit}

# Run tests with pytest
if [ "$TEST_TYPE" == "unit" ]; then
    echo "Running unit tests..."
    python -m pytest tests/unit -v
    exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo "Unit tests failed with exit code $exit_code"
        exit $exit_code
    fi
elif [ "$TEST_TYPE" == "integration" ]; then
    echo "Running integration tests..."
    echo "Note: Integration tests require a running server and Redis instance"
    python -m pytest tests/integration -v
    exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo "Integration tests failed with exit code $exit_code"
        exit $exit_code
    fi
elif [ "$TEST_TYPE" == "all" ]; then
    echo "Running all tests..."
    echo "Note: Integration tests require a running server and Redis instance"
    python -m pytest tests -v
    exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo "Tests failed with exit code $exit_code"
        exit $exit_code
    fi
elif [ "$TEST_TYPE" == "coverage" ]; then
    echo "Generating coverage report..."
    python -m pytest tests/unit --cov=backend --cov=streamlit --cov-report=term --cov-report=html
    exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo "Coverage tests failed with exit code $exit_code"
        exit $exit_code
    fi
else
    echo "Unknown test type: $TEST_TYPE"
    echo "Usage: $0 [unit|integration|all|coverage]"
    exit 1
fi

echo "Tests completed successfully!"
