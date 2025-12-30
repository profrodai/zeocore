# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/core/base/test_protocols.py
# role: tests
# neighbors: __init__.py, auth_provider_impl.py, config_provider_impl.py, integration_service_impl.py, test_auth_provider.py, test_base.py (+3 more)
# exports: SampleIntegration, SampleAuthProvider, SampleConfigProvider, MinimalStorageProtocol, SampleStorageIntegration, TestIntegrationProtocol, TestAuthProviderProtocol, TestConfigProviderProtocol (+2 more)
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===

"""
Tests for integration protocol interfaces.
"""

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from quack_core.integrations.core.protocols import (
    AuthProviderProtocol,
    ConfigProviderProtocol,
    IntegrationProtocol,
    StorageIntegrationProtocol,
)
from quack_core.integrations.core.results import (
    AuthResult,
    ConfigResult,
    IntegrationResult,
)


# Test implementations of each protocol
class SampleIntegration:
    """Test implementation of IntegrationProtocol."""

    @property
    def name(self) -> str:
        return "sample_integration"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self) -> IntegrationResult:
        return IntegrationResult.success_result(message="Initialized")

    def is_available(self) -> bool:
        return True


class SampleAuthProvider:
    """Test implementation of AuthProviderProtocol."""

    @property
    def name(self) -> str:
        return "sample_auth"

    def authenticate(self) -> AuthResult:
        return AuthResult.success_result(token="test_token")

    def refresh_credentials(self) -> AuthResult:
        return AuthResult.success_result(message="Refreshed")

    def get_credentials(self) -> object:
        return {"token": "test_token"}

    def save_credentials(self) -> bool:
        return True


class SampleConfigProvider:
    """Test implementation of ConfigProviderProtocol."""

    @property
    def name(self) -> str:
        return "sample_config"

    def load_config(self, config_path: str | None = None) -> ConfigResult:
        return ConfigResult.success_result(content={"key": "value"})

    def validate_config(self, config: dict) -> bool:
        return True

    def get_default_config(self) -> dict:
        return {"default_key": "default_value"}


@runtime_checkable
class MinimalStorageProtocol(Protocol):
    """Protocol extending both IntegrationProtocol and StorageIntegrationProtocol."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def initialize(self) -> IntegrationResult: ...

    def is_available(self) -> bool: ...

    def upload_file(
        self, file_path: str, remote_path: str | None = None
    ) -> IntegrationResult[str]: ...

    def download_file(
        self, remote_id: str, local_path: str | None = None
    ) -> IntegrationResult[str]: ...

    def list_files(
        self, remote_path: str | None = None, pattern: str | None = None
    ) -> IntegrationResult[list[Mapping]]: ...

    def create_folder(
        self, folder_name: str, parent_path: str | None = None
    ) -> IntegrationResult[str]: ...


class SampleStorageIntegration:
    """Test implementation of StorageIntegrationProtocol."""

    @property
    def name(self) -> str:
        return "sample_storage"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self) -> IntegrationResult:
        return IntegrationResult.success_result(message="Initialized")

    def is_available(self) -> bool:
        return True

    def upload_file(
        self, file_path: str, remote_path: str | None = None
    ) -> IntegrationResult[str]:
        return IntegrationResult.success_result("remote_id")

    def download_file(
        self, remote_id: str, local_path: str | None = None
    ) -> IntegrationResult[str]:
        return IntegrationResult.success_result("/downloaded/file")

    def list_files(
        self, remote_path: str | None = None, pattern: str | None = None
    ) -> IntegrationResult[list[Mapping]]:
        return IntegrationResult.success_result([{"name": "file1"}, {"name": "file2"}])

    def create_folder(
        self, folder_name: str, parent_path: str | None = None
    ) -> IntegrationResult[str]:
        return IntegrationResult.success_result("folder_id")


class TestIntegrationProtocol:
    """Tests for IntegrationProtocol."""

    def test_implementation(self) -> None:
        """Test that IntegrationProtocol can be implemented."""
        integration = SampleIntegration()

        # Check that it implements the protocol
        assert isinstance(integration, IntegrationProtocol)

        # Test required methods
        assert integration.name == "sample_integration"
        assert integration.version == "1.0.0"
        assert integration.is_available() is True

        # Test initialize method
        result = integration.initialize()
        assert result.success is True
        assert result.message == "Initialized"

    def test_runtime_checkable(self) -> None:
        """Test that the protocol is runtime-checkable."""

        # A class that doesn't implement all required methods
        class PartialIntegration:
            @property
            def name(self) -> str:
                return "partial"

        # Should not be recognized as implementing the protocol
        assert not isinstance(PartialIntegration(), IntegrationProtocol)

        # Create an object with the required attributes and methods
        class DynamicIntegration:
            @property
            def name(self) -> str:
                return "dynamic"

            @property
            def version(self) -> str:
                return "1.0.0"

            def initialize(self) -> IntegrationResult:
                return IntegrationResult()

            def is_available(self) -> bool:
                return True

        # Should be recognized as implementing the protocol
        assert isinstance(DynamicIntegration(), IntegrationProtocol)


class TestAuthProviderProtocol:
    """Tests for AuthProviderProtocol."""

    def test_implementation(self) -> None:
        """Test that AuthProviderProtocol can be implemented."""
        provider = SampleAuthProvider()

        # Check that it implements the protocol
        assert isinstance(provider, AuthProviderProtocol)

        # Test required methods
        assert provider.name == "sample_auth"

        # Test authenticate method
        result = provider.authenticate()
        assert result.success is True
        assert result.token == "test_token"

        # Test refresh_credentials method
        result = provider.refresh_credentials()
        assert result.success is True
        assert result.message == "Refreshed"

        # Test get_credentials method
        credentials = provider.get_credentials()
        assert credentials == {"token": "test_token"}

        # Test save_credentials method
        assert provider.save_credentials() is True

    def test_runtime_checkable(self) -> None:
        """Test that the protocol is runtime-checkable."""

        # A class that doesn't implement all required methods
        class PartialAuthProvider:
            @property
            def name(self) -> str:
                return "partial"

        # Should not be recognized as implementing the protocol
        assert not isinstance(PartialAuthProvider(), AuthProviderProtocol)


class TestConfigProviderProtocol:
    """Tests for ConfigProviderProtocol."""

    def test_implementation(self) -> None:
        """Test that ConfigProviderProtocol can be implemented."""
        provider = SampleConfigProvider()

        # Check that it implements the protocol
        assert isinstance(provider, ConfigProviderProtocol)

        # Test required methods
        assert provider.name == "sample_config"

        # Test load_config method
        result = provider.load_config()
        assert result.success is True
        assert result.content == {"key": "value"}

        # Test validate_config method
        assert provider.validate_config({}) is True

        # Test get_default_config method
        defaults = provider.get_default_config()
        assert defaults == {"default_key": "default_value"}

    def test_runtime_checkable(self) -> None:
        """Test that the protocol is runtime-checkable."""

        # A class that doesn't implement all required methods
        class PartialConfigProvider:
            @property
            def name(self) -> str:
                return "partial"

        # Should not be recognized as implementing the protocol
        assert not isinstance(PartialConfigProvider(), ConfigProviderProtocol)


class TestStorageIntegrationProtocol:
    """Tests for StorageIntegrationProtocol."""

    def test_implementation(self) -> None:
        """Test that StorageIntegrationProtocol can be implemented."""
        integration = SampleStorageIntegration()

        # Check that it implements both protocols
        assert isinstance(integration, IntegrationProtocol)
        assert isinstance(integration, StorageIntegrationProtocol)

        # Test required methods from IntegrationProtocol
        assert integration.name == "sample_storage"
        assert integration.version == "1.0.0"
        assert integration.is_available() is True

        # Test storage-specific methods
        upload_result = integration.upload_file("/local/file", "/remote/path")
        assert upload_result.success is True
        assert upload_result.content == "remote_id"

        download_result = integration.download_file("remote_id", "/local/path")
        assert download_result.success is True
        assert download_result.content == "/downloaded/file"

        list_result = integration.list_files()
        assert list_result.success is True
        assert len(list_result.content) == 2
        assert list_result.content[0]["name"] == "file1"

        folder_result = integration.create_folder("new_folder")
        assert folder_result.success is True
        assert folder_result.content == "folder_id"

    def test_runtime_checkable(self) -> None:
        """Test that the protocol is runtime-checkable."""

        # A class that implements IntegrationProtocol but not StorageIntegrationProtocol
        class BasicIntegration:
            @property
            def name(self) -> str:
                return "basic"

            @property
            def version(self) -> str:
                return "1.0.0"

            def initialize(self) -> IntegrationResult:
                return IntegrationResult()

            def is_available(self) -> bool:
                return True

        basic = BasicIntegration()
        # Should be recognized as implementing IntegrationProtocol
        assert isinstance(basic, IntegrationProtocol)
        # But not StorageIntegrationProtocol
        assert not isinstance(basic, StorageIntegrationProtocol)


class TestProtocolInheritance:
    """Tests for protocol inheritance and interface contracts."""

    def test_storage_integration_inheritance(self) -> None:
        """Test that StorageIntegrationProtocol properly inherits from IntegrationProtocol."""
        storage = SampleStorageIntegration()

        # Check implementation against the MinimalStorageProtocol
        assert isinstance(storage, MinimalStorageProtocol)

        # Check runtime type checking works for both protocols
        assert isinstance(storage, IntegrationProtocol)
        assert isinstance(storage, StorageIntegrationProtocol)

        # Incomplete implementation should fail checks
        class IncompleteStorage:
            @property
            def name(self) -> str:
                return "incomplete"

            @property
            def version(self) -> str:
                return "1.0.0"

        incomplete = IncompleteStorage()
        assert not isinstance(incomplete, MinimalStorageProtocol)
        assert not isinstance(incomplete, StorageIntegrationProtocol)
