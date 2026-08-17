"""
Tests for the pandoc integration service.

This module contains unit tests for the PandocIntegration service class
that provides document conversion functionality.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from zeo_core.core.errors import ZeoIntegrationError
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.pandoc.service import PandocIntegration, create_integration


@pytest.fixture
def setup_mocks(
    fs_stub: SimpleNamespace, mock_paths_service: MagicMock
) -> tuple[SimpleNamespace, MagicMock]:
    """Shared setup for service tests."""
    if not isinstance(mock_paths_service, MagicMock):
        mock_paths_service = MagicMock()

    mock_paths_service.expand_user_vars = MagicMock(side_effect=lambda x: x)
    mock_paths_service.resolve_project_path = MagicMock(
        side_effect=lambda x: SimpleNamespace(success=True, path=x)
    )

    # Setup fs_stub methods
    fs_stub.get_path_info = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.normalize_path_with_info = MagicMock(
        return_value=SimpleNamespace(success=True, path="output")
    )
    fs_stub.create_directory = MagicMock(return_value=SimpleNamespace(success=True))
    # Fix for expand_user_vars missing
    fs_stub.expand_user_vars = MagicMock(
        side_effect=lambda x: SimpleNamespace(success=True, data=x)
    )
    # Ensure find_files exists
    fs_stub.find_files = MagicMock(return_value=SimpleNamespace(success=True, files=[]))
    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=False, size=100)
    )

    return fs_stub, mock_paths_service


def test_pandoc_integration_name_version() -> None:
    """Test basic properties of PandocIntegration."""
    integration = PandocIntegration()
    assert integration.name == "Pandoc"
    assert integration.version == "1.0.0"
    assert not integration._initialized


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_initialize_with_mocked_verify_pandoc(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Test initialize method with mocked verify_pandoc."""
    fs_stub, mock_paths_service = setup_mocks

    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]  # SimpleNamespace duck-types FileSystemService for this test double
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )

    result = integration.initialize()

    assert result.success
    assert integration._initialized
    assert integration._pandoc_version == "2.11.0"
    assert integration.converter is not None


@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_initialize_with_verify_pandoc_error(
    mock_verify_pandoc: MagicMock, setup_mocks: tuple[SimpleNamespace, MagicMock]
) -> None:
    """Test initialize method when verify_pandoc raises an error."""
    fs_stub, mock_paths_service = setup_mocks

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    # We must assign fs_service for initialization cleanup/logic even if it fails early
    integration.fs_service = fs_stub  # type: ignore[assignment]  # SimpleNamespace duck-types FileSystemService for this test double

    # Mock verify_pandoc to raise an error
    mock_verify_pandoc.side_effect = ZeoIntegrationError("Pandoc not found", {})

    result = integration.initialize()

    assert not result.success
    assert not integration._initialized


def test_html_to_markdown_not_initialized() -> None:
    """Test HTML to Markdown conversion when service is not initialized."""
    integration = PandocIntegration()
    result = integration.html_to_markdown("input.html", "output.md")

    assert not result.success
    assert result.error is not None
    assert "not initialized" in result.error


def test_markdown_to_docx_not_initialized() -> None:
    """Test Markdown to DOCX conversion when service is not initialized."""
    integration = PandocIntegration()
    result = integration.markdown_to_docx("input.md", "output.docx")

    assert not result.success
    assert result.error is not None
    assert "not initialized" in result.error


def test_convert_directory_not_initialized() -> None:
    """Test directory conversion when service is not initialized."""
    integration = PandocIntegration()
    result = integration.convert_directory("input_dir", "markdown")

    assert not result.success
    assert result.error is not None
    assert "not initialized" in result.error


def test_is_pandoc_available() -> None:
    """Test is_pandoc_available method."""
    integration = PandocIntegration()

    # Mock verify_pandoc to succeed
    with patch(
        "zeo_core.integrations.pandoc.service.verify_pandoc", return_value="2.11.0"
    ):
        assert integration.is_pandoc_available()
        assert integration.get_pandoc_version() == "2.11.0"

    # Mock verify_pandoc to fail
    with patch(
        "zeo_core.integrations.pandoc.service.verify_pandoc",
        side_effect=ZeoIntegrationError("Pandoc not found", {}),
    ):
        assert not integration.is_pandoc_available()


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_html_to_markdown_with_initialized_service(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Test HTML to Markdown conversion with initialized service."""
    fs_stub, mock_paths_service = setup_mocks

    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]  # SimpleNamespace duck-types FileSystemService for this test double
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )

    # Initialize the service
    integration.initialize()

    # Mock the converter
    mock_result: IntegrationResult[str] = IntegrationResult(
        success=True, content="output.md"
    )
    mock_convert_file = MagicMock(return_value=mock_result)

    assert integration.converter is not None
    integration.converter.convert_file = mock_convert_file  # type: ignore[method-assign]

    # Test with output path
    result = integration.html_to_markdown("input.html", "output.md")
    assert result.success
    assert mock_convert_file.call_count == 1

    # Test without output path
    result = integration.html_to_markdown("input.html")
    assert result.success
    assert mock_convert_file.call_count == 2


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_markdown_to_docx_with_initialized_service(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Test Markdown to DOCX conversion with initialized service."""
    fs_stub, mock_paths_service = setup_mocks

    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]  # SimpleNamespace duck-types FileSystemService for this test double
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )

    # Initialize the service
    integration.initialize()

    # Mock the converter
    mock_result: IntegrationResult[str] = IntegrationResult(
        success=True, content="output.docx"
    )
    mock_convert_file = MagicMock(return_value=mock_result)

    assert integration.converter is not None
    integration.converter.convert_file = mock_convert_file  # type: ignore[method-assign]

    # Test with output path
    result = integration.markdown_to_docx("input.md", "output.docx")
    assert result.success
    assert mock_convert_file.call_count == 1

    # Test without output path
    result = integration.markdown_to_docx("input.md")
    assert result.success
    assert mock_convert_file.call_count == 2


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_convert_directory_with_initialized_service(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Test directory conversion with initialized service."""
    fs_stub, mock_paths_service = setup_mocks

    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]  # SimpleNamespace duck-types FileSystemService for this test double
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )

    # Add directory-specific mocks to fs_service
    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=True)
    )
    fs_stub.find_files = MagicMock(
        return_value=SimpleNamespace(success=True, files=["file1.html", "file2.html"])
    )

    # Initialize the service
    integration.initialize()

    # Mock the converter
    mock_result: IntegrationResult[list[str]] = IntegrationResult(
        success=True, content=["output1.md", "output2.md"]
    )
    mock_convert_batch = MagicMock(return_value=mock_result)

    assert integration.converter is not None
    integration.converter.convert_batch = mock_convert_batch  # type: ignore[method-assign]

    # Test with default parameters
    result = integration.convert_directory("input_dir", "markdown")
    assert result.success
    assert mock_convert_batch.call_count == 1

    # Test with custom parameters
    result = integration.convert_directory(
        "input_dir", "markdown", "custom_output", "*.html"
    )
    assert result.success
    assert mock_convert_batch.call_count == 2


@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_convert_directory_find_files_real_fs_service(
    mock_verify_pandoc: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RULING-239: convert_directory's find_files call against the REAL
    FileSystemService, not a mock/SimpleNamespace.

    Before the fix, convert_directory called
    self.fs_service.find_files(directory=input_dir, pattern=pattern) --
    but the real FileSystemService.find_files signature is
    find_files(path, pattern, ...), no `directory` kwarg. Every existing
    convert_directory test replaces fs_service with a MagicMock/
    SimpleNamespace whose find_files accepts arbitrary kwargs, so the
    TypeError this call raises against the real service was never caught.
    This test uses a REAL FileSystemService (sandboxed to tmp_path via
    monkeypatch.chdir, matching the module-level `fs` singleton's own
    default cwd-sandbox used by pandoc.operations.utils.get_file_info) so
    a regression back to `directory=` fails loudly with the exact
    TypeError this ruling fixed, instead of being silently absorbed by a
    permissive test double.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.html").write_text("<p>hello</p>")
    (tmp_path / "b.html").write_text("<p>world</p>")

    from zeo_core.core.fs.service import FileSystemService

    mock_verify_pandoc.return_value = "2.11.0"

    integration = PandocIntegration()
    integration.fs_service = FileSystemService()  # REAL service, not a mock/stub
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )

    init_result = integration.initialize()
    assert init_result.success, init_result.error

    # The call under test: convert_directory -> self.fs_service.find_files(...).
    # Exercised directly against the real service's find_files to prove the
    # kwarg name is correct.
    find_result = integration.fs_service.find_files(
        path=str(tmp_path), pattern="*.html"
    )
    assert find_result.success, find_result.error
    assert len(find_result.files) == 2

    # Regression guard on convert_directory ITSELF, not just the isolated
    # find_files call above: convert_directory's own try/except swallows any
    # exception from the find_files call and stuffs the message into
    # result.error -- so `directory=input_dir` regressing back in would NOT
    # raise here, it would surface as this exact TypeError text in
    # result.error. Assert that text is ABSENT (proving the correct kwarg
    # reached the real service) rather than asserting overall success --
    # full pipeline success is gated by a separate, NOT-yet-authorized
    # finding (RULING-239 s1.4: the list[Path]/list[str] mismatch in
    # _build_conversion_tasks causes every file to fail get_file_info
    # downstream of a working find_files call, confirmed live this round,
    # reported but not fixed here). Falsified: reverting the kwarg to
    # `directory=` while keeping this assertion makes it fail with exactly
    # "unexpected keyword argument 'directory'" in result.error.
    result = integration.convert_directory(str(tmp_path), "markdown", pattern="*.html")
    assert "unexpected keyword argument 'directory'" not in (result.error or "")


@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_convert_directory_builds_real_tasks_multi_file(
    mock_verify_pandoc: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RULING-241: find_result.files (list[Path], from the real, non-mocked
    FileSystemService) must reach _build_conversion_tasks's list[str]-typed
    pipeline as actual strings, or every file fails get_file_info's strict
    pydantic FileInfo.path field with a ValidationError.

    Before this fix, service.py:496 assigned find_result.files (list[Path])
    straight to input_files with no coercion. get_file_info (operations/
    utils.py) types its own `path` param `str` but performs no coercion
    before constructing FileInfo(path=path, ...), whose `path` field is a
    strict pydantic str -- so a real PosixPath blew up with
    `pydantic.ValidationError: Input should be a valid string`. This was
    unreachable until RULING-239's own find_files-kwarg fix landed (before
    that, find_files itself raised TypeError first) -- confirmed live,
    100%-reproducing, in SOW-29 s2, against a real, non-mocked
    FileSystemService with 2 real files. This test exercises THREE real
    files (RULING-241 s1.4's own "multiple, to catch any per-file edge
    case" requirement) and asserts tasks are actually built -- non-empty,
    correctly shaped -- not merely that no exception fires.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.html").write_text("<p>alpha</p>")
    (tmp_path / "b.html").write_text("<p>bravo</p>")
    (tmp_path / "c.html").write_text("<p>charlie</p>")

    from zeo_core.core.fs.service import FileSystemService

    mock_verify_pandoc.return_value = "2.11.0"

    integration = PandocIntegration()
    integration.fs_service = FileSystemService()  # REAL service, not a mock/stub
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )

    init_result = integration.initialize()
    assert init_result.success, init_result.error

    # Level 1: the real find_files call genuinely returns list[Path], not
    # list[str] -- confirms the input shape that must be coerced.
    find_result = integration.fs_service.find_files(
        path=str(tmp_path), pattern="*.html"
    )
    assert find_result.success, find_result.error
    assert len(find_result.files) == 3
    assert all(isinstance(p, Path) for p in find_result.files)

    # Confirms _build_conversion_tasks's list[str] annotation is honored, not
    # loosened (RULING-241 s1.2/1.3 forbid widening it): fed the RAW Path
    # objects find_files actually produces, it still fails every file --
    # get_file_info's strict pydantic FileInfo.path field rejects a
    # PosixPath. This is the correct, unchanged behavior of that function;
    # the fix belongs at the CALLER (service.py:496), proven next.
    # Deliberate list[Path]-into-list[str] mismatch below, ignored on
    # purpose: proving the annotation is honored (not silently widened) when
    # fed real, un-coerced Path input, per RULING-241 s1.2/1.3.
    raw_tasks = integration._build_conversion_tasks(find_result.files, "markdown", {})  # type: ignore[arg-type]
    assert raw_tasks == [], (
        "sanity check: _build_conversion_tasks must still reject raw Path "
        "input un-coerced -- if this now passes, someone widened its "
        "list[str] contract or added internal coercion, which RULING-241 "
        "s1.2/1.3 explicitly forbid. The coercion belongs at the caller."
    )

    # Level 2/3/4: the ACTUAL fix, service.py:496's str() coercion inside
    # convert_directory, feeding _build_conversion_tasks real strings. This
    # is the exact code path RULING-241 authorizes and requires proof for --
    # real find_files output, through the real coercion, into real task
    # construction. Asserts tasks are actually built (non-empty, correctly
    # shaped), not merely that no exception fires.
    result = integration.convert_directory(str(tmp_path), "markdown", pattern="*.html")
    assert result.error != "No valid conversion tasks could be created", result.error

    coerced_tasks = integration._build_conversion_tasks(
        [str(p) for p in find_result.files], "markdown", {}
    )
    assert len(coerced_tasks) == 3, (
        "expected 3 real ConversionTasks once find_result.files is coerced "
        "to str at the call site, matching what convert_directory's own "
        "fixed line 496 now does; an empty list here means the "
        "ValidationError is still firing -- the only visible symptom, "
        "since _build_conversion_tasks's except Exception swallows it."
    )
    built_names = {Path(task.source.path).name for task in coerced_tasks}
    assert built_names == {"a.html", "b.html", "c.html"}
    for task in coerced_tasks:
        assert task.source.format == "html"
        assert task.target_format == "markdown"


def test_init_fs_service_cwd_failure_falls_back_to_tempdir() -> None:
    """Covers service.py:80-87 -- if the real FileSystemService() constructor
    raises FileNotFoundError/OSError (e.g. because Path.cwd() fails, which
    happens when the process's cwd has been deleted -- a documented real
    scenario in tests), __init__ must catch it and construct a fallback
    FileSystemService rooted at tempfile.gettempdir() instead of propagating.
    """
    import tempfile

    from zeo_core.core.fs.service import FileSystemService as RealFsService

    call_count = 0
    original_init = RealFsService.__init__

    def fake_init(self: RealFsService, *args: object, **kwargs: object) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Simulate the first construction attempt (no base_dir override)
            # failing because cwd() is unavailable.
            raise FileNotFoundError("cwd is gone")
        original_init(self, *args, **kwargs)  # type: ignore[arg-type]

    with patch.object(RealFsService, "__init__", fake_init):
        integration = PandocIntegration()

    assert integration.fs_service is not None
    assert integration.fs_service.base_dir == Path(tempfile.gettempdir()).resolve()


def test_resolve_path_str_failure_returns_original() -> None:
    """Covers service.py:141 -- when paths_service.resolve_project_path()
    reports failure (or a None path even on success), _resolve_path_str
    falls back to returning the original, unresolved path string unchanged.
    """
    integration = PandocIntegration()
    integration.paths_service = MagicMock()
    integration.paths_service.resolve_project_path = MagicMock(
        return_value=SimpleNamespace(success=False, path=None)
    )

    result = integration._resolve_path_str("some/relative/path.html")
    assert result == "some/relative/path.html"

    # Also cover the "success but path is None" sub-case of the same branch.
    integration.paths_service.resolve_project_path = MagicMock(
        return_value=SimpleNamespace(success=True, path=None)
    )
    result = integration._resolve_path_str("another/path.html")
    assert result == "another/path.html"


def test_require_config_provider_raises_when_none() -> None:
    """Covers service.py:150-154 -- _require_config_provider must raise
    ZeoIntegrationError if self.config_provider is ever None, defending
    an invariant __init__ is supposed to guarantee (a concrete
    PandocConfigProvider is always constructed).
    """
    integration = PandocIntegration()
    integration.config_provider = None

    with pytest.raises(ZeoIntegrationError, match="unexpectedly None"):
        integration._require_config_provider()


@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_initialize_config_provider_none_returns_error_result(
    mock_verify_pandoc: MagicMock, setup_mocks: tuple[SimpleNamespace, MagicMock]
) -> None:
    """Covers service.py:182, 207-211 -- initialize()'s config-loading try
    block calls _require_config_provider(); if config_provider was somehow
    reset to None, that raises ZeoIntegrationError, which the surrounding
    except Exception in initialize() must catch and turn into a structured
    error IntegrationResult (not propagate).
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    integration.config_provider = None

    result = integration.initialize()

    assert not result.success
    assert not integration._initialized
    assert result.error is not None
    assert "Invalid configuration" in result.error


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_initialize_expand_user_vars_failure_falls_back_to_original(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:223-225 -- if fs_service.expand_user_vars() reports
    failure (success=False) or returns no data, initialize() falls back to
    using the original, unexpanded output_dir string for directory creation
    instead of the (unusable) expansion result.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    fs_stub.expand_user_vars = MagicMock(
        return_value=SimpleNamespace(success=False, data=None)
    )
    created_dirs: list[str] = []

    def _record_create_directory(path: str, **kw: object) -> SimpleNamespace:
        created_dirs.append(path)
        return SimpleNamespace(success=True)

    fs_stub.create_directory = MagicMock(side_effect=_record_create_directory)

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(
            success=True, content={"output_dir": "~/some_output"}
        )
    )

    result = integration.initialize()

    assert result.success, result.error
    assert created_dirs == ["~/some_output"]


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_initialize_create_directory_failure_returns_error_result(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:229-237 -- if fs_service.create_directory() reports
    failure, initialize() must surface a structured error IntegrationResult
    (with the underlying create_result.error message included) and leave
    _initialized False, rather than proceeding to converter setup.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    fs_stub.create_directory = MagicMock(
        return_value=SimpleNamespace(success=False, error="disk full")
    )

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(
            success=True, content={"output_dir": "some_output"}
        )
    )

    result = integration.initialize()

    assert not result.success
    assert not integration._initialized
    assert result.error is not None
    assert "disk full" in result.error


@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_initialize_filesystem_setup_unexpected_exception(
    mock_verify_pandoc: MagicMock, setup_mocks: tuple[SimpleNamespace, MagicMock]
) -> None:
    """Covers service.py:241-245 -- an unexpected exception raised anywhere
    in the "Setup File System" try block (e.g. from expand_user_vars itself
    raising rather than returning a failure result) must be caught and
    turned into a structured error IntegrationResult.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"

    fs_stub.expand_user_vars = MagicMock(side_effect=RuntimeError("expand blew up"))

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(
            success=True, content={"output_dir": "some_output"}
        )
    )

    result = integration.initialize()

    assert not result.success
    assert not integration._initialized
    assert result.error is not None
    assert "File system initialization failed" in result.error
    assert "expand blew up" in result.error


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_initialize_converter_construction_failure(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:260-265 -- an unexpected exception raised while
    constructing the DocumentConverter (final initialization step) must be
    caught and turned into a structured error IntegrationResult, leaving
    _initialized False.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )

    with patch(
        "zeo_core.integrations.pandoc.service.DocumentConverter",
        side_effect=RuntimeError("converter blew up"),
    ):
        result = integration.initialize()

    assert not result.success
    assert not integration._initialized
    assert result.error is not None
    assert "Failed to initialize converter" in result.error


def test_is_available_false_when_not_initialized() -> None:
    """Covers service.py:273 -- is_available() returns False when the
    integration has not been initialized (converter is None)."""
    integration = PandocIntegration()
    assert integration.is_available() is False


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_is_available_true_after_successful_initialize(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:273 -- is_available() returns True once the
    integration is successfully initialized and has a converter."""
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )

    integration.initialize()
    assert integration.is_available() is True


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_html_to_markdown_converter_raises_exception(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:330-333 -- an unexpected exception raised by
    converter.convert_file() (or path resolution) inside html_to_markdown
    must be caught and turned into a structured error IntegrationResult.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )
    integration.initialize()

    assert integration.converter is not None
    integration.converter.convert_file = MagicMock(  # type: ignore[method-assign]
        side_effect=RuntimeError("conversion exploded")
    )

    result = integration.html_to_markdown("input.html", "output.md")

    assert not result.success
    assert result.error is not None
    assert "HTML to Markdown conversion failed" in result.error
    assert "conversion exploded" in result.error


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_markdown_to_docx_converter_raises_exception(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:368-371 -- an unexpected exception raised by
    converter.convert_file() (or path resolution) inside markdown_to_docx
    must be caught and turned into a structured error IntegrationResult.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )
    integration.initialize()

    assert integration.converter is not None
    integration.converter.convert_file = MagicMock(  # type: ignore[method-assign]
        side_effect=RuntimeError("conversion exploded")
    )

    result = integration.markdown_to_docx("input.md", "output.docx")

    assert not result.success
    assert result.error is not None
    assert "Markdown to DOCX conversion failed" in result.error
    assert "conversion exploded" in result.error


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_convert_directory_path_is_not_a_directory(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:407-411 -- _verify_convert_directory returns an
    error IntegrationResult when the resolved input path exists but is not
    a directory (e.g. a plain file was passed as input_dir).
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=False)
    )

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )
    integration.initialize()

    result = integration.convert_directory("not_a_dir.html", "markdown")

    assert not result.success
    assert result.error is not None
    assert "Path is not a directory" in result.error


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_convert_directory_no_valid_tasks(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:510-514 -- when files ARE found matching the
    pattern but every one of them fails to yield a ConversionTask (e.g.
    get_file_info raises for each), convert_directory returns an explicit
    "No valid conversion tasks could be created" error rather than trying
    to hand an empty task list to the converter.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=True)
    )
    fs_stub.find_files = MagicMock(
        return_value=SimpleNamespace(success=True, files=["file1.html"])
    )

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )
    integration.initialize()

    with patch(
        "zeo_core.integrations.pandoc.operations.get_file_info",
        side_effect=RuntimeError("cannot stat file"),
    ):
        result = integration.convert_directory("input_dir", "markdown")

    assert not result.success
    assert result.error is not None
    assert "No valid conversion tasks could be created" in result.error


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_convert_directory_unexpected_exception(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:519-522 -- an unexpected exception raised anywhere
    in convert_directory's main try block (here, from find_files itself)
    must be caught and turned into a structured error IntegrationResult.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=True)
    )
    fs_stub.find_files = MagicMock(side_effect=RuntimeError("find_files exploded"))

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )
    integration.initialize()

    result = integration.convert_directory("input_dir", "markdown")

    assert not result.success
    assert result.error is not None
    assert "Directory conversion failed" in result.error
    assert "find_files exploded" in result.error


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_initialize_config_load_failure_warns_but_continues(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:188-189 -- if config_provider.load_config() reports
    failure, initialize() logs a warning but continues (config_dict falls
    back to {} via `config_result.content or {}`), rather than treating it
    as fatal.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(
            success=False, error="config file missing", content=None
        )
    )

    result = integration.initialize()

    # Failure to load config is non-fatal: PandocConfig() builds fine from
    # an empty dict, so initialization still succeeds overall.
    assert result.success, result.error
    assert integration._initialized


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_initialize_output_dir_override_applied(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:195-196 -- passing output_dir to the constructor
    overrides whatever output_dir (if any) came from loaded config, by
    writing directly into config_dict before PandocConfig validation.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    created_dirs: list[str] = []

    def _record_create_directory(path: str, **kw: object) -> SimpleNamespace:
        created_dirs.append(path)
        return SimpleNamespace(success=True)

    fs_stub.create_directory = MagicMock(side_effect=_record_create_directory)

    integration = PandocIntegration(output_dir="overridden_output")
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(
            success=True, content={"output_dir": "config_output"}
        )
    )

    result = integration.initialize()

    assert result.success, result.error
    assert created_dirs == ["overridden_output"]


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_html_to_markdown_converter_none_after_initialized(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:323-327 -- defensive guard: if the integration is
    somehow marked _initialized=True but self.converter is None (an
    invariant violation that should never happen via the public API), the
    resulting ZeoIntegrationError must be caught by html_to_markdown's own
    except block and surfaced as a structured error result.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )
    integration.initialize()
    integration.converter = None  # force the invariant violation

    result = integration.html_to_markdown("input.html", "output.md")

    assert not result.success
    assert result.error is not None
    assert "converter is unexpectedly None" in result.error


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_markdown_to_docx_converter_none_after_initialized(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:361-365 -- same defensive guard as html_to_markdown,
    exercised for markdown_to_docx: converter is None despite _initialized
    being True, the resulting ZeoIntegrationError is caught and surfaced
    as a structured error result.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )
    integration.initialize()
    integration.converter = None  # force the invariant violation

    result = integration.markdown_to_docx("input.md", "output.docx")

    assert not result.success
    assert result.error is not None
    assert "converter is unexpectedly None" in result.error


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_convert_directory_converter_none_after_initialized(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """RULING-274 s2 (round 25): same defensive guard as
    html_to_markdown/markdown_to_docx above, exercised for
    convert_directory (service.py:517-521). initialize()'s own success
    path sets self.converter and self._initialized=True atomically
    (service.py:249-252), so this invariant violation cannot occur via the
    public API -- forced directly here, same discipline as the two sibling
    tests immediately above. Unlike html_to_markdown/markdown_to_docx,
    convert_directory has no dedicated `except ZeoIntegrationError`
    clause -- the raise is caught by its own generic `except Exception`
    (service.py:519-522) and surfaced with the "Directory conversion
    failed" prefix.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )

    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=True)
    )
    fs_stub.find_files = MagicMock(
        return_value=SimpleNamespace(success=True, files=["file1.html"])
    )

    integration.initialize()
    integration.converter = None  # force the invariant violation

    result = integration.convert_directory("input_dir", "markdown")

    assert not result.success
    assert result.error is not None
    assert "converter is unexpectedly None" in result.error


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_convert_directory_input_dir_not_found(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:400-405 -- _verify_convert_directory returns an
    error IntegrationResult when the resolved input path does not exist
    (get_file_info reports success but exists=False, or reports failure).
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=False, is_dir=False)
    )

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )
    integration.initialize()

    result = integration.convert_directory("missing_dir", "markdown")

    assert not result.success
    assert result.error is not None
    assert "Input directory not found" in result.error


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_convert_directory_find_files_reports_failure(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:490-494 -- when fs_service.find_files() itself
    returns success=False (as opposed to raising), convert_directory returns
    a structured "Failed to find files" error result.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=True)
    )
    fs_stub.find_files = MagicMock(
        return_value=SimpleNamespace(success=False, error="glob failed", files=None)
    )

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )
    integration.initialize()

    result = integration.convert_directory("input_dir", "markdown")

    assert not result.success
    assert result.error is not None
    assert "Failed to find files" in result.error
    assert "glob failed" in result.error


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_convert_directory_no_files_found_matching_pattern(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Covers service.py:502-505 -- when find_files succeeds but returns no
    files at all, convert_directory short-circuits with a successful,
    empty-content IntegrationResult rather than attempting task building.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    fs_stub.get_file_info = MagicMock(
        return_value=SimpleNamespace(success=True, exists=True, is_dir=True)
    )
    fs_stub.find_files = MagicMock(return_value=SimpleNamespace(success=True, files=[]))

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )
    integration.initialize()

    result = integration.convert_directory("input_dir", "markdown")

    assert result.success
    assert result.content == []
    assert result.message == "No files found matching pattern"


def test_create_integration_factory_function() -> None:
    """Covers service.py:535 -- the create_integration() factory function
    forwards kwargs to PandocIntegration's constructor and returns an
    instance.
    """
    integration = create_integration()
    assert isinstance(integration, PandocIntegration)
    assert integration.name == "Pandoc"

    integration_with_output = create_integration(output_dir="custom_output")
    assert integration_with_output._init_output_dir == "custom_output"


def test_default_output_path_same_dir_same_basename_target_extension() -> None:
    """Covers service.py's _default_output_path -- RULING-277 Bug 4: when a
    caller omits output_path, html_to_markdown/markdown_to_docx must
    synthesize one in the same directory as input_path, with the same base
    filename and the target format's own extension, rather than letting
    output_path=None reach DocumentConverter.convert_file (which requires
    str and previously raised TypeError for real, unmocked callers).
    """
    integration = PandocIntegration()

    assert (
        integration._default_output_path("/some/dir/report.html", ".md")
        == "/some/dir/report.md"
    )
    assert (
        integration._default_output_path("docs/notes.md", ".docx") == "docs/notes.docx"
    )
    # No directory component at all -- os.path.dirname("") is "", and
    # os.path.join("", ...) still yields the correct same-dir-as-input result.
    assert integration._default_output_path("report.html", ".md") == "report.md"


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_html_to_markdown_output_path_none_synthesizes_real_default(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """RULING-277 Bug 4 regression: calling html_to_markdown with no
    output_path must not let None reach convert_file. Only convert_file
    itself is a spy (no real pandoc binary is available in this test
    environment); the output_path synthesis (_default_output_path) is the
    real, unmocked production code under test here -- the exact newly-
    guarded branch, exercised the way this chain's own precedent
    (test_resolve_file_details_mime_type_fallback, google-drive cluster,
    commit f85dc26b) tests a guarded branch rather than leaving it dead.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )
    integration.initialize()

    assert integration.converter is not None
    mock_convert_file = MagicMock(
        return_value=IntegrationResult(success=True, content="input.md")
    )
    integration.converter.convert_file = mock_convert_file  # type: ignore[method-assign]

    result = integration.html_to_markdown("some/dir/input.html")

    assert result.success
    mock_convert_file.assert_called_once_with(
        "some/dir/input.html", "some/dir/input.md", "markdown"
    )


@patch("zeo_core.core.fs.service.standalone.expand_user_vars")
@patch("zeo_core.integrations.pandoc.service.verify_pandoc")
def test_markdown_to_docx_output_path_none_synthesizes_real_default(
    mock_verify_pandoc: MagicMock,
    mock_expand_user_vars: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """RULING-277 Bug 4 regression, markdown_to_docx twin of the
    html_to_markdown test above: no output_path must synthesize a real
    default (same dir, same basename, .docx extension) rather than let None
    reach convert_file.
    """
    fs_stub, mock_paths_service = setup_mocks
    mock_verify_pandoc.return_value = "2.11.0"
    mock_expand_user_vars.side_effect = lambda x: x

    integration = PandocIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )
    integration.initialize()

    assert integration.converter is not None
    mock_convert_file = MagicMock(
        return_value=IntegrationResult(success=True, content="input.docx")
    )
    integration.converter.convert_file = mock_convert_file  # type: ignore[method-assign]

    result = integration.markdown_to_docx("some/dir/input.md")

    assert result.success
    mock_convert_file.assert_called_once_with(
        "some/dir/input.md", "some/dir/input.docx", "docx"
    )
