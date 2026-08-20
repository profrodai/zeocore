"""
Tests for the FFmpeg integration service, with `ffmpeg_zeo` itself mocked out.

These tests verify FFmpegIntegration's own logic (initialization sequencing,
error envelope shape, delegation arguments) independent of whether a real
ffmpeg binary is present -- matching pandoc's test_service.py convention of
mocking the wrapped library (`verify_pandoc`) rather than requiring the real
external tool for unit-level coverage. Real-binary, real-subprocess coverage
lives in test_service_live.py.
"""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.ffmpeg.protocols import (
    MediaConversionProtocol,
    MediaProbeProtocol,
)
from zeo_core.integrations.ffmpeg.service import FFmpegIntegration, create_integration


def test_ffmpeg_integration_satisfies_media_protocols() -> None:
    """FFmpegIntegration must structurally satisfy both runtime_checkable
    protocols this integration declares -- a direct check, since neither
    protocol is exercised via isinstance() anywhere else in the loader/
    registry layer the way IntegrationProtocol itself is."""
    integration = FFmpegIntegration()
    assert isinstance(integration, MediaProbeProtocol)
    assert isinstance(integration, MediaConversionProtocol)


@pytest.fixture
def setup_mocks(
    fs_stub: SimpleNamespace, mock_paths_service: MagicMock
) -> tuple[SimpleNamespace, MagicMock]:
    """Shared setup for service tests (mirrors pandoc/test_service.py)."""
    fs_stub.create_directory = MagicMock(return_value=SimpleNamespace(success=True))
    fs_stub.expand_user_vars = MagicMock(
        side_effect=lambda x: SimpleNamespace(success=True, data=x)
    )
    return fs_stub, mock_paths_service


def _binary_info(
    ffmpeg: str = "/usr/bin/ffmpeg", ffprobe: str = "/usr/bin/ffprobe"
) -> Any:  # noqa: ANN401 -- returns a duck-typed BinaryInfo-shaped SimpleNamespace, not the real ffmpeg_zeo class, matching this file's own mocking convention
    return SimpleNamespace(ffmpeg=ffmpeg, ffprobe=ffprobe, source="path", license=None)


def test_ffmpeg_integration_name_version() -> None:
    """Test basic properties of FFmpegIntegration."""
    integration = FFmpegIntegration()
    assert integration.name == "FFmpeg"
    assert integration.version == "1.0.0"
    assert integration.integration_id == "ffmpeg"
    assert not integration._initialized


def test_create_integration_factory() -> None:
    integration = create_integration()
    assert isinstance(integration, FFmpegIntegration)


def test_package_level_create_integration_entry_point() -> None:
    """The entry-points table registers zeo_core.integrations.ffmpeg:create_integration
    (the package __init__.py's factory), not service.py's -- a distinct object,
    covered separately here."""
    import zeo_core.integrations.ffmpeg as ffmpeg_package

    integration = ffmpeg_package.create_integration()
    assert isinstance(integration, FFmpegIntegration)


@patch("ffmpeg_zeo.resolve_binaries")
def test_initialize_success(
    mock_resolve_binaries: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Test initialize() succeeds when config loads and binaries resolve."""
    fs_stub, mock_paths_service = setup_mocks
    mock_resolve_binaries.return_value = _binary_info()

    integration = FFmpegIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )

    result = integration.initialize()

    assert result.success
    assert integration._initialized
    assert integration.is_available()
    assert integration.get_ffmpeg_binary() == "/usr/bin/ffmpeg"


def test_initialize_config_error(
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Test initialize() fails cleanly when config loading raises."""
    fs_stub, mock_paths_service = setup_mocks

    integration = FFmpegIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        side_effect=RuntimeError("boom")
    )

    result = integration.initialize()

    assert not result.success
    assert result.error is not None
    assert "Invalid configuration" in result.error
    assert not integration._initialized


def test_initialize_output_directory_creation_fails(
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Test initialize() fails cleanly when create_directory() reports failure."""
    fs_stub, mock_paths_service = setup_mocks
    fs_stub.create_directory = MagicMock(
        return_value=SimpleNamespace(success=False, error="disk full")
    )

    integration = FFmpegIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )

    result = integration.initialize()

    assert not result.success
    assert result.error is not None
    assert "Failed to create output directory" in result.error
    assert not integration._initialized


def test_initialize_output_directory_setup_raises(
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Test initialize() fails cleanly when the fs_service step itself raises."""
    fs_stub, mock_paths_service = setup_mocks
    fs_stub.expand_user_vars = MagicMock(side_effect=RuntimeError("fs exploded"))

    integration = FFmpegIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )

    result = integration.initialize()

    assert not result.success
    assert result.error is not None
    assert "File system initialization failed" in result.error
    assert not integration._initialized


@patch("ffmpeg_zeo.resolve_binaries")
def test_initialize_binary_resolution_unexpected_error(
    mock_resolve_binaries: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Test initialize() fails cleanly on a non-BinaryNotFoundError exception."""
    fs_stub, mock_paths_service = setup_mocks
    mock_resolve_binaries.side_effect = RuntimeError("unexpected")

    integration = FFmpegIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )

    result = integration.initialize()

    assert not result.success
    assert result.error is not None
    assert "Failed to resolve ffmpeg binaries" in result.error
    assert not integration._initialized


def test_ensure_initialized_when_ready_returns_none(
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """_ensure_initialized() returns None (no error) once initialized."""
    integration = FFmpegIntegration()
    integration._initialized = True
    assert integration._ensure_initialized() is None


def test_resolve_path_str_falls_back_on_failure() -> None:
    """_resolve_path_str() returns the original string when resolution fails."""
    integration = FFmpegIntegration()
    integration.paths_service = MagicMock()
    integration.paths_service.resolve_project_path.return_value = SimpleNamespace(
        success=False, path=None
    )
    assert integration._resolve_path_str("relative/input.mp4") == "relative/input.mp4"


@patch("ffmpeg_zeo.resolve_binaries")
def test_initialize_binary_not_found(
    mock_resolve_binaries: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    """Test initialize() fails cleanly when ffmpeg-zeo cannot find binaries."""
    from ffmpeg_zeo import BinaryNotFoundError

    fs_stub, mock_paths_service = setup_mocks
    mock_resolve_binaries.side_effect = BinaryNotFoundError("ffmpeg")

    integration = FFmpegIntegration()
    integration.paths_service = mock_paths_service
    integration.fs_service = fs_stub  # type: ignore[assignment]
    assert integration.config_provider is not None
    integration.config_provider.load_config = MagicMock(  # type: ignore[method-assign]
        return_value=IntegrationResult(success=True, content={})
    )

    result = integration.initialize()

    assert not result.success
    assert result.error is not None
    assert "not available" in result.error
    assert not integration._initialized
    assert not integration.is_available()


def test_probe_not_initialized() -> None:
    """Test probe() when service is not initialized."""
    integration = FFmpegIntegration()
    result = integration.probe("input.mp4")

    assert not result.success
    assert result.error is not None
    assert "not initialized" in result.error


def test_convert_not_initialized() -> None:
    integration = FFmpegIntegration()
    result = integration.convert("input.mp4", "output.mkv")
    assert not result.success
    assert "not initialized" in (result.error or "")


def test_transcode_h264_not_initialized() -> None:
    integration = FFmpegIntegration()
    result = integration.transcode_h264("input.mp4", "output.mp4")
    assert not result.success
    assert "not initialized" in (result.error or "")


def test_extract_audio_not_initialized() -> None:
    integration = FFmpegIntegration()
    result = integration.extract_audio("input.mp4", "output.aac")
    assert not result.success
    assert "not initialized" in (result.error or "")


def test_thumbnail_not_initialized() -> None:
    integration = FFmpegIntegration()
    result = integration.thumbnail("input.mp4", "output.jpg")
    assert not result.success
    assert "not initialized" in (result.error or "")


class _InitializedIntegration:
    """Helper: build an FFmpegIntegration that already believes it's initialized."""

    @staticmethod
    def build(
        fs_stub: SimpleNamespace, mock_paths_service: MagicMock
    ) -> FFmpegIntegration:
        integration = FFmpegIntegration()
        integration.paths_service = mock_paths_service
        integration.fs_service = fs_stub  # type: ignore[assignment]
        integration._initialized = True
        integration._ffmpeg_bin = "/usr/bin/ffmpeg"
        integration._ffprobe_bin = "/usr/bin/ffprobe"
        from zeo_core.integrations.ffmpeg.config import FFmpegConfig

        integration.config = FFmpegConfig()
        return integration


@patch("ffmpeg_zeo.probe")
def test_probe_success(
    mock_probe: MagicMock, setup_mocks: tuple[SimpleNamespace, MagicMock]
) -> None:
    fs_stub, mock_paths_service = setup_mocks
    integration = _InitializedIntegration.build(fs_stub, mock_paths_service)

    fake_probe_result = MagicMock()
    fake_probe_result.model_dump.return_value = {"format": {}, "streams": []}
    fake_probe_result.duration_seconds = 5.0
    fake_probe_result.bitrate_bps = 128000
    fake_probe_result.has_video = True
    fake_probe_result.has_audio = False
    fake_probe_result.width = 1920
    fake_probe_result.height = 1080
    fake_probe_result.video_codec = "h264"
    fake_probe_result.audio_codec = None
    fake_probe_result.fps = 30.0
    mock_probe.return_value = fake_probe_result

    result = integration.probe("input.mp4")

    assert result.success
    assert result.content is not None
    assert result.content["duration_seconds"] == 5.0
    assert result.content["has_video"] is True
    assert result.content["video_codec"] == "h264"


@patch("ffmpeg_zeo.probe")
def test_probe_ffmpeg_error(
    mock_probe: MagicMock, setup_mocks: tuple[SimpleNamespace, MagicMock]
) -> None:
    from ffmpeg_zeo import FFmpegError

    fs_stub, mock_paths_service = setup_mocks
    integration = _InitializedIntegration.build(fs_stub, mock_paths_service)
    mock_probe.side_effect = FFmpegError("ffprobe", returncode=1)

    result = integration.probe("missing.mp4")

    assert not result.success
    assert "ffprobe failed" in (result.error or "")


@patch("ffmpeg_zeo.probe")
def test_probe_unexpected_error(
    mock_probe: MagicMock, setup_mocks: tuple[SimpleNamespace, MagicMock]
) -> None:
    """probe() catches non-FFmpegError exceptions too (defensive branch)."""
    fs_stub, mock_paths_service = setup_mocks
    integration = _InitializedIntegration.build(fs_stub, mock_paths_service)
    mock_probe.side_effect = ValueError("unexpected")

    result = integration.probe("input.mp4")

    assert not result.success
    assert "Probe failed" in (result.error or "")


@patch("ffmpeg_zeo.run_recipe")
def test_run_recipe_unexpected_error(
    mock_run_recipe: MagicMock, setup_mocks: tuple[SimpleNamespace, MagicMock]
) -> None:
    """_run_recipe() catches non-FFmpegError exceptions too (defensive branch)."""
    fs_stub, mock_paths_service = setup_mocks
    integration = _InitializedIntegration.build(fs_stub, mock_paths_service)
    mock_run_recipe.side_effect = ValueError("bad recipe args")

    result = integration.convert("input.mp4", "output.mkv")

    assert not result.success
    assert "convert failed" in (result.error or "")
    assert integration.metrics.failed_renders == 1


@patch("ffmpeg_zeo.run")
@patch("ffmpeg_zeo.run_recipe")
def test_convert_success(
    mock_run_recipe: MagicMock,
    mock_run: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    fs_stub, mock_paths_service = setup_mocks
    integration = _InitializedIntegration.build(fs_stub, mock_paths_service)
    fake_graph = MagicMock()
    mock_run_recipe.return_value = fake_graph
    mock_run.return_value = MagicMock(returncode=0)

    result = integration.convert("input.mp4", "output.mkv")

    assert result.success
    assert result.content == "output.mkv"
    mock_run_recipe.assert_called_once()
    call_args = mock_run_recipe.call_args
    assert call_args.args[0] == "convert"
    assert call_args.kwargs["src"] == "input.mp4"
    assert call_args.kwargs["dst"] == "output.mkv"
    mock_run.assert_called_once_with(fake_graph, timeout=600.0)
    assert integration.metrics.successful_renders == 1
    assert integration.metrics.total_attempts == 1


@patch("ffmpeg_zeo.run")
@patch("ffmpeg_zeo.run_recipe")
def test_transcode_h264_passes_crf_and_preset(
    mock_run_recipe: MagicMock,
    mock_run: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    fs_stub, mock_paths_service = setup_mocks
    integration = _InitializedIntegration.build(fs_stub, mock_paths_service)
    mock_run_recipe.return_value = MagicMock()
    mock_run.return_value = MagicMock(returncode=0)

    result = integration.transcode_h264(
        "input.mp4", "output.mp4", crf=18, preset="slow"
    )

    assert result.success
    call_args = mock_run_recipe.call_args
    assert call_args.args[0] == "transcode_h264"
    assert call_args.kwargs["crf"] == 18
    assert call_args.kwargs["preset"] == "slow"


@patch("ffmpeg_zeo.run")
@patch("ffmpeg_zeo.run_recipe")
def test_extract_audio_default_output_path(
    mock_run_recipe: MagicMock,
    mock_run: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    fs_stub, mock_paths_service = setup_mocks
    integration = _InitializedIntegration.build(fs_stub, mock_paths_service)
    mock_run_recipe.return_value = MagicMock()
    mock_run.return_value = MagicMock(returncode=0)

    result = integration.extract_audio("dir/input.mp4")

    assert result.success
    assert result.content == "dir/input.aac"


@patch("ffmpeg_zeo.run")
@patch("ffmpeg_zeo.run_recipe")
def test_thumbnail_default_output_path_and_time(
    mock_run_recipe: MagicMock,
    mock_run: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    fs_stub, mock_paths_service = setup_mocks
    integration = _InitializedIntegration.build(fs_stub, mock_paths_service)
    mock_run_recipe.return_value = MagicMock()
    mock_run.return_value = MagicMock(returncode=0)

    result = integration.thumbnail("dir/input.mp4", time=2.5)

    assert result.success
    assert result.content == "dir/input.thumb.jpg"
    call_args = mock_run_recipe.call_args
    assert call_args.kwargs["time"] == 2.5


@patch("ffmpeg_zeo.run")
@patch("ffmpeg_zeo.run_recipe")
def test_render_failure_records_metrics(
    mock_run_recipe: MagicMock,
    mock_run: MagicMock,
    setup_mocks: tuple[SimpleNamespace, MagicMock],
) -> None:
    from ffmpeg_zeo import FFmpegError

    fs_stub, mock_paths_service = setup_mocks
    integration = _InitializedIntegration.build(fs_stub, mock_paths_service)
    mock_run_recipe.return_value = MagicMock()
    mock_run.side_effect = FFmpegError("ffmpeg", returncode=1)

    result = integration.convert("input.mp4", "output.mkv")

    assert not result.success
    assert integration.metrics.failed_renders == 1
    assert integration.metrics.total_attempts == 1
    assert "input.mp4" in integration.metrics.errors
