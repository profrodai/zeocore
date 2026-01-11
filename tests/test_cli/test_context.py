# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_cli/test_context.py
# role: tests
# neighbors: __init__.py, mocks.py, test_bootstrap.py, test_config.py, test_error.py, test_formatting.py (+5 more)
# exports: TestQuackContext
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===

"""
Tests for the CLI context module.
"""

import logging
import os
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from quack_core.config.models import QuackConfig
from quack_core.interfaces.cli.legacy.context import QuackContext


class TestQuackContext:
    """Tests for the QuackContext class."""

    def test_initialization(self) -> None:
        """Test initializing the QuackContext."""
        # Create basic dependencies
        config = QuackConfig()
        logger = logging.getLogger("test_quack_context")
        base_dir = "/test/base_dir"

        # Test with required parameters
        context = QuackContext(
            config=config,
            logger=logger,
            base_dir=base_dir,
            environment="development",
        )

        assert context.config is config
        assert context.logger is logger
        assert context.base_dir == base_dir
        assert context.environment == "development"
        assert context.debug is False  # Default
        assert context.verbose is False  # Default
        assert context.working_dir == os.getcwd()  # Default - Changed from Path.cwd()
        assert context.extra == {}  # Default

        # Test with all parameters
        working_dir = "/test/working_dir"
        extra = {"key": "value"}

        context = QuackContext(
            config=config,
            logger=logger,
            base_dir=base_dir,
            environment="test",
            debug=True,
            verbose=True,
            working_dir=working_dir,
            extra=extra,
        )

        assert context.environment == "test"
        assert context.debug is True
        assert context.verbose is True
        assert context.working_dir == working_dir
        assert context.extra == extra

    def test_model_validation(self) -> None:
        """Test that model validates inputs."""
        config = QuackConfig()
        logger = logging.getLogger("test_validation")

        # Test with invalid logger type
        with pytest.raises(ValidationError):
            QuackContext(
                config=config,
                logger="not_a_logger",  # type: ignore
                base_dir="/test",
                environment="development",
            )

        # Test with invalid environment
        with pytest.raises(ValidationError):
            QuackContext(
                config=config,
                logger=logger,
                base_dir="/test",
                environment=123,  # type: ignore
            )

    def test_frozen_model(self) -> None:
        """Test that the model is frozen (immutable)."""
        config = QuackConfig()
        logger = logging.getLogger("test_frozen")

        context = QuackContext(
            config=config,
            logger=logger,
            base_dir="/test",
            environment="development",
        )

        # Verify we can't modify attributes
        with pytest.raises(Exception):
            context.debug = True

        # Verify we can't add new attributes
        with pytest.raises(Exception):
            context.new_attr = "value"  # type: ignore

    def test_arbitrary_types_allowed(self) -> None:
        """Test that arbitrary types like Logger are allowed."""
        config = QuackConfig()

        # Create a mock logger
        logger = MagicMock(spec=logging.Logger)

        # This should not raise an error
        context = QuackContext(
            config=config,
            logger=logger,
            base_dir="/test",
            environment="development",
        )

        assert context.logger is logger

    def test_with_extra(self) -> None:
        """Test the with_extra method."""
        config = QuackConfig()
        logger = logging.getLogger("test_with_extra")

        context = QuackContext(
            config=config,
            logger=logger,
            base_dir="/test",
            environment="development",
            extra={"existing": "value"},
        )

        # Add more extra data
        new_context = context.with_extra(new_key="new_value", another_key=123)

        # Verify original is unchanged
        assert context.extra == {"existing": "value"}

        # Verify new context has updated extra dict
        assert new_context.extra == {
            "existing": "value",
            "new_key": "new_value",
            "another_key": 123,
        }

        # Verify all other attributes are the same
        assert new_context.config is context.config
        assert new_context.logger is context.logger
        assert new_context.base_dir == context.base_dir
        assert new_context.environment == context.environment
        assert new_context.debug == context.debug
        assert new_context.verbose == context.verbose
        assert new_context.working_dir == context.working_dir

        # Test with overlapping keys (should update)
        overlap_context = context.with_extra(existing="updated")
        assert overlap_context.extra == {"existing": "updated"}
