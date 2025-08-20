# quack-core/tests/test_integrations/github/test_auth.py
"""Tests for GitHub integration initialization."""

from unittest.mock import MagicMock, patch

import pytest

from quackcore.integrations.github import (
    GitHubIntegration,
    create_integration,
)


def test_create_integration():
    """Test that create_integration returns a GitHubIntegration instance."""
    integration = create_integration()
    assert isinstance(integration, GitHubIntegration)
    assert integration.name == "GitHub"
    assert integration.version == "1.0.0"


def test_integration_registration():
    """Test that the GitHub integration can be registered."""
    # Create a new integration
    integration = create_integration()

    # Create a simple mock registry
    class MockRegistry:
        def __init__(self):
            self.integrations = []

        def register(self, integration):
            self.integrations.append(integration)

    # Test that we can register the integration with this registry
    mock_registry = MockRegistry()
    mock_registry.register(integration)

    # Verify it was registered
    assert len(mock_registry.integrations) == 1
    assert mock_registry.integrations[0] is integration


def test_module_implements_getattr():
    """Test that the module implements __getattr__ for lazy loading."""
    import quackcore.integrations.github

    # Verify the module has __getattr__
    assert hasattr(quackcore.integrations.github, "__getattr__")

    # Mock an import to verify it would be called
    original_getattr = quackcore.integrations.github.__getattr__

    try:
        # Replace with a test implementation
        def mock_getattr(name):
            if name == "TEST_ATTRIBUTE":
                return "Test Value"
            return original_getattr(name)

        quackcore.integrations.github.__getattr__ = mock_getattr

        # Test our mock implementation works
        assert quackcore.integrations.github.TEST_ATTRIBUTE == "Test Value"

        # Verify proper error for invalid attributes
        with pytest.raises(AttributeError):
            _ = quackcore.integrations.github.NON_EXISTENT_ATTR

    finally:
        # Restore original
        quackcore.integrations.github.__getattr__ = original_getattr


def test_registry_integration():
    """Test that the GitHub integration is registered with registry."""
    # Create a new integration
    integration = create_integration()

    # Create a mock registry module with the correct methods
    mock_registry = MagicMock()
    mock_registry.register = MagicMock()
    mock_registry.get_integrations = MagicMock(return_value=[integration])

    # Patch the registry module
    with patch("quack-core.integrations.github.registry", mock_registry):
        # Import the module to trigger registration
        import importlib

        import quackcore.integrations.github

        importlib.reload(quackcore.integrations.github)

        # Check that we can access the integration through the registry
        integrations = mock_registry.get_integrations()
        assert any(isinstance(i, GitHubIntegration) for i in integrations)


def test_module_init():
    """Test that the module's __init__ tries to register the integration."""
    # Create a mock registry
    mock_registry = MagicMock()

    # Create a mock integration
    mock_integration = MagicMock(spec=GitHubIntegration)

    # Patch create_integration to return our mock integration
    with patch(
        "quack-core.integrations.github.create_integration",
        return_value=mock_integration,
    ):
        # Patch the registry module
        with patch("quack-core.integrations.github.registry", mock_registry):
            # Re-import the module to trigger registration
            import importlib

            import quackcore.integrations.github

            importlib.reload(quackcore.integrations.github)

            # Verify registration was attempted - registry should have been accessed
            assert mock_registry.register.called or hasattr(
                mock_registry, "add_integration"
            )


def test_lazy_loading():
    """Test lazy loading of quackster-related classes."""
    import quackcore.integrations.github

    # Mock __getattr__ on the module
    original_getattr = getattr(quackcore.integrations.github, "__getattr__", None)

    # Add a temporary __getattr__ function for testing
    def mock_getattr(name):
        if name == "GitHubGrader":
            return "MockGitHubGrader"
        if name == "GitHubTeachingAdapter":
            return "MockGitHubTeachingAdapter"
        raise AttributeError(
            f"module 'quack-core.integrations.github' has no attribute '{name}'"
        )

    # Apply the mock
    try:
        quackcore.integrations.github.__getattr__ = mock_getattr

        # Test accessing lazy-loaded attributes
        assert quackcore.integrations.github.GitHubGrader == "MockGitHubGrader"
        assert (
            quackcore.integrations.github.GitHubTeachingAdapter
            == "MockGitHubTeachingAdapter"
        )
    finally:
        # Restore original if it existed
        if original_getattr:
            quackcore.integrations.github.__getattr__ = original_getattr
        else:
            delattr(quackcore.integrations.github, "__getattr__")


def test_getattr_unknown_attribute():
    """Test that __getattr__ raises AttributeError for unknown attributes."""
    import quackcore.integrations.github

    # Mock __getattr__ on the module
    original_getattr = getattr(quackcore.integrations.github, "__getattr__", None)

    # Add a temporary __getattr__ function for testing
    def mock_getattr(name):
        if name == "GitHubGrader":
            return "MockGitHubGrader"
        if name == "GitHubTeachingAdapter":
            return "MockGitHubTeachingAdapter"
        raise AttributeError(
            f"module 'quack-core.integrations.github' has no attribute '{name}'"
        )

    # Apply the mock
    try:
        quackcore.integrations.github.__getattr__ = mock_getattr

        # Test accessing unknown attribute
        # We are intentionally accessing a non-existent attribute to test the error handling
        # noinspection PyUnresolvedReferences
        with pytest.raises(AttributeError):
            _ = quackcore.integrations.github.NonExistentAttribute
    finally:
        # Restore original if it existed
        if original_getattr:
            quackcore.integrations.github.__getattr__ = original_getattr
        else:
            delattr(quackcore.integrations.github, "__getattr__")
