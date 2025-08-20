# QuackCore Tests

This directory contains comprehensive tests for the QuackCore library. 
These tests ensure that all components work correctly in isolation and together as a system.

## Running Tests

Tests can be run using the following command from the project root:

```bash
make test
```

This will execute all tests with coverage reporting. To run specific tests, you can use pytest directly:

```bash
python -m pytest tests/test_fs
```

## Test Structure

The tests are organized by module:

- `test_errors/`: Tests for error handling classes and utilities
- `test_fs/`: Tests for filesystem operations
- `test_paths/`: Tests for path resolution
- `test_config/`: Tests for configuration management
- `test_cli/`: Test the cli hooks
- `test_plugins/`: Tests for plugin system
- `test_integration/`: Integration tests for full pipelines
- `test_integrations/`: Test integrations such as Google Drive, Github, GMail and others

and more, for an overview, here is the full structure:

```bash
└── tests
    ├── __init__.py
    ├── conftest.py
    ├── README.md
    ├── test_cli
    │   ├── __init__.py
    │   ├── mocks.py
    │   ├── test_bootstrap.py
    │   ├── test_config.py
    │   ├── test_context.py
    │   ├── test_error.py
    │   ├── test_formatting.py
    │   ├── test_interaction.py
    │   ├── test_logging.py
    │   ├── test_options.py
    │   ├── test_progress.py
    │   └── test_terminal.py
    ├── test_config
    │   ├── __init__.py
    │   ├── test_loader.py
    │   ├── test_models.py
    │   └── test_utils.py
    ├── test_errors
    │   ├── __init__.py
    │   ├── test_base.py
    │   └── test_handlers.py
    ├── test_fs
    │   ├── __init__.py
    │   ├── test_operations.py
    │   ├── test_results.py
    │   ├── test_service.py
    │   └── test_utils.py
    ├── test_integration
    │   ├── __init__.py
    │   └── test_full_pipeline.py
    ├── test_integrations
    │   ├── __init__.py
    │   ├── core
    │   │   ├── __init__.py
    │   │   ├── base
    │   │   │   ├── __init__.py
    │   │   │   ├── auth_provider_impl.py
    │   │   │   ├── config_provider_impl.py
    │   │   │   ├── integration_service_impl.py
    │   │   │   ├── test_auth_provider.py
    │   │   │   ├── test_base.py
    │   │   │   ├── test_config_provider_discovery.py
    │   │   │   ├── test_config_provider.py
    │   │   │   ├── test_integration_service.py
    │   │   │   └── test_protocols.py
    │   │   ├── test_protocol_inheritance.py
    │   │   ├── test_protocols.py
    │   │   ├── test_registry_discovery.py
    │   │   ├── test_registry.py
    │   │   └── test_results.py
    │   ├── github
    │   │   └── __init__.py
    │   ├── google
    │   │   ├── __init__.py
    │   │   ├── drive
    │   │   │   ├── __init__.py
    │   │   │   ├── mocks
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── base.py
    │   │   │   │   ├── credentials.py
    │   │   │   │   ├── download.py
    │   │   │   │   ├── media.py
    │   │   │   │   ├── requests.py
    │   │   │   │   ├── resources.py
    │   │   │   │   └── services.py
    │   │   │   ├── mocks.py
    │   │   │   ├── _operations
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_operations_download.py
    │   │   │   │   ├── test_operations_folder.py
    │   │   │   │   ├── test_operations_list_files.py
    │   │   │   │   ├── test_operations_permissions.py
    │   │   │   │   └── test_operations_upload.py
    │   │   │   ├── test_drive_models.py
    │   │   │   ├── test_drive_service_delete.py
    │   │   │   ├── test_drive_service_download.py
    │   │   │   ├── test_drive_service_files.py
    │   │   │   ├── test_drive_service_folders.py
    │   │   │   ├── test_drive_service_init.py
    │   │   │   ├── test_drive_service_list.py
    │   │   │   ├── test_drive_service_permissions.py
    │   │   │   ├── test_drive_service_upload.py
    │   │   │   ├── test_drive.py
    │   │   │   ├── test_protocols.py
    │   │   │   └── api
    │   │   │       ├── __init__.py
    │   │   │       ├── test_utils_api.py
    │   │   │       └── test_utils_query.py
    │   │   ├── mail
    │   │   │   ├── __init__.py
    │   │   │   ├── mocks.py
    │   │   │   ├── _operations
    │   │   │   │   ├── __init__.py
    │   │   │   │   ├── test_attachments.py
    │   │   │   │   ├── test_auth.py
    │   │   │   │   └── test_email.py
    │   │   │   ├── test_mail_service.py
    │   │   │   ├── test_mail.py
    │   │   │   └── api
    │   │   │       ├── __init__.py
    │   │   │       └── test_api.py
    │   │   ├── mocks.py
    │   │   ├── test_auth_provider.py
    │   │   ├── test_config_provider.py
    │   │   └── test_serialization.py
    │   ├── llms
    │   │   ├── __init__.py
    │   │   ├── clients
    │   │   │   ├── __init__.py
    │   │   │   ├── test_anthropic.py
    │   │   │   ├── test_base.py
    │   │   │   ├── test_clients.py
    │   │   │   ├── test_mock.py
    │   │   │   ├── test_ollama.py
    │   │   │   └── test_openai.py
    │   │   ├── mocks
    │   │   │   ├── __init__.py
    │   │   │   ├── anthropic.py
    │   │   │   ├── base.py
    │   │   │   ├── clients.py
    │   │   │   └── openai.py
    │   │   ├── service
    │   │   │   ├── __init__.py
    │   │   │   ├── test_dependencies.py
    │   │   │   ├── test_initialization.py
    │   │   │   ├── test_integration.py
    │   │   │   └── test_operations.py
    │   │   ├── test_config_provider.py
    │   │   ├── test_config.py
    │   │   ├── test_fallback.py
    │   │   ├── test_integration.py
    │   │   ├── test_llms.py
    │   │   ├── test_models.py
    │   │   ├── test_protocols.py
    │   │   ├── test_registry.py
    │   │   └── test_service.py
    │   └── pandoc
    │       ├── __init__.py
    │       ├── mocks.py
    │       ├── _operations
    │       │   ├── __init__.py
    │       │   ├── test_html_to_md.py
    │       │   ├── test_md_to_docx.py
    │       │   └── test_utils.py
    │       ├── test_config.py
    │       ├── test_converter.py
    │       ├── test_models.py
    │       ├── test_operations.py
    │       ├── test_pandoc_integration.py
    │       └── test_service.py
    ├── test_paths
    │   ├── __init__.py
    │   ├── test_context.py
    │   ├── test_resolvers.py
    │   └── test_utils.py
    ├── test_plugins
    │   ├── __init__.py
    │   ├── test_discovery.py
    │   ├── test_protocols.py
    │   └── test_registry.py
    ├── test_prompt
    │   └── __init__.py
    └── quackster
        ├── __init__.py
        ├── test_academy
        │   ├── __init__.py
        │   ├── conftest.py
        │   ├── test_assignment.py
        │   ├── test_context.py
        │   ├── test_course.py
        │   ├── test_feedback.py
        │   ├── test_init.py
        │   ├── test_plugin.py
        │   ├── test_results.py
        │   ├── test_service.py
        │   └── test_student.py
        ├── test_core
        │   ├── __init__.py
        │   ├── test_badges.py
        │   ├── test_certificates.py
        │   ├── test_github_api.py
        │   ├── test_models.py
        │   ├── test_quests.py
        │   ├── test_utils.py
        │   └── test_xp.py
        ├── test_gamification
        │   ├── __init__.py
        │   ├── test_badges.py
        │   ├── test_base.py
        │   ├── test_events.py
        │   ├── test_quests.py
        │   └── test_service.py
        ├── test_github
        │   ├── __init__.py
        │   ├── test_grading.py
        │   ├── test_teaching_adapter.py
        │   └── test_teaching_service.py
        └── test_npc
            ├── __init__.py
            ├── test_dialogue.py
            ├── test_memory.py
            ├── test_persona.py
            └── test_tools
                ├── __init__.py
                ├── conftest.py
                ├── test_badge_tools.py
                ├── test_certificate_tools.py
                ├── test_common.py
                ├── test_init.py
                ├── test_progress_tools.py
                ├── test_quest_tools.py
                ├── test_schema.py
                ├── test_tutorial_tools.py
                └── test_utils.py
```

## Creating New Tests

When creating new tests, please follow these guidelines:

1. Use appropriate pytest fixtures from `conftest.py`
2. Test both success and failure cases
3. Follow the pattern of existing tests for similar components
4. Use hypothesis for property-based testing where appropriate
5. Keep tests isolated and avoid side effects
6. Mock as much as possible with dedicated mock classes

## Mocks and Fixtures

Common testing utilities are provided in `conftest.py`:

- `temp_dir`: Creates a temporary directory for tests
- `test_file`: Creates a test file with content
- `sample_config`: Creates a sample configuration
- `mock_project_structure`: Creates a mock project structure
- `mock_plugin`: Creates a mock plugin for testing

## Coverage Goals

The goal is to maintain at least 90% test coverage for all modules. 
Coverage reports are generated when running tests with `make test`.