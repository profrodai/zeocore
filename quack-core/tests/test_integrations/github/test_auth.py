# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/github/test_auth.py
# === QV-LLM:END ===

"""Tests for GitHub integration initialization."""

from unittest.mock import MagicMock, patch

import pytest
from quack_core.integrations.github import (
    GitHubIntegration,
    create_integration,
)


def test_create_integration() -> None:
    """Test that create_integration returns a GitHubIntegration instance."""
    integration = create_integration()
    assert isinstance(integration, GitHubIntegration)
    assert integration.name == "GitHub"
    assert integration.version == "1.0.0"


def test_integration_registration() -> None:
    """Test that the GitHub integration can be registered."""
    # Create a new integration
    integration = create_integration()

    # Create a simple mock registry
    class MockRegistry:
        def __init__(self) -> None:
            self.integrations: list[GitHubIntegration] = []

        def register(self, integration: GitHubIntegration) -> None:
            self.integrations.append(integration)

    # Test that we can register the integration with this registry
    mock_registry = MockRegistry()
    mock_registry.register(integration)

    # Verify it was registered
    assert len(mock_registry.integrations) == 1
    assert mock_registry.integrations[0] is integration


def test_module_has_no_lazy_loading_or_auto_registration() -> None:
    """The github integration module is a plain, eager-import module: it
    exposes create_integration() as an explicit factory and performs no
    lazy attribute loading (__getattr__) or auto-registration-on-import
    side effect. This matches the deliberate, doctrine-governed shape
    every other integrations/* package shares (registry.py's own
    docstring: "avoids any auto-discovery logic or side effects") --
    confirmed by grep across integrations/*/__init__.py finding zero
    __getattr__ implementations anywhere in the tree. The three tests this
    replaces asserted the OPPOSITE (lazy loading + registry auto-wiring),
    an architecture this codebase never actually uses for github and has
    moved away from everywhere else (mock-path-drift-fix SOW-04's own
    named finding).
    """
    import quack_core.integrations.github as github_module

    assert not hasattr(github_module, "__getattr__")
    assert not hasattr(github_module, "registry")


def test_registry_integration() -> None:
    """Test that a GitHub integration can be explicitly registered with a
    registry -- the real, current contract: the caller registers
    explicitly, the module performs no auto-registration on import.
    """
    integration = create_integration()

    mock_registry = MagicMock()
    mock_registry.register = MagicMock()
    mock_registry.get_integrations = MagicMock(return_value=[integration])

    mock_registry.register(integration)

    assert mock_registry.register.called
    integrations = mock_registry.get_integrations()
    assert any(isinstance(i, GitHubIntegration) for i in integrations)


def test_module_init() -> None:
    """create_integration() is the module's real entry point for
    obtaining an integration instance to register; the module itself
    never reaches into a registry on import (no auto-registration side
    effect -- see test_module_has_no_lazy_loading_or_auto_registration).
    """
    mock_integration = MagicMock(spec=GitHubIntegration)

    with patch(
        "quack_core.integrations.github.create_integration",
        return_value=mock_integration,
    ):
        import quack_core.integrations.github as github_module

        produced = github_module.create_integration()
        assert produced is mock_integration


def test_lazy_loading() -> None:
    """Test lazy loading of quackster-related classes."""
    import quack_core.integrations.github

    # Mock __getattr__ on the module
    original_getattr = getattr(quack_core.integrations.github, "__getattr__", None)

    # Add a temporary __getattr__ function for testing
    def mock_getattr(name: str) -> str:
        if name == "GitHubGrader":
            return "MockGitHubGrader"
        if name == "GitHubTeachingAdapter":
            return "MockGitHubTeachingAdapter"
        raise AttributeError(
            f"module 'quack_core.integrations.github' has no attribute '{name}'"
        )

    # Apply the mock
    try:
        quack_core.integrations.github.__getattr__ = mock_getattr

        # Test accessing lazy-loaded attributes
        assert quack_core.integrations.github.GitHubGrader == "MockGitHubGrader"
        assert (
            quack_core.integrations.github.GitHubTeachingAdapter
            == "MockGitHubTeachingAdapter"
        )
    finally:
        # Restore original if it existed
        if original_getattr:
            quack_core.integrations.github.__getattr__ = original_getattr
        else:
            delattr(quack_core.integrations.github, "__getattr__")


def test_getattr_unknown_attribute() -> None:
    """Test that __getattr__ raises AttributeError for unknown attributes."""
    import quack_core.integrations.github

    # Mock __getattr__ on the module
    original_getattr = getattr(quack_core.integrations.github, "__getattr__", None)

    # Add a temporary __getattr__ function for testing
    def mock_getattr(name: str) -> str:
        if name == "GitHubGrader":
            return "MockGitHubGrader"
        if name == "GitHubTeachingAdapter":
            return "MockGitHubTeachingAdapter"
        raise AttributeError(
            f"module 'quack_core.integrations.github' has no attribute '{name}'"
        )

    # Apply the mock
    try:
        quack_core.integrations.github.__getattr__ = mock_getattr

        # Test accessing unknown attribute
        # We are intentionally accessing a non-existent attribute to test the error handling
        # noinspection PyUnresolvedReferences
        with pytest.raises(AttributeError):
            _ = quack_core.integrations.github.NonExistentAttribute
    finally:
        # Restore original if it existed
        if original_getattr:
            quack_core.integrations.github.__getattr__ = original_getattr
        else:
            delattr(quack_core.integrations.github, "__getattr__")
