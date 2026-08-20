from types import SimpleNamespace
from unittest.mock import MagicMock

from _pytest.monkeypatch import MonkeyPatch

from zeo_core.integrations.core.results import ConfigResult, IntegrationResult
from zeo_core.integrations.jupytext.service import (
    JupytextIntegration,
    create_integration,
)


def _mock_paths_service() -> MagicMock:
    """A MagicMock standing in for PathService, matching pandoc's own
    test_service.py precedent (MagicMock duck-types the real service
    without a `# type: ignore[assignment]` at every call site, unlike a
    SimpleNamespace)."""
    mock = MagicMock()
    mock.resolve_project_path.side_effect = lambda path: SimpleNamespace(
        success=True, path=path
    )
    return mock


def _make_initialized_integration(
    fs_stub: SimpleNamespace,
) -> tuple[JupytextIntegration, MagicMock]:
    """Build a JupytextIntegration with mocked config/paths/fs services and
    call initialize(), mirroring pandoc's test_service.py instantiation
    pattern (assign mocks onto the instance, then initialize()).

    Returns the integration AND the fs_service mock as a separate reference
    -- reading `integration.fs_service` back after assignment resolves to
    the class's declared `FileSystemService` type under mypy (crossing the
    return-value boundary loses the narrower runtime type), so callers that
    need to reconfigure fs_service mock behavior must do it through this
    returned reference, matching how pandoc's own tests always reconfigure
    through the local `fs_stub`/`mock_paths_service` fixture variable rather
    than through `integration.fs_service.*` after the fact.
    """
    integration = JupytextIntegration()
    integration.paths_service = _mock_paths_service()
    fs_service_mock = MagicMock()
    integration.fs_service = fs_service_mock
    fs_service_mock.expand_user_vars.return_value = SimpleNamespace(
        success=True, data="./output"
    )
    fs_service_mock.create_directory.return_value = SimpleNamespace(success=True)
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=ConfigResult(success=True, content={})
    )
    result = integration.initialize()
    assert result.success is True
    return integration, fs_service_mock


def test_create_integration_factory() -> None:
    integration = create_integration()
    assert isinstance(integration, JupytextIntegration)
    assert integration.name == "Jupytext"
    assert integration.version == "1.0.0"
    assert integration.integration_id == "jupytext"


def test_create_integration_factory_forwards_kwargs() -> None:
    integration = create_integration(output_dir="/tmp/custom")  # noqa: S108 -- kwarg-forwarding smoke test, never touches real filesystem
    assert integration._init_output_dir == "/tmp/custom"  # noqa: S108


def test_not_initialized_before_initialize(fs_stub: SimpleNamespace) -> None:
    integration = JupytextIntegration()
    assert integration.is_available() is False
    result = integration.script_to_notebook("ex01.py")
    assert result.success is False
    assert "not initialized" in (result.error or "").lower()


def test_initialize_success(fs_stub: SimpleNamespace) -> None:
    integration, _fs_mock = _make_initialized_integration(fs_stub)
    assert integration.is_available() is True
    assert integration.get_jupytext_version() is not None
    assert integration.get_jupytext_version() != "unknown"


def test_initialize_falls_back_to_defaults_with_no_config_file(
    fs_stub: SimpleNamespace,
) -> None:
    """The real-world case this integration must handle correctly: no
    zeo_config.yaml / jupytext_config.yaml on disk at all (quackslides has
    none today) -- initialize() must still succeed using JupytextConfig()'s
    defaults, not error out."""
    integration = JupytextIntegration()
    integration.paths_service = _mock_paths_service()
    fs_service_mock = MagicMock()
    integration.fs_service = fs_service_mock
    fs_service_mock.expand_user_vars.return_value = SimpleNamespace(
        success=True, data="./output"
    )
    fs_service_mock.create_directory.return_value = SimpleNamespace(success=True)
    # Deliberately do NOT mock config_provider.load_config -- exercise the
    # real BaseConfigProvider.load_config() -> ZeoConfigurationError path
    # against this test's actual cwd, which has no zeo_config.yaml.
    result = integration.initialize()
    assert result.success is True
    assert integration.is_available() is True


def test_initialize_config_result_unsuccessful_without_raising(
    fs_stub: SimpleNamespace,
) -> None:
    """load_config() can return a failed ConfigResult (success=False)
    without raising -- distinct from the ZeoConfigurationError-raising
    'no file found' path. initialize() must still proceed with defaults."""
    integration = JupytextIntegration()
    integration.paths_service = _mock_paths_service()
    fs_service_mock = MagicMock()
    integration.fs_service = fs_service_mock
    fs_service_mock.expand_user_vars.return_value = SimpleNamespace(
        success=True, data="./output"
    )
    fs_service_mock.create_directory.return_value = SimpleNamespace(success=True)
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=ConfigResult.error_result("validation failed")
    )
    result = integration.initialize()
    assert result.success is True


def test_initialize_output_dir_override(fs_stub: SimpleNamespace) -> None:
    integration = JupytextIntegration(output_dir="/overridden/output")
    integration.paths_service = _mock_paths_service()
    fs_service_mock = MagicMock()
    integration.fs_service = fs_service_mock
    fs_service_mock.expand_user_vars.return_value = SimpleNamespace(
        success=True, data="/overridden/output"
    )
    fs_service_mock.create_directory.return_value = SimpleNamespace(success=True)
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=ConfigResult(success=True, content={})
    )
    result = integration.initialize()
    assert result.success is True
    assert integration.converter is not None
    assert integration.converter.config.output_dir == "/overridden/output"


def test_initialize_jupytext_not_available(
    fs_stub: SimpleNamespace, monkeypatch: MonkeyPatch
) -> None:
    import zeo_core.integrations.jupytext.service as service_mod

    def broken_verify() -> str:
        raise RuntimeError("jupytext missing")

    monkeypatch.setattr(service_mod, "verify_jupytext", broken_verify)
    integration = JupytextIntegration()
    result = integration.initialize()
    assert result.success is False
    assert "not available" in (result.error or "")
    assert integration.is_available() is False


def test_initialize_invalid_config(fs_stub: SimpleNamespace) -> None:
    integration = JupytextIntegration()
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=ConfigResult(
            success=True, content={"output_dir": 12345}
        )  # wrong type, fails pydantic validation
    )
    result = integration.initialize()
    assert result.success is False
    assert "Invalid configuration" in (result.error or "")


def test_initialize_expand_user_vars_failure_falls_back_to_raw_output_dir(
    fs_stub: SimpleNamespace,
) -> None:
    integration = JupytextIntegration()
    integration.paths_service = _mock_paths_service()
    fs_service_mock = MagicMock()
    integration.fs_service = fs_service_mock
    # success=False (no .data) forces the `else: expanded_dir = output_dir` branch.
    fs_service_mock.expand_user_vars.return_value = SimpleNamespace(
        success=False, data=None
    )
    fs_service_mock.create_directory.return_value = SimpleNamespace(success=True)
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=ConfigResult(success=True, content={})
    )
    result = integration.initialize()
    assert result.success is True


def test_initialize_fs_setup_raises(fs_stub: SimpleNamespace) -> None:
    integration = JupytextIntegration()
    integration.paths_service = _mock_paths_service()
    fs_service_mock = MagicMock()
    integration.fs_service = fs_service_mock
    fs_service_mock.expand_user_vars.side_effect = RuntimeError("fs exploded")
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=ConfigResult(success=True, content={})
    )
    result = integration.initialize()
    assert result.success is False
    assert "File system initialization failed" in (result.error or "")


def test_initialize_converter_construction_failure(
    fs_stub: SimpleNamespace, monkeypatch: MonkeyPatch
) -> None:
    import zeo_core.integrations.jupytext.service as service_mod

    def broken_converter(config: object) -> object:
        raise RuntimeError("converter blew up")

    monkeypatch.setattr(service_mod, "NotebookConverter", broken_converter)

    integration = JupytextIntegration()
    integration.paths_service = _mock_paths_service()
    fs_service_mock = MagicMock()
    integration.fs_service = fs_service_mock
    fs_service_mock.expand_user_vars.return_value = SimpleNamespace(
        success=True, data="./output"
    )
    fs_service_mock.create_directory.return_value = SimpleNamespace(success=True)
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=ConfigResult(success=True, content={})
    )
    result = integration.initialize()
    assert result.success is False
    assert "Failed to initialize converter" in (result.error or "")


def test_initialize_output_dir_create_failure(fs_stub: SimpleNamespace) -> None:
    integration = JupytextIntegration()
    integration.paths_service = _mock_paths_service()
    fs_service_mock = MagicMock()
    integration.fs_service = fs_service_mock
    fs_service_mock.expand_user_vars.return_value = SimpleNamespace(
        success=True, data="./output"
    )
    fs_service_mock.create_directory.return_value = SimpleNamespace(
        success=False, error="permission denied"
    )
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=ConfigResult(success=True, content={})
    )
    result = integration.initialize()
    assert result.success is False
    assert "Failed to create output directory" in (result.error or "")


def test_notebook_to_script_not_initialized(fs_stub: SimpleNamespace) -> None:
    integration = JupytextIntegration()
    result = integration.notebook_to_script("notebook.ipynb")
    assert result.success is False
    assert "not initialized" in (result.error or "").lower()


def test_convert_directory_not_initialized(fs_stub: SimpleNamespace) -> None:
    integration = JupytextIntegration()
    result = integration.convert_directory("weeks/week01", "ipynb")
    assert result.success is False
    assert "not initialized" in (result.error or "").lower()


def test_script_to_notebook_converter_none_after_init_is_defensive_error(
    fs_stub: SimpleNamespace,
) -> None:
    """A pathological state (initialized flag true, converter manually
    cleared) must surface as a caught error, not an unhandled AttributeError
    -- exercises the `converter is None` defensive raise + except Exception
    wrapper together, matching PandocIntegration's identical precedent."""
    integration, _fs_mock = _make_initialized_integration(fs_stub)
    integration.converter = None
    result = integration.script_to_notebook("ex01.py")
    assert result.success is False
    assert "unexpectedly None" in (result.error or "")


def test_notebook_to_script_converter_none_after_init_is_defensive_error(
    fs_stub: SimpleNamespace,
) -> None:
    integration, _fs_mock = _make_initialized_integration(fs_stub)
    integration.converter = None
    result = integration.notebook_to_script("notebook.ipynb")
    assert result.success is False
    assert "unexpectedly None" in (result.error or "")


def test_convert_directory_converter_none_after_init_is_defensive_error(
    fs_stub: SimpleNamespace,
) -> None:
    integration, fs_mock = _make_initialized_integration(fs_stub)
    fs_mock.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, is_dir=True
    )
    fs_mock.find_files.return_value = SimpleNamespace(success=True, files=["ex01.py"])
    integration.converter = None
    result = integration.convert_directory("weeks/week01", "ipynb")
    assert result.success is False
    assert "unexpectedly None" in (result.error or "")


def test_script_to_notebook(fs_stub: SimpleNamespace) -> None:
    integration, _fs_mock = _make_initialized_integration(fs_stub)
    result = integration.script_to_notebook("ex01.py")
    assert result.success is True
    assert result.content == "ex01.ipynb"


def test_script_to_notebook_explicit_output_path(fs_stub: SimpleNamespace) -> None:
    integration, _fs_mock = _make_initialized_integration(fs_stub)
    result = integration.script_to_notebook("ex01.py", output_path="custom.ipynb")
    assert result.success is True
    assert result.content == "custom.ipynb"


def test_notebook_to_script(fs_stub: SimpleNamespace) -> None:
    integration, _fs_mock = _make_initialized_integration(fs_stub)
    result = integration.notebook_to_script("notebook.ipynb")
    assert result.success is True
    assert result.content == "notebook.py"


def test_notebook_to_script_markdown_format(fs_stub: SimpleNamespace) -> None:
    integration, _fs_mock = _make_initialized_integration(fs_stub)
    result = integration.notebook_to_script("notebook.ipynb", script_format="md")
    assert result.success is True
    assert result.content == "notebook.md"


def test_is_jupytext_available_true(fs_stub: SimpleNamespace) -> None:
    integration = JupytextIntegration()
    assert integration.is_jupytext_available() is True


def test_is_jupytext_available_false(
    fs_stub: SimpleNamespace, monkeypatch: MonkeyPatch
) -> None:
    import zeo_core.integrations.jupytext.service as service_mod

    monkeypatch.setattr(
        service_mod,
        "verify_jupytext",
        lambda: (_ for _ in ()).throw(RuntimeError("missing")),
    )
    integration = JupytextIntegration()
    assert integration.is_jupytext_available() is False


def test_convert_directory(fs_stub: SimpleNamespace) -> None:
    integration, fs_mock = _make_initialized_integration(fs_stub)
    fs_mock.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, is_dir=True
    )
    fs_mock.find_files.return_value = SimpleNamespace(
        success=True, files=["ex01.py", "ex02.py"]
    )
    result = integration.convert_directory("weeks/week01", "ipynb")
    assert result.success is True
    assert result.content is not None
    assert len(result.content) == 2


def test_convert_directory_not_a_directory(fs_stub: SimpleNamespace) -> None:
    integration, fs_mock = _make_initialized_integration(fs_stub)
    fs_mock.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, is_dir=False
    )
    result = integration.convert_directory("not_a_dir.py", "ipynb")
    assert result.success is False
    assert "not a directory" in (result.error or "")


def test_convert_directory_missing(fs_stub: SimpleNamespace) -> None:
    integration, fs_mock = _make_initialized_integration(fs_stub)
    fs_mock.get_file_info.return_value = SimpleNamespace(
        success=False, exists=False, is_dir=False
    )
    result = integration.convert_directory("missing_dir", "ipynb")
    assert result.success is False
    assert "not found" in (result.error or "")


def test_convert_directory_find_files_failure(fs_stub: SimpleNamespace) -> None:
    integration, fs_mock = _make_initialized_integration(fs_stub)
    fs_mock.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, is_dir=True
    )
    fs_mock.find_files.return_value = SimpleNamespace(
        success=False, error="disk error", files=None
    )
    result = integration.convert_directory("weeks/week01", "ipynb")
    assert result.success is False
    assert "Failed to find files" in (result.error or "")


def test_convert_directory_with_explicit_output_dir(fs_stub: SimpleNamespace) -> None:
    integration, fs_mock = _make_initialized_integration(fs_stub)
    fs_mock.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, is_dir=True
    )
    fs_mock.find_files.return_value = SimpleNamespace(success=True, files=["ex01.py"])
    result = integration.convert_directory(
        "weeks/week01", "ipynb", output_dir="custom_out"
    )
    assert result.success is True


def test_convert_directory_build_tasks_skips_failing_file(
    fs_stub: SimpleNamespace,
) -> None:
    integration, fs_mock = _make_initialized_integration(fs_stub)
    fs_mock.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, is_dir=True
    )
    fs_mock.find_files.return_value = SimpleNamespace(
        success=True, files=["ex01.py", "bad.py"]
    )

    real_fs_get_file_info = fs_stub.get_file_info

    def selective(path: str) -> SimpleNamespace:
        if "bad" in path:
            return SimpleNamespace(success=False, exists=False)
        result: SimpleNamespace = real_fs_get_file_info(path)
        return result

    fs_stub.get_file_info = selective

    result = integration.convert_directory("weeks/week01", "ipynb")
    assert result.success is True
    assert result.content is not None
    assert len(result.content) == 1


def test_convert_directory_no_valid_tasks(fs_stub: SimpleNamespace) -> None:
    integration, fs_mock = _make_initialized_integration(fs_stub)
    fs_mock.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, is_dir=True
    )
    fs_mock.find_files.return_value = SimpleNamespace(success=True, files=["bad.py"])
    fs_stub.get_file_info = lambda path: SimpleNamespace(success=False, exists=False)
    result = integration.convert_directory("weeks/week01", "ipynb")
    assert result.success is False
    assert "No valid conversion tasks" in (result.error or "")


def test_convert_directory_no_files_found(fs_stub: SimpleNamespace) -> None:
    integration, fs_mock = _make_initialized_integration(fs_stub)
    fs_mock.get_file_info.return_value = SimpleNamespace(
        success=True, exists=True, is_dir=True
    )
    fs_mock.find_files.return_value = SimpleNamespace(success=True, files=[])
    result = integration.convert_directory("empty_dir", "ipynb")
    assert result.success is True
    assert result.content == []


def test_require_config_provider_raises_when_none(fs_stub: SimpleNamespace) -> None:
    from zeo_core.core.errors import ZeoIntegrationError

    integration = JupytextIntegration()
    integration.config_provider = None
    try:
        integration._require_config_provider()
        raise AssertionError("expected ZeoIntegrationError")
    except ZeoIntegrationError:
        pass


def test_ensure_initialized_returns_none_when_initialized(
    fs_stub: SimpleNamespace,
) -> None:
    integration, _fs_mock = _make_initialized_integration(fs_stub)
    assert integration._ensure_initialized() is None


def test_resolve_path_str_falls_back_on_failure() -> None:
    integration = JupytextIntegration()
    mock = _mock_paths_service()
    mock.resolve_project_path.side_effect = lambda path: SimpleNamespace(
        success=False, path=None
    )
    integration.paths_service = mock
    assert integration._resolve_path_str("ex01.py") == "ex01.py"


def test_default_output_path() -> None:
    integration = JupytextIntegration()
    assert (
        integration._default_output_path("/a/b/ex01.py", ".ipynb") == "/a/b/ex01.ipynb"
    )


def test_get_jupytext_version_none_before_init() -> None:
    integration = JupytextIntegration()
    assert integration.get_jupytext_version() is None


def test_result_success_result_shape(fs_stub: SimpleNamespace) -> None:
    """Sanity check on the shared IntegrationResult contract this service
    depends on throughout (matches pandoc's own reliance on it)."""
    ok = IntegrationResult.success_result("x", message="done")
    assert ok.success is True
    assert ok.content == "x"
    err: IntegrationResult[str] = IntegrationResult.error_result("boom")
    assert err.success is False
    assert err.content is None
