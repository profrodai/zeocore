"""
Pytest configuration for ffmpeg integration tests.

Mirrors `tests/test_integrations/pandoc/conftest.py`'s `fs_stub` shape: stubs
out `zeo_core.core.fs.service.standalone` so unit tests never touch a real
filesystem sandbox, while `tests/test_integrations/ffmpeg/test_service_live.py`
(no fs_stub involved) exercises the wrapper against the real ffmpeg binary and
a real filesystem in an isolated tmp_path.
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


@pytest.fixture(autouse=True)
def fs_stub(monkeypatch: MonkeyPatch) -> SimpleNamespace:
    """
    Stub out the zeo_core.core.fs.service.standalone methods for file _ops.

    Same shape/rationale as pandoc/conftest.py's fs_stub -- each ffmpeg
    integration module binds its own local `fs` alias at import time
    (`from zeo_core.core.fs.service import standalone as fs`), so this
    monkeypatches that local alias directly on every module that binds it
    rather than the package-level attribute (see pandoc/conftest.py's own
    NOTE for why the latter is broken on Python 3.10).
    """
    if "zeo_core.core.fs.service" not in sys.modules:
        if "zeocore" not in sys.modules:
            sys.modules["zeocore"] = types.ModuleType("zeocore")
        if "zeo_core.core.fs" not in sys.modules:
            sys.modules["zeo_core.core.fs"] = types.ModuleType("zeo_core.core.fs")
        sys.modules["zeo_core.core.fs.service"] = types.ModuleType(
            "zeo_core.core.fs.service"
        )

    stub = SimpleNamespace()

    class DataResult:
        def __init__(
            self,
            success: bool = True,
            data: Any = None,  # noqa: ANN401 -- mirrors pandoc/conftest.py's DataResult stub
            error: str | None = None,
            path: str = "/dummy/path",
        ) -> None:
            self.success = success
            self.data = data
            self.error = error
            self.path = path

    stub.get_file_info = lambda path: SimpleNamespace(
        success=True, exists=True, size=100, modified=time.time(), is_dir=False
    )
    stub.create_directory = lambda path, exist_ok=True: SimpleNamespace(success=True)
    stub.join_path = lambda *parts: DataResult(success=True, data=os.path.join(*parts))
    stub.split_path = lambda path: DataResult(
        success=True, data=path.split(os.sep) if isinstance(path, str) else [str(path)]
    )
    stub.get_extension = lambda path: DataResult(
        success=True,
        data=path.split(".")[-1] if isinstance(path, str) and "." in path else "",
    )
    stub.get_path_info = lambda path: SimpleNamespace(success=True)
    stub.is_valid_path = lambda path: True
    stub.normalize_path = lambda p: SimpleNamespace(
        success=True, path=os.path.abspath(p)
    )
    stub.normalize_path_with_info = stub.normalize_path
    stub.expand_user_vars = lambda path: SimpleNamespace(
        success=True,
        data=os.path.expanduser(path) if isinstance(path, str) else path,
    )
    stub.resolve_path = lambda path: SimpleNamespace(
        success=True, path=os.path.abspath(path) if path else "/dummy/path"
    )

    import zeo_core.integrations.ffmpeg.config as _ffmpeg_config

    for _mod in (_ffmpeg_config,):
        if hasattr(_mod, "fs"):
            monkeypatch.setattr(_mod, "fs", stub)

    return stub


@pytest.fixture
def mock_paths_service(monkeypatch: MonkeyPatch) -> MagicMock:
    """Mock the paths service for resolving project paths (matches pandoc's)."""
    mock = MagicMock()
    mock.resolve_project_path = lambda path: SimpleNamespace(success=True, path=path)
    return mock
