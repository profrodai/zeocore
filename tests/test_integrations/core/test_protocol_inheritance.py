# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/core/test_protocol_inheritance.py
# role: tests
# neighbors: __init__.py, test_get_service.py, test_protocols.py, test_registry.py, test_registry_discovery.py, test_results.py
# exports: MinimalIntegration, MinimalAuthProvider, MinimalConfigProvider, MinimalStorageIntegration, CustomStorageIntegrationProtocol, ExtendedIntegrationProtocol, TestProtocolInheritance
# git_branch: refactor/toolkitWorkflow
# git_commit: 234aec0
# === QV-LLM:END ===

"""
Tests for protocol inheritance and runtime protocol checking.

This module tests the inheritance relationships between protocols and
ensures proper runtime protocol checking.
"""

from collections.abc import Mapping
from typing import Protocol, TypeVar, runtime_checkable

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


# Define a clean minimal implementation of each protocol to avoid
# test cross-contamination
class MinimalIntegration:
    """Minimal implementation of IntegrationProtocol."""

    @property
    def name(self) -> str:
        return "minimal_integration"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self) -> IntegrationResult:
        return IntegrationResult(success=True)

    def is_available(self) -> bool:
        return True


class MinimalAuthProvider:
    """Minimal implementation of AuthProviderProtocol."""

    @property
    def name(self) -> str:
        return "minimal_auth"

    def authenticate(self) -> AuthResult:
        return AuthResult(success=True)

    def refresh_credentials(self) -> AuthResult:
        return AuthResult(success=True)

    def get_credentials(self) -> object:
        return {}

    def save_credentials(self) -> bool:
        return True


class MinimalConfigProvider:
    """Minimal implementation of ConfigProviderProtocol."""

    @property
    def name(self) -> str:
        return "minimal_config"

    def load_config(self, config_path: str | None = None) -> ConfigResult:
        return ConfigResult(success=True)

    def validate_config(self, config: dict) -> bool:
        return True

    def get_default_config(self) -> dict:
        return {}


class MinimalStorageIntegration:
    """Minimal implementation of StorageIntegrationProtocol."""

    @property
    def name(self) -> str:
        return "minimal_storage"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self) -> IntegrationResult:
        return IntegrationResult(success=True)

    def is_available(self) -> bool:
        return True

    def upload_file(
        self, file_path: str, remote_path: str | None = None
    ) -> IntegrationResult[str]:
        return IntegrationResult.success_result("fileId")

    def download_file(
        self, remote_id: str, local_path: str | None = None
    ) -> IntegrationResult[str]:
        return IntegrationResult.success_result("local_path")

    def list_files(
        self, remote_path: str | None = None, pattern: str | None = None
    ) -> IntegrationResult[list[Mapping]]:
        return IntegrationResult.success_result([{"name": "test.txt"}])

    def create_folder(
        self, folder_name: str, parent_path: str | None = None
    ) -> IntegrationResult[str]:
        return IntegrationResult.success_result("folder_id")


# Create additional custom protocols for testing inheritance
T = TypeVar("T")  # Generic type for result content


@runtime_checkable
class CustomStorageIntegrationProtocol(Protocol):
    """Custom protocol extending both IntegrationProtocol and adding storage _operations."""

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


@runtime_checkable
class ExtendedIntegrationProtocol(IntegrationProtocol, Protocol):
    """Extended protocol with additional methods."""

    def validate(self) -> bool: ...

    def get_metadata(self) -> dict: ...


class TestProtocolInheritance:
    """Tests for protocol inheritance and runtime protocol checking."""

    def test_basic_protocol_checking(self) -> None:
        """Test basic protocol checking for main protocols."""
        # Check standard implementations
        integration = MinimalIntegration()
        auth_provider = MinimalAuthProvider()
        config_provider = MinimalConfigProvider()
        storage_integration = MinimalStorageIntegration()

        # Direct protocol implementation checks
        assert isinstance(integration, IntegrationProtocol)
        assert isinstance(auth_provider, AuthProviderProtocol)
        assert isinstance(config_provider, ConfigProviderProtocol)
        assert isinstance(storage_integration, StorageIntegrationProtocol)

        # Check inheritance relationships
        assert isinstance(storage_integration, IntegrationProtocol)
        assert not isinstance(integration, StorageIntegrationProtocol)

        # Negative checks
        assert not isinstance(integration, AuthProviderProtocol)
        assert not isinstance(auth_provider, IntegrationProtocol)
        assert not isinstance(config_provider, StorageIntegrationProtocol)

    def test_partial_implementations(self) -> None:
        """Test that partial implementations are not recognized as fully implementing protocols."""

        # Partial IntegrationProtocol
        class PartialIntegration:
            @property
            def name(self) -> str:
                return "partial"

            @property
            def version(self) -> str:
                return "1.0.0"

            # Missing initialize and is_available methods

        partial = PartialIntegration()
        assert not isinstance(partial, IntegrationProtocol)

        # Partial StorageIntegrationProtocol (implements IntegrationProtocol but not storage methods)
        class PartialStorage:
            @property
            def name(self) -> str:
                return "partial_storage"

            @property
            def version(self) -> str:
                return "1.0.0"

            def initialize(self) -> IntegrationResult:
                return IntegrationResult(success=True)

            def is_available(self) -> bool:
                return True

            # Missing storage-specific methods

        partial_storage = PartialStorage()
        assert isinstance(partial_storage, IntegrationProtocol)
        assert not isinstance(partial_storage, StorageIntegrationProtocol)

        # Missing a single method
        class AlmostStorage(PartialStorage):
            def upload_file(
                self, file_path: str, remote_path: str | None = None
            ) -> IntegrationResult[str]:
                return IntegrationResult.success_result("fileId")

            def download_file(
                self, remote_id: str, local_path: str | None = None
            ) -> IntegrationResult[str]:
                return IntegrationResult.success_result("local_path")

            def list_files(
                self, remote_path: str | None = None, pattern: str | None = None
            ) -> IntegrationResult[list[Mapping]]:
                return IntegrationResult.success_result([{"name": "test.txt"}])

            # Missing create_folder method

        almost_storage = AlmostStorage()
        assert isinstance(almost_storage, IntegrationProtocol)
        assert not isinstance(almost_storage, StorageIntegrationProtocol)

    def test_custom_protocol_checking(self) -> None:
        """Test custom protocol checking with protocol inheritance."""
        # Test with custom storage protocol
        storage = MinimalStorageIntegration()
        assert isinstance(storage, CustomStorageIntegrationProtocol)

        # Missing method from custom protocol
        class PartialCustomStorage:
            @property
            def name(self) -> str:
                return "partial_custom"

            @property
            def version(self) -> str:
                return "1.0.0"

            def initialize(self) -> IntegrationResult:
                return IntegrationResult(success=True)

            def is_available(self) -> bool:
                return True

            def upload_file(
                self, file_path: str, remote_path: str | None = None
            ) -> IntegrationResult[str]:
                return IntegrationResult.success_result("fileId")

            # Missing download_file method

        partial_custom = PartialCustomStorage()
        assert not isinstance(partial_custom, CustomStorageIntegrationProtocol)

        # Test extended protocol
        class ExtendedIntegration(MinimalIntegration):
            def validate(self) -> bool:
                return True

            def get_metadata(self) -> dict:
                return {"version": self.version}

        extended = ExtendedIntegration()
        assert isinstance(extended, IntegrationProtocol)
        assert isinstance(extended, ExtendedIntegrationProtocol)

        # Not implementing the extended methods
        non_extended = MinimalIntegration()
        assert isinstance(non_extended, IntegrationProtocol)
        assert not isinstance(non_extended, ExtendedIntegrationProtocol)

    def test_protocol_attributes(self) -> None:
        """Test protocol attributes and method signatures."""
        # Test attribute access
        integration = MinimalIntegration()
        assert integration.name == "minimal_integration"
        assert integration.version == "1.0.0"

        # Test method return types
        result = integration.initialize()
        assert isinstance(result, IntegrationResult)
        assert result.success is True

        available = integration.is_available()
        assert isinstance(available, bool)
        assert available is True

        # Storage methods return types
        storage = MinimalStorageIntegration()

        upload_result = storage.upload_file("/path/to/file")
        assert isinstance(upload_result, IntegrationResult)
        assert upload_result.content == "fileId"

        download_result = storage.download_file("fileId")
        assert isinstance(download_result, IntegrationResult)
        assert download_result.content == "local_path"

        list_result = storage.list_files()
        assert isinstance(list_result, IntegrationResult)
        assert isinstance(list_result.content, list)
        assert isinstance(list_result.content[0], Mapping)
        assert list_result.content[0]["name"] == "test.txt"

        folder_result = storage.create_folder("test_folder")
        assert isinstance(folder_result, IntegrationResult)
        assert folder_result.content == "folder_id"

    def test_duck_typing_compatibility(self) -> None:
        """Test duck typing compatibility with protocols."""

        # Create a duck-typed implementation without inheriting
        class DuckTypedIntegration:
            @property
            def name(self) -> str:
                return "duck_typed"

            @property
            def version(self) -> str:
                return "1.0.0"

            def initialize(self) -> object:  # Different return type annotation
                return IntegrationResult(success=True)

            def is_available(self) -> bool:
                return True

        duck = DuckTypedIntegration()
        assert isinstance(duck, IntegrationProtocol)

        # Duck-typed storage implementation
        class DuckTypedStorage:
            @property
            def name(self) -> str:
                return "duck_storage"

            @property
            def version(self) -> str:
                return "1.0.0"

            def initialize(self) -> IntegrationResult:
                return IntegrationResult(success=True)

            def is_available(self) -> bool:
                return True

            def upload_file(
                self, file_path: str, remote_path: str = None
            ) -> IntegrationResult[str]:
                return IntegrationResult.success_result("fileId")

            def download_file(
                self, remote_id: str, local_path: str = None
            ) -> IntegrationResult[str]:
                return IntegrationResult.success_result("local_path")

            def list_files(
                self, remote_path: str = None, pattern: str = None
            ) -> IntegrationResult[list]:
                return IntegrationResult.success_result([{"name": "test.txt"}])

            def create_folder(
                self, folder_name: str, parent_path: str = None
            ) -> IntegrationResult:
                return IntegrationResult.success_result("folder_id")

        duck_storage = DuckTypedStorage()
        assert isinstance(duck_storage, IntegrationProtocol)
        assert isinstance(duck_storage, StorageIntegrationProtocol)

    def test_runtime_protocol_registration(self) -> None:
        """Test using runtime protocols for registration and type checking."""

        # Create two distinct runtime protocols for testing
        @runtime_checkable
        class ServiceA(Protocol):
            def provide_service_a(self) -> str: ...

        @runtime_checkable
        class ServiceB(Protocol):
            def provide_service_b(self) -> str: ...

        # Create implementations
        class A:
            def provide_service_a(self) -> str:
                return "Service A"

        class B:
            def provide_service_b(self) -> str:
                return "Service B"

        class AB:
            def provide_service_a(self) -> str:
                return "Service A from AB"

            def provide_service_b(self) -> str:
                return "Service B from AB"

        # Test runtime protocol checking
        a = A()
        b = B()
        ab = AB()

        assert isinstance(a, ServiceA)
        assert not isinstance(a, ServiceB)

        assert isinstance(b, ServiceB)
        assert not isinstance(b, ServiceA)

        assert isinstance(ab, ServiceA)
        assert isinstance(ab, ServiceB)

        # Test using runtime protocols in a registry-like scenario
        registry = {"service_a": [], "service_b": []}

        for service in [a, b, ab]:
            if isinstance(service, ServiceA):
                registry["service_a"].append(service)
            if isinstance(service, ServiceB):
                registry["service_b"].append(service)

        assert len(registry["service_a"]) == 2  # a and ab
        assert len(registry["service_b"]) == 2  # b and ab
