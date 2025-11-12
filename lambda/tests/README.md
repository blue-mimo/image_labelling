# Lambda Function Tests

This directory contains unit tests for all Lambda functions in the image labeling application.

## Running Tests

### Run all tests:
```bash
cd lambda
../.venv/bin/python -m pytest tests/ -v
```

### Run specific test file:
```bash
cd lambda
../.venv/bin/python -m pytest tests/test_suggest_filters.py -v
```

### Run with coverage:
```bash
cd lambda
../.venv/bin/python -m pytest tests/ --cov=. --cov-report=term-missing
```

### Run specific tests with coverage:
```bash
cd lambda
../.venv/bin/python -m pytest tests/test_update_prefix_suggestions.py tests/test_suggest_filters.py \
  --cov=update_prefix_suggestions --cov=suggest_filters --cov-report=term-missing
```

## Test Files

- `test_update_prefix_suggestions.py` - Tests for prefix suggestions update Lambda (35 tests, 99% coverage)
- `test_suggest_filters.py` - Tests for filter suggestions Lambda (11 tests, 100% coverage)
- `test_process_added_image.py` - Tests for image processing Lambda
- `test_list_images.py` - Tests for listing images Lambda
- `test_get_labels.py` - Tests for getting labels Lambda
- `test_get_image.py` - Tests for getting images Lambda
- `test_upload_image.py` - Tests for uploading images Lambda
- `test_delete_image.py` - Tests for deleting images Lambda

## Coverage Report

See [TEST_COVERAGE_REPORT.md](TEST_COVERAGE_REPORT.md) for detailed coverage information.

## Requirements

Tests use the virtual environment at `../.venv/` which includes:
- pytest
- pytest-cov
- boto3
- moto (for AWS mocking)
