"""
Pytest configuration for jupytext integration tests.

This module provides common fixtures for all jupytext integration tests,
following the pandoc integration's own conftest.py conventions: an autouse
`fs_stub` fixture that monkeypatches the module-level `fs` alias each
jupytext submodule binds at import time (`from zeo_core.core.fs.service
import standalone as fs`), plus small real-content fixtures for jupytext
itself (a pure-Python library with no external binary, unlike pypandoc --
real conversions are exercised directly rather than mocked everywhere).
"""

import os
import sys
import time
import types
from types import SimpleNamespace
from typing import Any

import pytest
from _pytest.monkeypatch import MonkeyPatch

# A real, small percent-format script -- mirrors quackslides' own exercise
# file convention (# %% [markdown] header cell, # %% code cell) exactly.
PERCENT_PY_SOURCE = """# %% [markdown]
# ## Exercise 1 -- Tool Calling
# Implement a basic tool-calling loop.

# %%
def call_tool(name: str, args: dict) -> str:
    return f"{name}({args})"
"""

# A real, minimal .ipynb JSON document (nbformat v4) with one markdown and
# one code cell -- used to exercise the notebook -> script direction without
# depending on script -> notebook having already run.
MINIMAL_IPYNB_SOURCE = """{
 "cells": [
  {
   "id": "title-cell",
   "cell_type": "markdown",
   "metadata": {},
   "source": ["## Title"]
  },
  {
   "id": "code-cell",
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": ["x = 1"]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
"""


@pytest.fixture(autouse=True)
def fs_stub(monkeypatch: MonkeyPatch) -> SimpleNamespace:
    """
    Stub out the zeo_core.core.fs.service.standalone methods for file _ops.

    Mirrors pandoc's own `fs_stub` fixture: default `read_text` returns the
    real percent-format fixture content for `.py` paths and the real minimal
    notebook JSON for `.ipynb` paths, so operations-layer tests exercise
    genuine jupytext parsing/serialization rather than opaque mock strings.
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
            data: Any = None,  # noqa: ANN401 -- mirrors pandoc conftest's own DataResult stub, deliberately heterogeneous
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
    stub.write_text = lambda path, content, encoding=None: SimpleNamespace(
        success=True, bytes_written=len(content) if isinstance(content, str) else 0
    )
    stub.read_text = lambda path, encoding=None: SimpleNamespace(
        success=True,
        content=MINIMAL_IPYNB_SOURCE if path.endswith(".ipynb") else PERCENT_PY_SOURCE,
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
    stub.get_file_size_str = lambda size: DataResult(success=True, data=f"{size}B")
    stub.find_files = lambda dir_path, pattern, recursive=False: SimpleNamespace(
        success=True, files=["file1.py", "file2.py"]
    )
    stub.expand_user_vars = lambda path: DataResult(success=True, data=path)

    # Same rationale as pandoc's own conftest.py: patch each jupytext
    # submodule's already-bound local `fs` name directly (monkeypatch.setattr
    # per-module), never the package-level `standalone` object itself --
    # production code reads through the local alias, and permanently
    # clobbering the shared `standalone` object leaks past this fixture's
    # teardown into unrelated tests (pandoc conftest.py's own documented
    # Python 3.10 patch-target-collision history).
    import zeo_core.integrations.jupytext.config as _jtx_config
    import zeo_core.integrations.jupytext.operations.to_notebook as _jtx_to_notebook
    import zeo_core.integrations.jupytext.operations.to_script as _jtx_to_script
    import zeo_core.integrations.jupytext.operations.utils as _jtx_utils

    for _mod in (_jtx_config, _jtx_to_notebook, _jtx_to_script, _jtx_utils):
        if hasattr(_mod, "fs"):
            monkeypatch.setattr(_mod, "fs", stub)

    return stub


@pytest.fixture
def mock_paths_service(monkeypatch: MonkeyPatch) -> SimpleNamespace:
    """Mock the paths service for resolving project paths (pandoc conftest parity)."""
    mock = SimpleNamespace()
    mock.resolve_project_path = lambda path: SimpleNamespace(success=True, path=path)
    return mock
