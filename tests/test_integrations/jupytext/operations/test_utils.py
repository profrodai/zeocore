from types import SimpleNamespace

import pytest
from _pytest.monkeypatch import MonkeyPatch

from zeo_core.core.errors import ZeoIntegrationError
from zeo_core.integrations.jupytext.operations.utils import (
    detect_format,
    get_file_info,
    guess_format_from_path,
    verify_jupytext,
)

from ..conftest import PERCENT_PY_SOURCE

# --- verify_jupytext ---


def test_verify_jupytext_real() -> None:
    """jupytext is a real installed dependency in this test environment --
    exercise the real import/version path rather than mocking it, since
    (unlike pypandoc) there is no external binary to avoid invoking."""
    version = verify_jupytext()
    assert isinstance(version, str)
    assert version != ""


def test_verify_jupytext_missing(monkeypatch: MonkeyPatch) -> None:
    import importlib

    # verify_jupytext() calls importlib.import_module("jupytext"), which
    # short-circuits through sys.modules (never reaching builtins.__import__)
    # once the real package is already imported in-process -- patch
    # importlib.import_module itself, matching how pandoc's own operations
    # lazily import pypandoc the same way.
    real_import_module = importlib.import_module

    def fake_import_module(name: str, *args: object, **kwargs: object) -> object:
        if name == "jupytext":
            raise ImportError("no jupytext")
        return real_import_module(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    with pytest.raises(ZeoIntegrationError, match="not installed"):
        verify_jupytext()


# --- guess_format_from_path ---


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("ex01.py", "py:percent"),
        ("notebook.ipynb", "ipynb"),
        ("README.md", "md"),
        ("README.markdown", "md"),
        ("script.unknownext", "py:percent"),
    ],
)
def test_guess_format_from_path(path: str, expected: str) -> None:
    assert guess_format_from_path(path) == expected


def test_guess_format_from_path_custom_default() -> None:
    assert guess_format_from_path("script.xyz", default="md") == "md"


# --- detect_format ---


def test_detect_format_ipynb_extension() -> None:
    assert detect_format("{}", "notebook.ipynb") == "ipynb"


def test_detect_format_percent_py() -> None:
    fmt = detect_format(PERCENT_PY_SOURCE, "ex01.py")
    assert fmt.startswith("py")


def test_detect_format_falls_back_on_error(monkeypatch: MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "jupytext.formats":
            raise ImportError("boom")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", fake_import)
    fmt = detect_format(PERCENT_PY_SOURCE, "ex01.py")
    assert fmt == "py:percent"


def test_detect_format_falls_back_when_guess_format_raises(
    monkeypatch: MonkeyPatch,
) -> None:
    """A successful import of jupytext.formats whose guess_format() call
    itself raises must still fall back to extension-based detection, not
    propagate."""
    import sys

    # sys.modules lookup rather than a static `import jupytext.formats`,
    # matching pandoc's own precedent of never statically importing its
    # equally stub-less optional dependency (pypandoc) -- see
    # test_to_notebook.py::test_convert_to_notebook_parse_failure.
    jupytext_formats = sys.modules["jupytext.formats"]

    def broken_guess_format(text: str, ext: str) -> object:
        raise ValueError("cannot guess")

    monkeypatch.setattr(jupytext_formats, "guess_format", broken_guess_format)
    fmt = detect_format(PERCENT_PY_SOURCE, "ex01.py")
    assert fmt == "py:percent"


def test_detect_format_no_extension_uses_guessed_directly() -> None:
    """A path with no extension hits the `guessed` (no ext prefix) branch."""
    fmt = detect_format(PERCENT_PY_SOURCE, "ex01_noext")
    assert fmt  # jupytext still guesses something for percent-format content


# --- get_file_info ---


def test_get_file_info_success(fs_stub: SimpleNamespace) -> None:
    info = get_file_info("ex01.py")
    assert info.path == "ex01.py"
    assert info.format == "py:percent"
    assert info.size == 100


def test_get_file_info_with_format_hint(fs_stub: SimpleNamespace) -> None:
    info = get_file_info("ex01.py", format_hint="md")
    assert info.format == "md"


def test_get_file_info_missing_file(fs_stub: SimpleNamespace) -> None:
    fs_stub.get_file_info = lambda path: SimpleNamespace(success=False, exists=False)
    with pytest.raises(ZeoIntegrationError, match="File not found"):
        get_file_info("missing.py")
