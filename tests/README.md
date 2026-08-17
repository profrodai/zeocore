# ZeoCore Tests

This directory contains comprehensive tests for the ZeoCore library. 
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

The tests are organized by module, mirroring `src/zeo_core/`:

- `test_adapters/`: Tests for the HTTP adapter
- `test_cli/`: Reserved for CLI hooks (no `zeo_core.cli` module exists yet)
- `test_config/`: Tests for configuration management
- `test_contracts/`: Tests for the data contracts (`CapabilityResult`, artifacts, envelopes)
- `test_core/`: Tests for core utilities (MIME detection, logging, registry, serialization)
- `test_dev/`: Tests for local dev-only tooling
- `test_errors/`: Tests for error handling classes and utilities
- `test_fs/`: Tests for filesystem operations
- `test_http/`: Tests for the HTTP adapter's routes/auth/jobs
- `test_integration/`: Integration tests for full pipelines
- `test_integrations/`: Tests for integrations such as Google Drive, Gmail, GitHub, LLMs, and Pandoc
- `test_paths/`: Tests for path resolution
- `test_plugins/`: Tests for the plugin system
- `test_prompt/`: Tests for prompt template selection/enhancement
- `test_tools/`: Tests for the `zeo_core.tools` capability-authoring framework

For the full, current structure, run `tree tests` (or `make structure-tree`)
from the repo root -- the tree below is a snapshot and can drift from disk
as tests are added, so treat it as illustrative, not authoritative:

```bash
tests
├── test_adapters
│   ├── __init__.py
│   └── test_http_adapter.py
├── test_cli
│   └── __init__.py
├── test_config
│   ├── __init__.py
│   ├── test_config_base.py
│   ├── test_config_plugin.py
│   ├── test_loader.py
│   ├── test_models.py
│   └── test_utils.py
├── test_contracts
│   ├── fixtures
│   │   ├── artifact_ref_local.json
│   │   ├── artifact_ref_s3.json
│   │   ├── manifest_error.json
│   │   └── manifest_success.json
│   ├── __init__.py
│   ├── test_artifacts.py
│   ├── test_capabilities.py
│   ├── test_dependency_boundaries.py
│   ├── test_envelopes.py
│   └── test_schema_examples.py
├── test_core
│   ├── test_logging
│   │   ├── __init__.py
│   │   └── test_config.py
│   ├── __init__.py
│   ├── test_mime.py
│   ├── test_registry.py
│   └── test_serialization.py
├── test_dev
│   ├── __init__.py
│   └── test_run_local.py
├── test_errors
│   ├── __init__.py
│   ├── test_base.py
│   └── test_handlers.py
├── test_fs
│   ├── __init__.py
│   ├── test_api_surface.py
│   ├── test_architecture.py
│   ├── test_atomic_wrapping.py
│   ├── test_operations.py
│   ├── test_path_utils.py
│   ├── test_results.py
│   ├── test_service_mixins_cluster.py
│   ├── test_service.py
│   ├── test_standalone.py
│   ├── test_suite.py
│   ├── test_utility_operations.py
│   └── test_utils.py
├── test_http
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_config.py
│   ├── test_integration.py
│   ├── test_jobs.py
│   ├── test_routes_jobs.py
│   ├── test_routes_zeomedia.py
│   └── test_util.py
├── test_integration
│   ├── __init__.py
│   └── test_full_pipeline.py
├── test_integrations
│   ├── core
│   │   ├── base
│   │   │   ├── __init__.py
│   │   │   ├── auth_provider_impl.py
│   │   │   ├── config_provider_impl.py
│   │   │   ├── integration_service_impl.py
│   │   │   ├── test_auth_provider.py
│   │   │   ├── test_base.py
│   │   │   ├── test_config_provider_discovery.py
│   │   │   ├── test_config_provider.py
│   │   │   ├── test_integration_service.py
│   │   │   └── test_protocols.py
│   │   ├── __init__.py
│   │   ├── test_get_service.py
│   │   ├── test_protocol_inheritance.py
│   │   ├── test_protocols.py
│   │   ├── test_registry.py
│   │   └── test_results.py
│   ├── github
│   │   ├── operations
│   │   │   └── __init__.py
│   │   ├── utils
│   │   │   └── __init__.py
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_api.py
│   │   ├── test_auth_provider.py
│   │   ├── test_auth.py
│   │   ├── test_client.py
│   │   ├── test_config.py
│   │   ├── test_github_init.py
│   │   ├── test_integration.py
│   │   ├── test_models.py
│   │   ├── test_operations.py
│   │   ├── test_protocols.py
│   │   └── test_service.py
│   ├── google
│   │   ├── drive
│   │   │   ├── mocks
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── credentials.py
│   │   │   │   ├── download.py
│   │   │   │   ├── media.py
│   │   │   │   ├── requests.py
│   │   │   │   ├── resources.py
│   │   │   │   └── services.py
│   │   │   ├── operations
│   │   │   │   ├── __init__.py
│   │   │   │   ├── test_operations_download.py
│   │   │   │   ├── test_operations_folder.py
│   │   │   │   ├── test_operations_list_files.py
│   │   │   │   ├── test_operations_permissions.py
│   │   │   │   ├── test_operations_resolve_project_path_real_bug.py
│   │   │   │   ├── test_operations_upload_mime_type_real_bug.py
│   │   │   │   └── test_operations_upload.py
│   │   │   ├── utils
│   │   │   │   ├── __init__.py
│   │   │   │   ├── test_utils_api.py
│   │   │   │   └── test_utils_query.py
│   │   │   ├── __init__.py
│   │   │   ├── mocks.py
│   │   │   ├── test_drive_models.py
│   │   │   ├── test_drive_service_delete.py
│   │   │   ├── test_drive_service_download.py
│   │   │   ├── test_drive_service_error_paths.py
│   │   │   ├── test_drive_service_files.py
│   │   │   ├── test_drive_service_folders.py
│   │   │   ├── test_drive_service_init.py
│   │   │   ├── test_drive_service_list.py
│   │   │   ├── test_drive_service_permissions.py
│   │   │   ├── test_drive_service_upload.py
│   │   │   ├── test_drive.py
│   │   │   └── test_protocols.py
│   │   ├── mail
│   │   │   ├── operations
│   │   │   │   ├── __init__.py
│   │   │   │   ├── test_attachments.py
│   │   │   │   ├── test_auth.py
│   │   │   │   ├── test_email_message_parts.py
│   │   │   │   ├── test_email.py
│   │   │   │   └── test_handle_attachment_split_path_real_bug.py
│   │   │   ├── utils
│   │   │   │   ├── __init__.py
│   │   │   │   └── test_api.py
│   │   │   ├── __init__.py
│   │   │   ├── mocks.py
│   │   │   ├── test_mail_service.py
│   │   │   └── test_mail.py
│   │   ├── __init__.py
│   │   ├── mocks.py
│   │   ├── test_auth_provider.py
│   │   ├── test_config_provider.py
│   │   └── test_serialization.py
│   ├── llms
│   │   ├── clients
│   │   │   ├── __init__.py
│   │   │   ├── test_anthropic.py
│   │   │   ├── test_base.py
│   │   │   ├── test_clients.py
│   │   │   ├── test_mock.py
│   │   │   ├── test_ollama.py
│   │   │   └── test_openai.py
│   │   ├── mocks
│   │   │   ├── __init__.py
│   │   │   ├── anthropic.py
│   │   │   ├── base.py
│   │   │   ├── clients.py
│   │   │   └── openai.py
│   │   ├── service
│   │   │   ├── __init__.py
│   │   │   ├── test_dependencies.py
│   │   │   ├── test_init_module.py
│   │   │   ├── test_initialization.py
│   │   │   ├── test_integration.py
│   │   │   └── test_operations.py
│   │   ├── __init__.py
│   │   ├── test_config_provider.py
│   │   ├── test_config.py
│   │   ├── test_fallback.py
│   │   ├── test_integration.py
│   │   ├── test_llms.py
│   │   ├── test_models.py
│   │   ├── test_protocols.py
│   │   ├── test_registry.py
│   │   └── test_service.py
│   ├── pandoc
│   │   ├── operations
│   │   │   ├── __init__.py
│   │   │   ├── test_html_to_md.py
│   │   │   ├── test_md_to_docx.py
│   │   │   ├── test_utils_fix.py
│   │   │   └── test_utils.py
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── mocks.py
│   │   ├── test_config.py
│   │   ├── test_converter.py
│   │   ├── test_models.py
│   │   ├── test_pandoc_integration_edge_cases.py
│   │   ├── test_pandoc_integration_full.py
│   │   ├── test_pandoc_integration.py
│   │   ├── test_pandoc_utils.py
│   │   └── test_service.py
│   ├── __init__.py
│   └── test_loader.py
├── test_paths
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api_public_path_utils.py
│   ├── test_context.py
│   ├── test_paths_plugin.py
│   ├── test_resolvers.py
│   ├── test_service.py
│   └── test_utils.py
├── test_plugins
│   ├── __init__.py
│   ├── test_discovery.py
│   ├── test_explicit_loading.py
│   ├── test_protocols.py
│   └── test_registry.py
├── test_prompt
│   ├── __init__.py
│   ├── test_enhancer.py
│   ├── test_prompt_plugin.py
│   ├── test_prompt_smoke.py
│   ├── test_registry.py
│   ├── test_selector.py
│   ├── test_service.py
│   ├── test_strategies_core.py
│   └── test_strategy_base.py
├── test_tools
│   ├── mixins
│   │   ├── __init__.py
│   │   ├── test_env_init.py
│   │   ├── test_integration_enabled.py
│   │   └── test_lifecycle.py
│   ├── __init__.py
│   ├── conftest.py
│   ├── mocks.py
│   └── test_imports.py
├── __init__.py
├── conftest.py
├── README.md
└── test_helper.py
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