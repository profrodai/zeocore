# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/pandoc/test_service.py
# === QV-LLM:END ===

"""
Tests for the pandoc integration service.

This module contains unit tests for the PandocIntegration service class
that provides document conversion functionality.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from quack_core.core.errors import QuackIntegrationError
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.pandoc.service import PandocIntegration


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


@patch("quack_core.core.fs.service.standalone.expand_user_vars")
@patch("quack_core.integrations.pandoc.service.verify_pandoc")
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


@patch("quack_core.integrations.pandoc.service.verify_pandoc")
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
    mock_verify_pandoc.side_effect = QuackIntegrationError("Pandoc not found", {})

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
        "quack_core.integrations.pandoc.service.verify_pandoc", return_value="2.11.0"
    ):
        assert integration.is_pandoc_available()
        assert integration.get_pandoc_version() == "2.11.0"

    # Mock verify_pandoc to fail
    with patch(
        "quack_core.integrations.pandoc.service.verify_pandoc",
        side_effect=QuackIntegrationError("Pandoc not found", {}),
    ):
        assert not integration.is_pandoc_available()


@patch("quack_core.core.fs.service.standalone.expand_user_vars")
@patch("quack_core.integrations.pandoc.service.verify_pandoc")
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


@patch("quack_core.core.fs.service.standalone.expand_user_vars")
@patch("quack_core.integrations.pandoc.service.verify_pandoc")
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


@patch("quack_core.core.fs.service.standalone.expand_user_vars")
@patch("quack_core.integrations.pandoc.service.verify_pandoc")
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


@patch("quack_core.integrations.pandoc.service.verify_pandoc")
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

    from quack_core.core.fs.service import FileSystemService

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


@patch("quack_core.integrations.pandoc.service.verify_pandoc")
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

    from quack_core.core.fs.service import FileSystemService

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
