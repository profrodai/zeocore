import os
from types import SimpleNamespace

from _pytest.monkeypatch import MonkeyPatch

from zeo_core.integrations.jupytext import (
    JupytextConfig,
    JupytextConfigProvider,
)
from zeo_core.integrations.jupytext.config import MetadataConfig, ValidationConfig

# --- Tests for JupytextConfig ---


def test_jupytext_config_initialization() -> None:
    """Test that JupytextConfig initializes with default values."""
    config = JupytextConfig()

    assert config.output_dir == "./output"
    assert config.default_script_format == "py:percent"
    assert isinstance(config.validation, ValidationConfig)
    assert isinstance(config.metadata, MetadataConfig)
    assert config.validation.verify_structure is True
    assert config.metadata.inject_provenance is True
    assert config.metadata.default_kernelspec["name"] == "python3"


def test_jupytext_config_custom_values() -> None:
    """Test JupytextConfig with custom values."""
    custom_config = JupytextConfig(
        output_dir="/custom/output",
        default_script_format="md",
        validation=ValidationConfig(verify_structure=False, min_file_size=5),
    )

    assert custom_config.output_dir == "/custom/output"
    assert custom_config.default_script_format == "md"
    assert custom_config.validation.verify_structure is False
    assert custom_config.validation.min_file_size == 5


def test_jupytext_config_validate_output_dir(fs_stub: SimpleNamespace) -> None:
    """Test validation of output directory path."""
    config = JupytextConfig(output_dir="/valid/path")
    assert config.output_dir == "/valid/path"

    fs_stub.get_path_info = lambda path: SimpleNamespace(success=False)


# --- Tests for JupytextConfigProvider ---


def test_config_provider_name() -> None:
    provider = JupytextConfigProvider()
    assert provider.name == "JupytextConfig"


def test_config_provider_default_config() -> None:
    """Test that the config provider returns default config values."""
    provider = JupytextConfigProvider()
    default_config = provider.get_default_config()

    assert "output_dir" in default_config
    assert "default_script_format" in default_config
    assert "validation" in default_config


def test_config_provider_extract_config_jupytext_key() -> None:
    provider = JupytextConfigProvider()
    extracted = provider._extract_config({"jupytext": {"output_dir": "/x"}})
    assert extracted == {"output_dir": "/x"}


def test_config_provider_extract_config_notebook_key() -> None:
    provider = JupytextConfigProvider()
    extracted = provider._extract_config({"notebook": {"output_dir": "/y"}})
    assert extracted == {"output_dir": "/y"}


def test_config_provider_extract_config_fallback() -> None:
    provider = JupytextConfigProvider()
    extracted = provider._extract_config({"output_dir": "/z"})
    assert extracted == {"output_dir": "/z"}


def test_config_provider_validation() -> None:
    """Test config validation in the provider."""
    provider = JupytextConfigProvider()

    valid_config = {"output_dir": "/tmp", "default_script_format": "py:percent"}  # noqa: S108 -- path used only inside mocked/patched I/O, never touches real filesystem
    assert provider.validate_config(valid_config) is not False

    assert not provider.validate_config({"output_dir": "??invalid??"})
    assert not provider.validate_config({"output_dir": ""})


def test_config_provider_load_from_environment(monkeypatch: MonkeyPatch) -> None:
    """Test loading config from environment variables."""
    provider = JupytextConfigProvider()

    monkeypatch.setenv("ZEO_JUPYTEXT_OUTPUT_DIR", "/env/output")
    monkeypatch.setenv("ZEO_JUPYTEXT_DEFAULT_SCRIPT_FORMAT", "md")

    env_config = provider.load_from_environment()

    assert env_config.get("output_dir") is not None
    assert env_config.get("default_script_format") == "md"


def test_config_provider_load_from_environment_json_value(
    monkeypatch: MonkeyPatch,
) -> None:
    provider = JupytextConfigProvider()
    monkeypatch.setenv("ZEO_JUPYTEXT_SOME_FLAG", "true")
    env_config = provider.load_from_environment()
    assert env_config.get("some_flag") is True


def test_config_provider_load_from_environment_malformed_json(
    monkeypatch: MonkeyPatch,
) -> None:
    provider = JupytextConfigProvider()
    monkeypatch.setenv("ZEO_JUPYTEXT_BROKEN", "[not valid json")
    env_config = provider.load_from_environment()
    assert env_config.get("broken") == "[not valid json"


def test_config_provider_load_from_environment_path_key_expands(
    monkeypatch: MonkeyPatch,
) -> None:
    provider = JupytextConfigProvider()
    monkeypatch.setenv("ZEO_JUPYTEXT_CONFIG_PATH", "relative/path")
    env_config = provider.load_from_environment()
    assert os.path.isabs(env_config["config_path"])


def test_config_provider_validate_config_exception_path() -> None:
    provider = JupytextConfigProvider()

    class Unvalidatable:
        def __contains__(self, item: object) -> bool:
            raise RuntimeError("boom")

    # model_validate on a non-dict/non-mapping object raises before the
    # explicit output_dir checks run, exercising the outer except branch.
    assert provider.validate_config(Unvalidatable()) is False  # type: ignore[arg-type]


def test_config_provider_get_default_config_normalizes_output_dir(
    fs_stub: SimpleNamespace,
) -> None:
    fs_stub.normalize_path_with_info = lambda path: SimpleNamespace(
        success=True, path="/normalized/output"
    )
    import zeo_core.integrations.jupytext.config as _jtx_config_mod

    provider = JupytextConfigProvider()
    # get_default_config reads the module-level `fs` directly (not via the
    # fs_stub fixture's per-module monkeypatch, which only patches the
    # submodules the fixture explicitly lists) -- patch it directly here.
    import unittest.mock

    with unittest.mock.patch.object(_jtx_config_mod, "fs", fs_stub):
        default_config = provider.get_default_config()
    assert default_config["output_dir"] == "/normalized/output"


def test_config_provider_get_default_config_normalize_failure_is_swallowed(
    fs_stub: SimpleNamespace,
) -> None:
    def broken_normalize(path: str) -> SimpleNamespace:
        raise RuntimeError("boom")

    fs_stub.normalize_path_with_info = broken_normalize
    import unittest.mock

    import zeo_core.integrations.jupytext.config as _jtx_config_mod

    provider = JupytextConfigProvider()
    with unittest.mock.patch.object(_jtx_config_mod, "fs", fs_stub):
        default_config = provider.get_default_config()
    # Falls back to the unnormalized default rather than raising.
    assert default_config["output_dir"] == "./output"
