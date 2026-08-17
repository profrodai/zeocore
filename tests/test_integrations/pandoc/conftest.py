"""
Pytest configuration for pandoc integration tests.

This module provides common fixtures and configuration for all pandoc
integration tests.
"""

import os
import sys
import time
import types
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from _pytest.monkeypatch import MonkeyPatch


# Fixture for monkeypatching filesystem service
@pytest.fixture(autouse=True)
def fs_stub(monkeypatch: MonkeyPatch) -> SimpleNamespace:
    """
    Stub out the quack_core.core.fs.service.standalone methods for file _ops.
    """
    # Create a module structure if it doesn't exist
    if "quack_core.core.fs.service" not in sys.modules:
        # Create the module hierarchy
        if "quack-core" not in sys.modules:
            quackcore_mod = types.ModuleType("quack-core")
            sys.modules["quack-core"] = quackcore_mod

        if "quack_core.core.fs" not in sys.modules:
            fs_mod = types.ModuleType("quack_core.core.fs")
            sys.modules["quack_core.core.fs"] = fs_mod

        # Create the service module
        service_mod = types.ModuleType("quack_core.core.fs.service")
        sys.modules["quack_core.core.fs.service"] = service_mod

    # Create the stub with all necessary methods
    stub = SimpleNamespace()

    # Create a DataResult-like object to return from _ops
    class DataResult:
        def __init__(
            self,
            success: bool = True,
            data: Any = None,  # noqa: ANN401 -- mirrors the real DataResult's
            # deliberately heterogeneous data field (str, dict, list, model,
            # depending on the operation); a mock stub for it is correctly
            # just as loose.
            error: str | None = None,
            path: str = "/dummy/path",
            message: str | None = None,
            fmt: str | None = None,
        ) -> None:
            self.success = success
            self.data = data
            self.error = error
            self.path = path  # Always provide a path to avoid validation errors
            self.message = message or ""
            self.format = fmt or ""

    # Default get_file_info returns success, exists, size, modified
    stub.get_file_info = lambda path: SimpleNamespace(
        success=True, exists=True, size=100, modified=time.time(), is_dir=False
    )

    # Create directory operation with result
    stub.create_directory = lambda path, exist_ok=True: SimpleNamespace(success=True)

    # String path handling with DataResult style returns
    stub.join_path = lambda *parts: DataResult(success=True, data=os.path.join(*parts))

    # Split path into components with DataResult style return
    stub.split_path = lambda path: DataResult(
        success=True, data=path.split(os.sep) if isinstance(path, str) else [str(path)]
    )

    # Text file _ops
    stub.write_text = lambda path, content, encoding=None: SimpleNamespace(
        success=True, bytes_written=len(content) if isinstance(content, str) else 0
    )

    # Reading content from files
    stub.read_text = lambda path, encoding=None: SimpleNamespace(
        success=True,
        content="<html><body><h1>Title</h1><p>Content</p></body></html>"
        if path.endswith(".html")
        else "# Title\n\nContent",
    )

    # Get file extension
    stub.get_extension = lambda path: DataResult(
        success=True,
        data=path.split(".")[-1] if isinstance(path, str) and "." in path else "",
    )

    # Path validation and normalization
    stub.get_path_info = lambda path: SimpleNamespace(success=True)
    stub.is_valid_path = lambda path: True
    stub.normalize_path = lambda p: SimpleNamespace(
        success=True, path=os.path.abspath(p)
    )
    stub.normalize_path_with_info = stub.normalize_path

    # Convert file size to string
    stub.get_file_size_str = lambda size: DataResult(
        success=True, data=f"{size}B", path="/dummy/path", fmt="size_string"
    )

    # File finding
    stub.find_files = lambda dir_path, pattern, recursive=False: SimpleNamespace(
        success=True, files=["file1.html", "file2.html"]
    )

    # Add additional methods needed for other tests
    stub.write_json = lambda path, content, indent=None: SimpleNamespace(
        success=True, path=path, bytes_written=100
    )

    stub.read_binary = lambda path: SimpleNamespace(
        success=True, content=b"binary content"
    )

    stub.resolve_path = lambda path: SimpleNamespace(
        success=True, path=os.path.abspath(path) if path else "/dummy/path"
    )

    # Set the standalone attribute directly in the module
    # This is the critical change - we need to directly set the attribute on the module
    # sys.modules[...] is typed ModuleType, which has no static `standalone`
    # attribute -- this is a deliberate dynamic monkeypatch of a real (or
    # synthetic) module object, not a typo, so the lookup is bound through an
    # Any-typed local once rather than per-attribute-access ignored.
    fs_service_mod: Any = sys.modules["quack_core.core.fs.service"]
    fs_service_mod.standalone = stub

    # The line above alone does NOT reach every consumer: each pandoc module
    # binds its own local `fs` name at import time via
    # `from quack_core.core.fs.service import standalone as fs`, so
    # reassigning sys.modules[...].standalone after that import has already
    # happened never touches the already-bound local alias (mock-path-drift-fix
    # SOW-02 Finding 2). Patch the alias directly on every module that binds
    # it, so this one shared, autouse fixture actually reaches all of them.
    import quack_core.integrations.pandoc.config as _pandoc_config
    import quack_core.integrations.pandoc.converter as _pandoc_converter
    import quack_core.integrations.pandoc.operations.html_to_md as _pandoc_html_to_md
    import quack_core.integrations.pandoc.operations.md_to_docx as _pandoc_md_to_docx
    import quack_core.integrations.pandoc.operations.utils as _pandoc_utils

    for _mod in (
        _pandoc_config,
        _pandoc_converter,
        _pandoc_html_to_md,
        _pandoc_md_to_docx,
        _pandoc_utils,
    ):
        if hasattr(_mod, "fs"):
            monkeypatch.setattr(_mod, "fs", stub)

    return stub


# Fixture for mocking pypandoc
@pytest.fixture
def mock_pypandoc(monkeypatch: MonkeyPatch) -> MagicMock:
    """
    Create a mock pypandoc module for testing.
    """
    mock = MagicMock()
    mock.get_pandoc_version.return_value = "2.11.0"
    mock.convert_file.return_value = "# Converted Content\n\nThis is markdown."
    monkeypatch.setitem(sys.modules, "pypandoc", mock)
    return mock


# Fixture for path service
@pytest.fixture
def mock_paths_service(monkeypatch: MonkeyPatch) -> MagicMock:
    """
    Mock the paths service for resolving project paths.
    """
    mock = MagicMock()
    # Define the resolve_project_path method to just return the path unchanged
    mock.resolve_project_path = lambda path: path

    # Create a proper paths module structure
    if "quack_core.core.paths" not in sys.modules:
        paths_mod = types.ModuleType("quack_core.core.paths")
        sys.modules["quack_core.core.paths"] = paths_mod

    # Add necessary functions directly to the module
    # Same shape as fs_service_mod above: a deliberate dynamic monkeypatch of
    # a real (or synthetic) module object, bound through one Any-typed local
    # (renamed from the `paths_mod` ModuleType local above to avoid a mypy
    # redefinition-with-different-type conflict on the same name).
    paths_mod_any: Any = sys.modules["quack_core.core.paths"]
    paths_mod_any.service = mock
    paths_mod_any.resolve_path = lambda path: (
        os.path.abspath(path) if path else "/dummy/path"
    )
    paths_mod_any.expand_user_vars = lambda path: (
        os.path.expanduser(path)
        if path and isinstance(path, str) and path.startswith("~")
        else path
    )
    paths_mod_any.read_yaml = lambda path: SimpleNamespace(
        success=True, data={}
    )

    return mock


# Fixture for bs4
@pytest.fixture
def mock_bs4(monkeypatch: MonkeyPatch) -> MagicMock:
    """
    Mock BeautifulSoup for HTML validation.
    """
    mock_soup = MagicMock()
    mock_soup.find.return_value = True  # Default to finding body tag
    mock_soup.find_all.return_value = []  # No links by default

    mock_bs = MagicMock()
    mock_bs.BeautifulSoup.return_value = mock_soup

    monkeypatch.setitem(sys.modules, "bs4", mock_bs)
    return mock_bs


# Fixture for docx
@pytest.fixture
def mock_docx(monkeypatch: MonkeyPatch) -> MagicMock:
    """
    Mock python-docx for DOCX validation.
    """
    mock_para = MagicMock()
    mock_para.style.name = "Heading 1"

    mock_doc = MagicMock()
    mock_doc.paragraphs = [mock_para]

    mock_docx_module = MagicMock()
    mock_docx_module.Document.return_value = mock_doc

    monkeypatch.setitem(sys.modules, "docx", mock_docx_module)
    return mock_docx_module
