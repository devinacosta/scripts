# 🧪 Testing Guide for escmd

This document provides comprehensive guidance for testing the escmd CLI tool after the recent refactoring to ensure all functionality remains intact.

## 📋 Overview

The testing strategy includes:
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test end-to-end CLI functionality
- **Configuration Tests**: Test configuration loading and validation
- **Mocking Strategy**: Mock Elasticsearch connections for reliable testing

## 🚀 Quick Start

### 1. Install Test Dependencies

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Or use the test runner
./run_tests.sh install
```

### 2. Run All Tests

```bash
# Run all tests
./run_tests.sh

# Or directly with pytest
pytest
```

### 3. Run Specific Test Types

```bash
# Unit tests only
./run_tests.sh unit

# Integration tests only
./run_tests.sh integration

# With coverage report
./run_tests.sh coverage
```

## 🏗️ Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── unit/                       # Unit tests
│   ├── test_command_handler.py # Command routing tests
│   ├── test_health_handler.py  # Health handler tests
│   └── test_configuration.py   # Configuration tests
├── integration/                # Integration tests
│   └── test_cli_integration.py # End-to-end CLI tests
└── fixtures/                   # Test data files
```

## 🎯 What We Test

### 1. Command Routing (`test_command_handler.py`)

Tests that verify the refactored command routing works correctly:

```python
def test_command_routing_health(self, command_handler):
    """Test that health command routes to health handler."""
    command_handler.args.command = 'health'
    
    with patch.object(command_handler.handlers['health'], 'handle_health') as mock_method:
        command_handler.execute()
        mock_method.assert_called_once()
```

**Why Important**: Ensures our refactoring didn't break the core routing logic.

### 2. Handler Functionality (`test_health_handler.py`)

Tests individual handler methods with mocked ES client:

```python
def test_handle_ping_success(self, health_handler, mock_es_client):
    """Test successful ping command."""
    mock_es_client.test_connection.return_value = True
    mock_es_client.get_cluster_health.return_value = {...}
    
    health_handler.handle_ping()
    
    mock_es_client.test_connection.assert_called_once()
```

**Why Important**: Verifies that each handler method works correctly in isolation.

### 3. Configuration Management (`test_configuration.py`)

Tests configuration loading and validation:

```python
def test_load_valid_yaml_config(self, temp_config_file):
    """Test loading a valid YAML configuration file."""
    config_manager = ConfigurationManager(config_file=temp_config_file)
    
    assert config_manager.config is not None
    assert 'test-cluster' in config_manager.config
```

**Why Important**: Ensures configuration handling works correctly across refactoring.

### 4. End-to-End CLI (`test_cli_integration.py`)

Tests the complete CLI workflow:

```python
@patch('esclient.ElasticsearchClient')
def test_health_command_json_output(self, mock_es_class, cli_env):
    """Test health command with JSON output."""
    result = self.run_escmd_command(['health', '-l', 'test-cluster', '--format', 'json'])
    
    assert result.returncode == 0
    output_data = json.loads(result.stdout.strip())
    assert output_data['cluster_name'] == 'test-cluster'
```

**Why Important**: Verifies the complete user experience works end-to-end.

## 🎭 Mocking Strategy

### Elasticsearch Client Mocking

We mock the `ElasticsearchClient` to avoid requiring actual Elasticsearch connections:

```python
@pytest.fixture
def mock_es_client():
    """Mock Elasticsearch client with common methods."""
    client = Mock()
    client.get_cluster_health.return_value = {
        'cluster_name': 'test-cluster',
        'status': 'green',
        'number_of_nodes': 3
    }
    return client
```

### Benefits:
- ✅ **Fast**: No network calls
- ✅ **Reliable**: No external dependencies
- ✅ **Predictable**: Controlled responses
- ✅ **Isolated**: Test specific functionality

## 📊 Test Coverage

### Current Coverage Areas

1. **Command Routing**: All 26 commands tested
2. **Handler Methods**: Key handlers (health, index, configuration)
3. **Configuration**: YAML/JSON loading, validation
4. **CLI Integration**: End-to-end command execution
5. **Error Handling**: Invalid commands, missing configs

### Priority Test Cases

| Component | Priority | Coverage |
|-----------|----------|----------|
| Command Routing | 🔴 Critical | ✅ Complete |
| Health Handler | 🔴 Critical | ✅ Complete |
| Index Handler | 🟡 High | ⏳ Planned |
| Configuration | 🟡 High | ✅ Complete |
| CLI Integration | 🟡 High | ✅ Complete |

## 🔧 Running Tests

### Basic Commands

```bash
# All tests
pytest

# Verbose output
pytest -v

# Specific test file
pytest tests/unit/test_command_handler.py

# Specific test method
pytest tests/unit/test_command_handler.py::TestCommandHandler::test_command_routing_health

# Run tests matching pattern
pytest -k "test_health"
```

### Using Test Runner Script

```bash
# Install dependencies
./run_tests.sh install

# Run all tests
./run_tests.sh all

# Unit tests only
./run_tests.sh unit

# Integration tests only
./run_tests.sh integration

# With coverage
./run_tests.sh coverage

# Specific test file
./run_tests.sh specific tests/unit/test_health_handler.py

# Clean artifacts
./run_tests.sh clean
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html

# View in browser
open htmlcov/index.html
```

## 🐛 Debugging Tests

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Mock Setup**: Verify mock return values match expected types
3. **Path Issues**: Check that file paths in tests are correct
4. **Configuration**: Ensure test fixtures create valid configs

### Debug Tips

```bash
# Run with pdb debugger
pytest --pdb

# Show print statements
pytest -s

# Run single test with debug
pytest tests/unit/test_command_handler.py::TestCommandHandler::test_command_routing_health -s -v
```

## 📝 Writing New Tests

### Test Naming Conventions

- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

### Example Test Template

```python
def test_new_functionality(self, fixture_name):
    """Test description of what this test verifies."""
    # Arrange: Set up test data and mocks
    mock_object.method.return_value = expected_value
    
    # Act: Execute the functionality
    result = object_under_test.method()
    
    # Assert: Verify the results
    assert result == expected_result
    mock_object.method.assert_called_once()
```

### Best Practices

1. **Use descriptive test names**: `test_health_command_with_json_format`
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **Mock external dependencies**: Elasticsearch, file system, etc.
4. **Test both success and failure cases**
5. **Use fixtures for common setup**

## ✅ Testing Checklist

After making changes to escmd, run this checklist:

- [ ] All unit tests pass: `./run_tests.sh unit`
- [ ] All integration tests pass: `./run_tests.sh integration`
- [ ] Coverage remains high: `./run_tests.sh coverage`
- [ ] No new linting errors
- [ ] Manual testing of changed commands
- [ ] Configuration loading still works
- [ ] Error handling still works

## 🚀 Continuous Testing

### Pre-commit Testing

```bash
# Add to your workflow
./run_tests.sh unit && ./run_tests.sh integration
```

### Testing New Handler

When adding a new handler:

1. Add unit tests for the handler methods
2. Add the handler to command routing tests
3. Add integration tests for CLI commands
4. Update fixtures if needed

## 🎯 Why These Tests Matter

After our refactoring from a monolithic `command_handler.py` to specialized handlers:

1. **Prevents Regressions**: Ensures refactoring didn't break functionality
2. **Validates Architecture**: Confirms new handler-based design works
3. **Enables Confidence**: Makes future changes safer
4. **Documents Behavior**: Tests serve as executable documentation
5. **Facilitates Maintenance**: Makes code easier to modify and extend

## 📈 Future Improvements

### Planned Enhancements

1. **More Handler Tests**: Add tests for remaining handlers
2. **Performance Tests**: Measure command execution time
3. **Error Scenario Tests**: More comprehensive error handling
4. **Configuration Validation**: Deeper config validation tests
5. **CLI Argument Tests**: Test argument parsing edge cases

### Contributing Tests

When adding new features:
- Write tests first (TDD approach)
- Ensure good coverage (>80%)
- Include both success and failure cases
- Document complex test scenarios

This comprehensive testing strategy ensures that our refactored escmd tool maintains all its functionality while being more maintainable and reliable! 🎉
