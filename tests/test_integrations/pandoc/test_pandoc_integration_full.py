import os
import sys
import time
import types
from collections.abc import Generator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import zeo_core.core.fs.service.standalone
from _pytest.monkeypatch import MonkeyPatch
from zeo_core.core.errors import ZeoIntegrationError
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.pandoc.config import (
    PandocConfig,
    PandocConfigProvider,
)
from zeo_core.integrations.pandoc.converter import DocumentConverter
from zeo_core.integrations.pandoc.models import (
    ConversionTask,
    FileInfo,
)
from zeo_core.integrations.pandoc.operations.html_to_md import (
    post_process_markdown,
    validate_html_structure,
)
from zeo_core.integrations.pandoc.operations.utils import (
    get_file_info as util_get_file_info,
)
from zeo_core.integrations.pandoc.operations.utils import (
    prepare_pandoc_args,
    verify_pandoc,
)
from zeo_core.integrations.pandoc.service import PandocIntegration


# Fixtures for monkeypatching filesystem service
@pytest.fixture(autouse=True)
def fs_stub(monkeypatch: MonkeyPatch) -> Generator[SimpleNamespace, None, None]:
    """
    Stub out the zeo_core.core.fs.service.standalone methods for file _ops.
    """
    import zeo_core.core.fs.service as fs_service

    stub = SimpleNamespace()
    # Default get_file_info returns success, exists, size, modified
    stub.get_file_info = lambda path: SimpleNamespace(
        success=True, exists=True, size=100, modified=time.time()
    )
    stub.create_directory = lambda path, exist_ok: SimpleNamespace(success=True)
    # match os.path.join signature: first arg required, then *paths
    stub.join_path = lambda a, *parts: os.path.join(a, *parts)
    stub.split_path = lambda path: path.split(os.sep)
    stub.write_text = lambda path, content, encoding=None: SimpleNamespace(
        success=True, bytes_written=len(content)
    )
    stub.read_text = lambda path, encoding=None: SimpleNamespace(
        success=True, content="dummy content"
    )
    stub.get_extension = lambda path: SimpleNamespace(data=path.split(".")[-1])
    stub.get_path_info = lambda path: SimpleNamespace(success=True)
    stub.is_valid_path = lambda path: True
    stub.normalize_path = lambda p: SimpleNamespace(
        success=True, path=os.path.abspath(p)
    )
    stub.normalize_path_with_info = stub.normalize_path
    stub.get_file_size_str = lambda size: f"{size}B"
    monkeypatch.setattr(fs_service, "standalone", stub)

    # The line above alone does NOT reach every consumer: each pandoc module
    # binds its own local `fs` name at import time via
    # `from zeo_core.core.fs.service import standalone as fs`, so
    # reassigning fs_service.standalone after that import has already
    # happened never touches the already-bound local alias (mock-path-drift-fix
    # SOW-02 Finding 2). Patch the alias directly on every module that binds
    # it, so this fixture actually reaches all of them.
    import zeo_core.integrations.pandoc.config as _pandoc_config
    import zeo_core.integrations.pandoc.converter as _pandoc_converter
    import zeo_core.integrations.pandoc.operations.html_to_md as _pandoc_html_to_md
    import zeo_core.integrations.pandoc.operations.md_to_docx as _pandoc_md_to_docx
    import zeo_core.integrations.pandoc.operations.utils as _pandoc_utils

    for _mod in (
        _pandoc_config,
        _pandoc_converter,
        _pandoc_html_to_md,
        _pandoc_md_to_docx,
        _pandoc_utils,
    ):
        if hasattr(_mod, "fs"):
            monkeypatch.setattr(_mod, "fs", stub)

    yield stub


# Tests for verify_pandoc
def test_verify_pandoc_success(monkeypatch: MonkeyPatch) -> None:
    # Create a dummy pypandoc module
    dummy = types.ModuleType("pypandoc")
    # `get_pandoc_version` is not a static ModuleType attribute -- deliberate
    # dynamic monkeypatch of a synthetic module, bound through an Any-typed
    # local rather than ignored per-access.
    dummy_any: Any = dummy
    dummy_any.get_pandoc_version = lambda: "2.11"
    monkeypatch.setitem(sys.modules, "pypandoc", dummy)

    ver = verify_pandoc()
    assert ver == "2.11"


def test_verify_pandoc_import_error(monkeypatch: MonkeyPatch) -> None:
    # pypandoc (the Python wrapper) is genuinely installed in this
    # environment even though the `pandoc` binary is not, so deleting
    # "pypandoc" from sys.modules does not simulate "package not
    # installed" -- it just forces a fresh, successful re-import, which
    # then fails with OSError from the missing binary (a different branch
    # of verify_pandoc than this test intends to exercise). Patch
    # importlib.import_module directly to raise ImportError, matching the
    # technique test_utils.py::test_verify_pandoc_import_error already
    # uses correctly for the same function.
    import importlib

    def raise_import_error(name: str) -> None:
        raise ImportError(f"No module named '{name}'")

    monkeypatch.setattr(importlib, "import_module", raise_import_error)
    with pytest.raises(ZeoIntegrationError) as excinfo:
        verify_pandoc()
    assert "pypandoc module is not installed" in str(excinfo.value)


# Tests for prepare_pandoc_args
def test_prepare_pandoc_args_defaults() -> None:
    config = PandocConfig()
    args = prepare_pandoc_args(config, "html", "markdown", None)
    # Check core flags present
    assert "--wrap=none" in args
    assert "--standalone" in args
    assert "--markdown-headings=atx" in args
    # HTML to markdown extra args default
    assert "--strip-comments" in args
    assert "--no-highlight" in args


# Tests for util_get_file_info
def test_util_get_file_info_success() -> None:
    info = util_get_file_info("test.html", format_hint=None)
    assert isinstance(info, FileInfo)
    assert info.format == "html"
    assert info.size == 100


def test_util_get_file_info_not_found(monkeypatch: MonkeyPatch) -> None:
    # standalone.get_file_info's real signature returns FileInfoResult;
    # a SimpleNamespace duck-types it here for the test double. Deliberate
    # return-type widening, scoped through an Any-typed local rather than
    # ignored -- the callee only reads .success/.exists via getattr/hasattr.
    standalone_any: Any = zeo_core.core.fs.service.standalone
    standalone_any.get_file_info = lambda p: SimpleNamespace(
        success=False, exists=False
    )
    with pytest.raises(ZeoIntegrationError):
        util_get_file_info("missing.md")


# Tests for post_process_markdown
@pytest.mark.parametrize(
    "raw,expected_sub",
    [
        ("Text {remove} here", "Text  here"),
        ("Hello <!-- comment -->World", "Hello World"),
        ("<div>x</div>", "x"),
    ],
)
def test_post_process_markdown(raw: str, expected_sub: str) -> None:
    cleaned = post_process_markdown(raw)
    assert expected_sub in cleaned


# Tests for validate_html_structure
def test_validate_html_structure_valid() -> None:
    html = "<html><body><h1>Title</h1><p>Text</p></body></html>"
    valid, errors = validate_html_structure(html, check_links=False)
    assert valid and not errors


def test_validate_html_structure_missing_body() -> None:
    html = "<html><head></head></html>"
    valid, errors = validate_html_structure(html, check_links=False)
    assert not valid
    assert "missing body" in errors[0].lower()


def test_validate_html_structure_empty_links() -> None:
    html = '<html><body><a href=""></a></body></html>'
    valid, errors = validate_html_structure(html, check_links=True)
    assert not valid
    assert "empty links" in errors[0]


# Tests for DocumentConverter.convert_file
@pytest.fixture
def converter(monkeypatch: MonkeyPatch) -> DocumentConverter:
    # Inject our dummy pypandoc module for converter init
    dummy = types.ModuleType("pypandoc")
    # `get_pandoc_version` is not a static ModuleType attribute -- deliberate
    # dynamic monkeypatch of a synthetic module, bound through an Any-typed
    # local rather than ignored per-access.
    dummy_any: Any = dummy
    dummy_any.get_pandoc_version = lambda: "2.11"
    monkeypatch.setitem(sys.modules, "pypandoc", dummy)

    config = PandocConfig()
    return DocumentConverter(config)


def test_convert_file_html_to_md_success(
    converter: DocumentConverter, monkeypatch: MonkeyPatch
) -> None:
    # Stub file_info. converter.py imports get_file_info at module top level
    # from zeo_core.integrations.pandoc.operations (its own package-level
    # re-export), not from operations.utils directly -- patch the alias
    # actually consumed.
    monkeypatch.setattr(
        "zeo_core.integrations.pandoc.converter.get_file_info",
        lambda path: FileInfo(
            path=path, format="html", size=100, modified=None, extra_args=[]
        ),
    )
    # Stub conversion operation. converter.py's deferred import
    # (`from ...pandoc.operations import convert_html_to_markdown`) re-resolves
    # from the `operations` package's own already-bound re-export every call,
    # not from operations.html_to_md's origin -- patch that re-export.
    # convert_file unpacks a tuple content into its first element (see
    # converter.py's own "Unpack the returned tuple" comment) -- a list
    # content is passed through unchanged, so the mock must return a tuple
    # to match the real function's documented shape.
    monkeypatch.setattr(
        "zeo_core.integrations.pandoc.operations.convert_html_to_markdown",
        lambda i, o, cfg, m: IntegrationResult.success_result(("out.md", None)),
    )

    result = converter.convert_file("in.html", "out.md", "markdown")
    assert result.success
    assert result.content == "out.md"


def test_convert_file_unsupported(converter: DocumentConverter) -> None:
    # Stub file_info to unsupported format
    def fake_get(path: str, format_hint: str | None = None) -> FileInfo:
        return FileInfo(path=path, format="txt", size=0, modified=None, extra_args=[])

    import zeo_core.integrations.pandoc.operations.utils as utils_mod

    utils_mod.get_file_info = fake_get

    result = converter.convert_file("file.txt", "out.md", "markdown")
    assert not result.success
    assert result.error is not None
    assert "Unsupported conversion" in result.error


# Tests for DocumentConverter.convert_batch
def test_convert_batch_all_success(converter: DocumentConverter) -> None:
    # Stub convert_file to always succeed
    converter.convert_file = (  # type: ignore[method-assign]
        lambda input_path, output_path, output_format: IntegrationResult.success_result(
            output_path
        )
    )

    tasks = [
        ConversionTask(
            source=FileInfo(
                path="a.html", format="html", size=0, modified=None, extra_args=[]
            ),
            target_format="markdown",
            output_path="a.md",
        ),
        ConversionTask(
            source=FileInfo(
                path="b.html", format="html", size=0, modified=None, extra_args=[]
            ),
            target_format="markdown",
            output_path="b.md",
        ),
    ]
    result = converter.convert_batch(tasks)
    assert result.success
    assert result.content is not None
    assert set(result.content) == {"a.md", "b.md"}


def test_convert_batch_partial_failure(converter: DocumentConverter) -> None:
    # First succeeds, second fails
    def fake_convert(
        input_path: str, output_path: str, output_format: str | None = None
    ) -> IntegrationResult[str]:
        if input_path.endswith("fail.html"):
            return IntegrationResult.error_result("err")
        return IntegrationResult.success_result(output_path)

    converter.convert_file = fake_convert  # type: ignore[method-assign]

    tasks = [
        ConversionTask(
            source=FileInfo(
                path="ok.html", format="html", size=0, modified=None, extra_args=[]
            ),
            target_format="markdown",
            output_path="ok.md",
        ),
        ConversionTask(
            source=FileInfo(
                path="fail.html", format="html", size=0, modified=None, extra_args=[]
            ),
            target_format="markdown",
            output_path="fail.md",
        ),
    ]
    result = converter.convert_batch(tasks)
    assert result.success
    assert result.message is not None
    assert "Partially successful" in result.message
    assert result.content == ["ok.md"]


# Tests for PandocIntegration availability
def test_pandoc_integration_is_available(monkeypatch: MonkeyPatch) -> None:
    import zeo_core.integrations.pandoc.service as service_mod

    # inject dummy module
    monkeypatch.setattr(service_mod, "verify_pandoc", lambda: "2.11")

    integration = PandocIntegration()
    assert integration.is_pandoc_available()
    assert integration.get_pandoc_version() == "2.11"


def test_pandoc_integration_not_available(monkeypatch: MonkeyPatch) -> None:
    import zeo_core.integrations.pandoc.service as service_mod
    from zeo_core.core.errors import ZeoIntegrationError

    monkeypatch.setattr(
        service_mod,
        "verify_pandoc",
        lambda: (_ for _ in ()).throw(ZeoIntegrationError("fail", {})),
    )

    integration = PandocIntegration()
    assert not integration.is_pandoc_available()
    assert integration.get_pandoc_version() is None


# Tests for Config
def test_pandoc_config_default() -> None:
    config = PandocConfig()
    assert config.output_dir == "./output"
    assert isinstance(config.pandoc_options.wrap, str)


def test_pandoc_config_validate_output_dir(monkeypatch: MonkeyPatch) -> None:
    # Invalidate path
    # Same deliberate return-type widening as test_util_get_file_info_not_found
    # above -- standalone.get_path_info's real return type is PathResult.
    standalone_path_any: Any = zeo_core.core.fs.service.standalone
    standalone_path_any.get_path_info = lambda p: SimpleNamespace(
        success=False
    )
    with pytest.raises(ValueError):
        PandocConfig(output_dir="??invalid")


# Tests for ConfigProvider
def test_config_provider_validate_config(monkeypatch: MonkeyPatch) -> None:
    provider = PandocConfigProvider()
    # valid schema
    assert provider.validate_config({"output_dir": "/tmp"}) is not False  # noqa: S108 -- path used only inside mocked/patched I/O, never touches real filesystem
    # test invalid path: validate_config's real, current contract (config.py)
    # checks basic string validity and a forbidden-character set
    # (?, *, <, >, |) -- it never calls is_valid_path, so setting that stub
    # has no effect on the outcome. Exercise the actual gate instead.
    assert not provider.validate_config({"output_dir": "in*valid?"})


def test_config_provider_get_default_and_env(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    provider = PandocConfigProvider()
    # normalize default
    cfg_default = provider.get_default_config()
    assert "output_dir" in cfg_default

    # load from environment
    monkeypatch.setenv("ZEO_PANDOC_OUTPUT_DIR", str(tmp_path))
    cfg_env = provider.load_from_environment()
    assert cfg_env.get("output_dir") == os.path.abspath(str(tmp_path))
