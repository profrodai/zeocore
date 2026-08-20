"""
Tests for notebook -> script/markdown conversion (the inverse of
to_notebook.py). Not exercised by quackslides today, but a complete
integration should support both directions jupytext itself supports.
"""

from types import SimpleNamespace

from _pytest.monkeypatch import MonkeyPatch

from zeo_core.integrations.jupytext.config import JupytextConfig, ValidationConfig
from zeo_core.integrations.jupytext.operations.to_script import convert_to_script


def test_convert_to_script_success(fs_stub: SimpleNamespace) -> None:
    config = JupytextConfig()
    result = convert_to_script("notebook.ipynb", "notebook.py", config)

    assert result.success is True
    output_path, details = result.content  # type: ignore[misc]
    assert output_path == "notebook.py"
    assert details.source_format == "ipynb"
    assert details.target_format == "py:percent"
    assert details.cell_count == 2  # MINIMAL_IPYNB_SOURCE has 2 cells


def test_convert_to_script_writes_real_percent_format(fs_stub: SimpleNamespace) -> None:
    captured: dict[str, str] = {}

    def capture_write(
        path: str, content: str, encoding: str | None = None
    ) -> SimpleNamespace:
        captured["content"] = content
        return SimpleNamespace(success=True, bytes_written=len(content))

    fs_stub.write_text = capture_write
    config = JupytextConfig()
    result = convert_to_script("notebook.ipynb", "notebook.py", config)

    assert result.success is True
    assert "# %%" in captured["content"]
    assert "x = 1" in captured["content"]


def test_convert_to_script_explicit_target_format(fs_stub: SimpleNamespace) -> None:
    config = JupytextConfig()
    result = convert_to_script(
        "notebook.ipynb", "notebook.md", config, target_format="md"
    )
    assert result.success is True
    _, details = result.content  # type: ignore[misc]
    assert details.target_format == "md"


def test_convert_to_script_uses_config_default_format(fs_stub: SimpleNamespace) -> None:
    config = JupytextConfig(default_script_format="py:light")
    result = convert_to_script("notebook.ipynb", "notebook.py", config)
    assert result.success is True
    _, details = result.content  # type: ignore[misc]
    assert details.target_format == "py:light"


def test_convert_to_script_missing_input(fs_stub: SimpleNamespace) -> None:
    fs_stub.get_file_info = lambda path: SimpleNamespace(success=False, exists=False)
    config = JupytextConfig()
    result = convert_to_script("missing.ipynb", "out.py", config)
    assert result.success is False
    assert "not found" in (result.error or "")


def test_convert_to_script_jupytext_not_installed(
    fs_stub: SimpleNamespace, monkeypatch: MonkeyPatch
) -> None:
    import importlib

    real_import_module = importlib.import_module

    def fake_import_module(name: str, *args: object, **kwargs: object) -> object:
        if name == "jupytext":
            raise ImportError("no jupytext")
        return real_import_module(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    config = JupytextConfig()
    result = convert_to_script("notebook.ipynb", "out.py", config)
    assert result.success is False
    assert "not installed" in (result.error or "")


def test_convert_to_script_empty_notebook_rejected(fs_stub: SimpleNamespace) -> None:
    fs_stub.read_text = lambda path, encoding=None: SimpleNamespace(
        success=True,
        content='{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}',
    )
    config = JupytextConfig(validation=ValidationConfig(verify_structure=True))
    result = convert_to_script("empty.ipynb", "out.py", config)
    assert result.success is False
    assert "no cells" in (result.error or "").lower()


def test_convert_to_script_output_below_min_size(fs_stub: SimpleNamespace) -> None:
    config = JupytextConfig(validation=ValidationConfig(min_file_size=10_000_000))
    result = convert_to_script("notebook.ipynb", "out.py", config)
    assert result.success is False
    assert "below the minimum" in (result.error or "")


def test_convert_to_script_write_failure(fs_stub: SimpleNamespace) -> None:
    fs_stub.write_text = lambda path, content, encoding=None: SimpleNamespace(
        success=False, error="disk full"
    )
    config = JupytextConfig()
    result = convert_to_script("notebook.ipynb", "out.py", config)
    assert result.success is False
    assert "Failed to write" in (result.error or "")


def test_convert_to_script_read_failure(fs_stub: SimpleNamespace) -> None:
    fs_stub.read_text = lambda path, encoding=None: SimpleNamespace(
        success=False, error="disk error"
    )
    config = JupytextConfig()
    result = convert_to_script("notebook.ipynb", "out.py", config)
    assert result.success is False
    assert "Could not read" in (result.error or "")


def test_convert_to_script_non_string_content(fs_stub: SimpleNamespace) -> None:
    fs_stub.read_text = lambda path, encoding=None: SimpleNamespace(
        success=True, content=b"not a string"
    )
    config = JupytextConfig()
    result = convert_to_script("notebook.ipynb", "out.py", config)
    assert result.success is False
    assert "did not decode to text" in (result.error or "")


def test_convert_to_script_directory_create_failure(fs_stub: SimpleNamespace) -> None:
    fs_stub.create_directory = lambda path, exist_ok=True: SimpleNamespace(
        success=False, error="permission denied"
    )
    config = JupytextConfig()
    result = convert_to_script("notebook.ipynb", "sub/out.py", config)
    assert result.success is False
    assert "Failed to create output directory" in (result.error or "")


def test_convert_to_script_bytes_written_fallback_to_len(
    fs_stub: SimpleNamespace,
) -> None:
    """When fs.write_text's result has no usable bytes_written, the
    operation must fall back to len(text.encode('utf-8')) rather than
    erroring."""
    fs_stub.write_text = lambda path, content, encoding=None: SimpleNamespace(
        success=True, bytes_written=None
    )
    config = JupytextConfig()
    result = convert_to_script("notebook.ipynb", "out.py", config)
    assert result.success is True
    _, details = result.content  # type: ignore[misc]
    assert details.output_size is not None
    assert details.output_size > 0


def test_convert_to_script_bytes_written_non_numeric_fallback(
    fs_stub: SimpleNamespace,
) -> None:
    fs_stub.write_text = lambda path, content, encoding=None: SimpleNamespace(
        success=True, bytes_written="not-a-number"
    )
    config = JupytextConfig()
    result = convert_to_script("notebook.ipynb", "out.py", config)
    assert result.success is True
    _, details = result.content  # type: ignore[misc]
    assert details.output_size is not None
    assert details.output_size > 0
