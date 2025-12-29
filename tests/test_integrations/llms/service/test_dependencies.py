# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/llms/service/test_dependencies.py
# role: service
# neighbors: __init__.py, test_initialization.py, test_integration.py, test_operations.py
# exports: TestDependencies
# git_branch: refactor/toolkitWorkflow
# git_commit: 21647d6
# === QV-LLM:END ===

from unittest.mock import MagicMock, patch

from quack_core.integrations.llms.service.dependencies import check_llm_dependencies


class TestDependencies:
    """Tests for dependency checking functions."""

    def test_check_llm_dependencies_all_available(self) -> None:
        """Test dependency checking with all providers available."""
        with patch(
            "importlib.util.find_spec", return_value=MagicMock()
        ) as mock_find_spec:
            # Also mock the requests.get for Ollama server check
            with patch(
                "requests.get", return_value=MagicMock(status_code=200)
            ) as mock_get:
                success, message, providers = check_llm_dependencies()

                assert success is True
                assert "Available LLM providers:" in message
                assert set(providers) == {"openai", "anthropic", "ollama", "mock"}

                # Verify find_spec was called for each provider package
                assert mock_find_spec.call_count >= 3

                # Verify requests.get was called for Ollama
                mock_get.assert_called_once_with(
                    "http://localhost:11434/api/version", timeout=1
                )

    def test_check_llm_dependencies_some_missing(self) -> None:
        """Test dependency checking with some providers missing."""

        # Mock importlib.util.find_spec to return None for certain imports
        def mock_find_spec(name: str) -> MagicMock | None:
            if name == "openai":
                return MagicMock()
            if name in ["anthropic", "requests"]:
                return None
            return MagicMock()

        with patch("importlib.util.find_spec", side_effect=mock_find_spec):
            success, message, providers = check_llm_dependencies()

            assert success is True  # Still true if at least one real provider
            assert "Available LLM providers:" in message
            assert set(providers) == {"openai", "mock"}
            assert "anthropic" not in providers
            assert "ollama" not in providers

    def test_check_llm_dependencies_all_missing(self) -> None:
        """Test dependency checking with all providers missing."""
        with patch("importlib.util.find_spec", return_value=None):
            success, message, providers = check_llm_dependencies()

            assert success is False
            assert "No LLM providers available" in message
            assert set(providers) == {"mock"}

    def test_check_ollama_connection_failure(self) -> None:
        """Test dependency checking with Ollama connection failure."""
        with patch("importlib.util.find_spec", return_value=MagicMock()):
            # Create a real mock for requests that has the Exception attributes
            with patch("requests.get", side_effect=Exception("Connection failed")):
                success, message, providers = check_llm_dependencies()

                assert success is True  # Still true if at least one real provider
                assert "Available LLM providers:" in message
                assert "ollama" not in providers
