"""Tests for FFmpegConfig / FFmpegConfigProvider."""

import pytest

from zeo_core.integrations.ffmpeg.config import FFmpegConfig, FFmpegConfigProvider


class TestFFmpegConfig:
    def test_defaults(self) -> None:
        config = FFmpegConfig()
        assert config.output_dir == "./output"
        assert config.timeout_sec == 600.0
        assert config.overwrite is True
        assert config.download_missing_binaries is False

    def test_download_binaries_alias(self) -> None:
        config = FFmpegConfig(download_missing_binaries=True)
        assert config.download_binaries is True

    def test_override(self) -> None:
        config = FFmpegConfig(output_dir="./render", timeout_sec=30.0)
        assert config.output_dir == "./render"
        assert config.timeout_sec == 30.0


class TestFFmpegConfigProvider:
    def test_name(self) -> None:
        provider = FFmpegConfigProvider()
        assert provider.name == "FFmpegConfig"

    def test_extract_config_with_ffmpeg_section(self) -> None:
        provider = FFmpegConfigProvider()
        result = provider._extract_config({"ffmpeg": {"timeout_sec": 5.0}})
        assert result == {"timeout_sec": 5.0}

    def test_extract_config_without_ffmpeg_section(self) -> None:
        provider = FFmpegConfigProvider()
        result = provider._extract_config({"timeout_sec": 5.0})
        assert result == {"timeout_sec": 5.0}

    def test_validate_config_valid(self) -> None:
        provider = FFmpegConfigProvider()
        assert provider.validate_config({"output_dir": "./output"}) is True

    def test_validate_config_empty_output_dir(self) -> None:
        provider = FFmpegConfigProvider()
        assert provider.validate_config({"output_dir": "  "}) is False

    def test_validate_config_invalid_chars(self) -> None:
        provider = FFmpegConfigProvider()
        assert provider.validate_config({"output_dir": "bad*path"}) is False

    def test_validate_config_wrong_type(self) -> None:
        provider = FFmpegConfigProvider()
        assert provider.validate_config({"output_dir": 123}) is False

    def test_validate_config_pydantic_rejects(self) -> None:
        provider = FFmpegConfigProvider()
        assert provider.validate_config({"timeout_sec": "not-a-number"}) is False

    def test_get_default_config(self) -> None:
        # Deliberately does NOT use the fs_stub fixture: get_default_config()
        # calls the real zeo_core.core.fs.service.standalone.normalize_path_with_info
        # (config.py's fs import succeeds for real in this environment, so the
        # ImportError stub branch never activates) which resolves "./output"
        # to an absolute, sandboxed path -- only the *shape* of that
        # normalization is this test's contract, not the literal default string.
        provider = FFmpegConfigProvider()
        default_config = provider.get_default_config()
        assert default_config["output_dir"].endswith("output")
        assert default_config["timeout_sec"] == 600.0

    def test_load_from_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        provider = FFmpegConfigProvider()
        monkeypatch.setenv("ZEO_FFMPEG_TIMEOUT_SEC", "45.0")
        monkeypatch.setenv("ZEO_FFMPEG_OVERWRITE", "false")
        config = provider.load_from_environment()
        assert config["overwrite"] is False
        # timeout_sec is not JSON-parseable as bare "45.0" by the string-only
        # branch (it isn't a path key or a bool/JSON literal), so it stays a
        # plain string here -- FFmpegConfig(**config) coerces it via pydantic.
        assert config["timeout_sec"] == "45.0"
        validated = FFmpegConfig(**config)
        assert validated.timeout_sec == 45.0
        assert validated.overwrite is False

    def test_load_from_environment_output_dir_path_handling(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = FFmpegConfigProvider()
        monkeypatch.setenv("ZEO_FFMPEG_OUTPUT_DIR", "relative/dir")
        config = provider.load_from_environment()
        assert config["output_dir"].endswith("relative/dir")

    def test_load_from_environment_json_list_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = FFmpegConfigProvider()
        monkeypatch.setenv("ZEO_FFMPEG_GLOBAL_ARGS", '["-nostdin", "-y"]')
        config = provider.load_from_environment()
        assert config["global_args"] == ["-nostdin", "-y"]

    def test_load_from_environment_invalid_json_falls_back_to_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = FFmpegConfigProvider()
        monkeypatch.setenv("ZEO_FFMPEG_EXTRA", "[not valid json")
        config = provider.load_from_environment()
        assert config["extra"] == "[not valid json"

    def test_load_from_environment_plain_string_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = FFmpegConfigProvider()
        monkeypatch.setenv("ZEO_FFMPEG_PRESET", "ultrafast")
        config = provider.load_from_environment()
        assert config["preset"] == "ultrafast"

    def test_get_default_config_normalize_raises_falls_back(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_default_config() tolerates normalize_path_with_info() raising."""
        import zeo_core.integrations.ffmpeg.config as ffmpeg_config_module

        def _raise(_path: str) -> None:
            raise RuntimeError("normalize exploded")

        monkeypatch.setattr(ffmpeg_config_module.fs, "normalize_path_with_info", _raise)
        provider = FFmpegConfigProvider()
        default_config = provider.get_default_config()
        assert default_config["output_dir"] == "./output"
