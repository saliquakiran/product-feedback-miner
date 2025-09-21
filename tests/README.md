# Product Feedback Miner - Infrastructure Tests

This directory contains comprehensive tests for the Product Feedback Miner infrastructure components.

## Test Structure

### `test_infrastructure_comprehensive.py`
The main comprehensive test file that covers all infrastructure components:

#### **Database Models (9 tests)**
- `test_raw_feedback_model` - Tests RawFeedback creation and validation
- `test_processed_document_model` - Tests ProcessedDocument and relationships
- `test_cluster_model` - Tests Cluster model creation
- `test_cluster_membership_relationship` - Tests many-to-many relationships
- `test_prioritization_score_model` - Tests PrioritizationScore model
- `test_ticket_model` - Tests Ticket model creation
- `test_agent_execution_model` - Tests AgentExecution model
- `test_system_config_model` - Tests SystemConfig model
- `test_digest_report_model` - Tests DigestReport model

#### **Configuration System (5 tests)**
- `test_config_loading_with_defaults` - Tests default configuration loading
- `test_config_loading_with_environment_variables` - Tests env var parsing
- `test_database_config_creation` - Tests DatabaseConfig dataclass
- `test_agent_config_creation` - Tests AgentConfig dataclass
- `test_boolean_parsing` - Tests boolean environment variable parsing

#### **BaseAgent Framework (8 tests)**
- `test_agent_initialization` - Tests BaseAgent initialization
- `test_config_merge` - Tests configuration merging
- `test_get_output_type` - Tests output type generation
- `test_get_input_dependencies` - Tests dependency management
- `test_create_default_context` - Tests context creation
- `test_retry_with_backoff_success` - Tests retry logic (success)
- `test_retry_with_backoff_failure` - Tests retry logic (failure)
- `test_validate_input_default` - Tests input validation
- `test_prepare_output_default` - Tests output preparation

#### **Logging System (3 tests)**
- `test_setup_logging` - Tests logging setup
- `test_get_agent_logger` - Tests agent logger creation
- `test_log_agent_execution` - Tests execution logging

#### **Monitoring System (4 tests)**
- `test_health_monitor_initialization` - Tests health monitor setup
- `test_metrics_collector_initialization` - Tests metrics collector setup
- `test_collect_system_metrics` - Tests system metrics collection
- `test_check_system_health` - Tests health checking

#### **Database Setup (2 tests)**
- `test_database_models_creation` - Tests all models can be created
- `test_database_constraints` - Tests foreign key constraints

### `run_infrastructure_tests.py`
Test runner script that executes all infrastructure tests and provides a summary.

## Running Tests

```bash
# Run all infrastructure tests
python tests/run_infrastructure_tests.py

# Run specific test file
python -m pytest tests/test_infrastructure_comprehensive.py -v

# Run specific test class
python -m pytest tests/test_infrastructure_comprehensive.py::TestDatabaseModels -v

# Run specific test method
python -m pytest tests/test_infrastructure_comprehensive.py::TestDatabaseModels::test_raw_feedback_model -v
```

## Test Coverage

The comprehensive test suite covers:

✅ **Database Models**: All 10 models with relationships and constraints
✅ **Configuration System**: Default values, environment variables, dataclasses
✅ **BaseAgent Framework**: Initialization, configuration, retry logic, validation
✅ **Logging System**: Setup, agent loggers, execution logging
✅ **Monitoring System**: Health monitoring, metrics collection
✅ **Database Setup**: Model creation, constraints, relationships

## Test Results

**32 tests passed, 0 failed** ✅

All infrastructure components are working correctly and ready for production use.

## Notes

- Tests use SQLite in-memory database for speed and isolation
- API key validation is disabled during testing
- Tests are designed to be independent and can run in any order
- All tests use proper fixtures for database setup/teardown
