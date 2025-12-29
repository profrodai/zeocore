# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_cli/mocks.py
# role: tests
# neighbors: __init__.py, test_bootstrap.py, test_config.py, test_context.py, test_error.py, test_formatting.py (+5 more)
# exports: MockConfig, create_mock_logger, create_mock_logger_factory, patch_common_dependencies
# git_branch: refactor/toolkitWorkflow
# git_commit: 7e3e554
# === QV-LLM:END ===

"""
Common mock objects and utilities for testing CLI modules.

This module provides reusable mock classes and functions for testing
the QuackCore CLI components. Centralizing these mocks ensures consistency
across all test modules and makes tests more maintainable.
"""

from unittest.mock import MagicMock, patch

from quack_core.config.models import QuackConfig


class MockConfig(QuackConfig):
    """
    Mock configuration class for testing that inherits from QuackConfig.

    This provides a standard mock implementation that can be used across test modules,
    with easily modifiable attributes that match the QuackConfig structure.
    """

    def __init__(self, debug=False, verbose=False):
        """
        Initialize the mock config with modifiable attributes.

        Args:
            debug: Initial value for general.debug
            verbose: Initial value for general.verbose
        """
        # Initialize the base QuackConfig
        super().__init__()

        # Override the values we want to customize
        self.general.debug = debug
        self.general.verbose = verbose

        # Add commonly used test values
        self.logging.level = "INFO"
        self.logging.file = None  # Avoid filesystem errors
        self.logging.console = True

        self.paths.base_dir = "/mock/base/dir"
        self.paths.output_dir = "/mock/output/dir"


def create_mock_logger():
    """
    Create a standard mock logger.

    Returns:
        MagicMock: A configured mock logger with standard debugging methods
    """
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.critical = MagicMock()
    return logger


def create_mock_logger_factory():
    """
    Create a mock logger factory function.

    Returns:
        MagicMock: A mock function that returns a mock logger
    """
    factory = MagicMock()
    factory.return_value = create_mock_logger()
    return factory


def patch_common_dependencies(func):
    """
    Decorator to patch common dependencies for CLI tests.

    The patches are applied in the correct order and the mock objects are passed
    to the decorated function in the same order they're declared here.

    Args:
        func: The test function to decorate

    Returns:
        Decorated test function with common patches applied
    """
    # Apply patches in the correct order from innermost to outermost
    # This is important as the mocks will be passed to the function in reverse order
    setup_logging_patch = patch("quack_core.interfaces.cli.legacy.boostrap.setup_logging")
    load_config_patch = patch("quack_core.interfaces.cli.legacy.boostrap.load_config")
    find_root_patch = patch("quack_core.interfaces.cli.legacy.boostrap.find_project_root")

    # Apply decorators in the correct order
    return setup_logging_patch(load_config_patch(find_root_patch(func)))
