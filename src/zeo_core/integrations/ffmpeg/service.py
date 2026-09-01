"""ffmpeg Integration Service

This module provides the main integration service for media probing and
rendering/transcoding, wrapping the org's own `ffmpeg-zeo` PyPI package
(github.com/zeroemployeeorg/ffmpeg-zeo) -- not the raw ffmpeg binary directly.
`ffmpeg-zeo` itself resolves and shells out to the ffmpeg/ffprobe binaries;
this module is a thin adapter from its API onto zeocore's own
`IntegrationProtocol`/`IntegrationResult` conventions, matching
`zeo_core.integrations.pandoc.service.PandocIntegration`'s shape.
"""

import logging
import os
from typing import TYPE_CHECKING, Any

from zeo_core.core.errors import ZeoIntegrationError
from zeo_core.core.fs.service import FileSystemService
from zeo_core.core.logging import LOG_LEVELS, LogLevel
from zeo_core.core.paths.service import PathService
from zeo_core.integrations.core.base import BaseIntegrationService
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.ffmpeg.config import FFmpegConfig, FFmpegConfigProvider
from zeo_core.integrations.ffmpeg.models import RenderMetrics

if TYPE_CHECKING:
    # ffmpeg_zeo is an optional dependency (the `ffmpeg` extra) -- imported
    # for real only inside the methods below, never at module load time, so
    # this integration remains importable without ffmpeg-zeo installed
    # (matching pandoc's own lazy `import pypandoc` pattern). This
    # TYPE_CHECKING-guarded import exists purely so mypy can type
    # `_probe_result_to_dict` precisely instead of falling back to `Any`.
    from ffmpeg_zeo import ProbeResult

logger = logging.getLogger(__name__)


def _probe_result_to_dict(probe_result: "ProbeResult") -> dict[str, Any]:
    """Coerce an `ffmpeg_zeo.ProbeResult` into a plain JSON-safe dict.

    `ProbeResult` is a pydantic `BaseModel` with `extra="allow"` and
    `cached_property`-based derived fields (`duration_seconds`, `fps`, etc.)
    that `model_dump()` alone does not include. Both the raw ffprobe fields
    and the derived convenience fields are surfaced here so callers get the
    same information whether they inspect the dict or the original object.
    """
    data = probe_result.model_dump(mode="json")
    data["duration_seconds"] = probe_result.duration_seconds
    data["bitrate_bps"] = probe_result.bitrate_bps
    data["has_video"] = probe_result.has_video
    data["has_audio"] = probe_result.has_audio
    data["width"] = probe_result.width
    data["height"] = probe_result.height
    data["video_codec"] = probe_result.video_codec
    data["audio_codec"] = probe_result.audio_codec
    data["fps"] = probe_result.fps
    return data


class FFmpegIntegration(BaseIntegrationService):
    """Main integration service for media probing and rendering.

    Wraps `ffmpeg-zeo`'s typed Graph IR / recipes / probe surface behind
    zeocore's `IntegrationResult` error-handling envelope. Manages
    configuration and initialization; delegates the actual subprocess work
    to `ffmpeg_zeo` (which itself owns binary discovery, argv construction,
    and process execution -- this class does not shell out directly).

    Attributes:
        metrics: Render metrics accumulated across calls.
        _config_loaded: Flag indicating if configuration was loaded successfully.
        _ffmpeg_bin: Cached path to the resolved ffmpeg binary.
    """

    def __init__(
        self,
        config_path: str | None = None,
        output_dir: str | None = None,
        config_provider: FFmpegConfigProvider | None = None,
        paths_service: PathService | None = None,
        fs_service: FileSystemService | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
    ) -> None:
        """Initialize the ffmpeg integration service.

        Args:
            config_path: Optional path to configuration file.
            output_dir: Optional output directory override.
            config_provider: Optional custom config provider.
            paths_service: Optional paths service instance.
            fs_service: Optional filesystem service instance.
            log_level: Logging level.
        """
        if config_provider is None:
            config_provider = FFmpegConfigProvider(log_level=log_level)

        super().__init__(
            config_provider=config_provider,
            auth_provider=None,
            config=None,
            config_path=config_path,
            log_level=log_level,
        )

        self.paths_service = paths_service or PathService()

        try:
            self.fs_service = fs_service or FileSystemService()
        except FileNotFoundError, OSError:
            import tempfile

            self.fs_service = fs_service or FileSystemService(
                base_dir=tempfile.gettempdir()
            )

        self._init_output_dir = output_dir
        self._config_path = config_path

        self.config: FFmpegConfig | None = None  # type: ignore[assignment]
        self.metrics: RenderMetrics = RenderMetrics()
        self._config_loaded = False
        self._ffmpeg_bin: str | None = None
        self._ffprobe_bin: str | None = None

    @property
    def name(self) -> str:
        """Name of the integration."""
        return "FFmpeg"

    @property
    def version(self) -> str:
        """Version of the integration."""
        return "1.0.0"

    def _ensure_initialized(self) -> IntegrationResult | None:
        """Ensure the integration is initialized.

        Returns:
            IntegrationResult error if not initialized, None if initialized.
        """
        if not self._initialized:
            logger.error("FFmpeg integration is not initialized")
            not_initialized_msg = (
                "FFmpeg integration is not initialized. Call initialize() first."
            )
            return IntegrationResult.error_result(
                error=not_initialized_msg,
                message=not_initialized_msg,
            )
        return None

    def _resolve_path_str(self, path: str) -> str:
        """Resolve a path to the project root, falling back to the original string."""
        result = self.paths_service.resolve_project_path(path)
        if result.success and result.path is not None:
            return str(result.path)
        return path

    def _default_output_path(self, input_path: str, extension: str) -> str:
        """Synthesize an output path when the caller did not supply one."""
        directory = os.path.dirname(input_path)
        name, _ = os.path.splitext(os.path.basename(input_path))
        return os.path.join(directory, name + extension)

    def _load_ffmpeg_config(
        self,
    ) -> tuple[FFmpegConfig | None, IntegrationResult | None]:
        """Step 1 of initialize(): load and validate configuration.

        Returns:
            (config, None) on success, or (None, error IntegrationResult).
            Extracted to keep initialize() itself under the C901 threshold;
            behavior/order unchanged from the inline version.
        """
        try:
            if self.config_provider is None:
                raise ZeoIntegrationError(
                    "FFmpegIntegration.config_provider is unexpectedly None"
                )
            config_result = self.config_provider.load_config(
                config_path=self._config_path
            )

            if not config_result.success:
                logger.warning(f"Failed to load config: {config_result.error}")

            config_dict = config_result.content or {}

            if self._init_output_dir:
                config_dict["output_dir"] = self._init_output_dir

            ffmpeg_config = FFmpegConfig(**config_dict)
            self._config_loaded = True
            self.config = ffmpeg_config
            return ffmpeg_config, None

        except Exception as e:
            error_msg = f"Invalid configuration: {str(e)}"
            logger.error(error_msg)
            self._initialized = False
            return None, IntegrationResult.error_result(
                error=error_msg, message=error_msg
            )

    def _setup_output_directory(
        self, ffmpeg_config: FFmpegConfig
    ) -> IntegrationResult | None:
        """Step 2 of initialize(): create the output directory if configured.

        Returns:
            None on success, error IntegrationResult on failure. Extracted
            for the same C901 reason as _load_ffmpeg_config.
        """
        try:
            output_dir = ffmpeg_config.output_dir
            if output_dir:
                expanded_dir_result = self.fs_service.expand_user_vars(output_dir)
                if expanded_dir_result.success and expanded_dir_result.data:
                    expanded_dir = expanded_dir_result.data
                else:
                    expanded_dir = output_dir

                create_result = self.fs_service.create_directory(expanded_dir)
                if not create_result.success:
                    error_msg = (
                        f"Failed to create output directory: {create_result.error}"
                    )
                    logger.error(error_msg)
                    self._initialized = False
                    return IntegrationResult.error_result(
                        error=error_msg, message=error_msg
                    )

                logger.info(f"Output directory ready: {expanded_dir}")
            return None

        except Exception as e:
            error_msg = f"File system initialization failed: {str(e)}"
            logger.error(error_msg)
            self._initialized = False
            return IntegrationResult.error_result(error=error_msg, message=error_msg)

    def _resolve_ffmpeg_binaries(
        self, ffmpeg_config: FFmpegConfig
    ) -> IntegrationResult | None:
        """Step 3 of initialize(): verify ffmpeg/ffprobe resolve via ffmpeg-zeo.

        Returns:
            None on success (with `self._ffmpeg_bin`/`self._ffprobe_bin` set),
            error IntegrationResult on failure. Extracted for the same C901
            reason as _load_ffmpeg_config.
        """
        try:
            from ffmpeg_zeo import BinaryNotFoundError
            from ffmpeg_zeo import resolve_binaries as ffmpeg_zeo_resolve_binaries

            binary_info = ffmpeg_zeo_resolve_binaries(
                download=ffmpeg_config.download_binaries
            )
            self._ffmpeg_bin = str(binary_info.ffmpeg)
            self._ffprobe_bin = str(binary_info.ffprobe)
            logger.info(f"ffmpeg resolved via {binary_info.source}: {self._ffmpeg_bin}")
            return None
        except ImportError as e:
            error_msg = (
                "ffmpeg-zeo is not installed. Install with "
                f"'pip install zeocore[ffmpeg]'. ({e})"
            )
            logger.error(error_msg)
            self._initialized = False
            return IntegrationResult.error_result(error=error_msg, message=error_msg)
        except BinaryNotFoundError as e:
            error_msg = f"ffmpeg/ffprobe not available: {str(e)}"
            logger.error(error_msg)
            self._initialized = False
            return IntegrationResult.error_result(error=error_msg, message=error_msg)
        except Exception as e:
            error_msg = f"Failed to resolve ffmpeg binaries: {str(e)}"
            logger.error(error_msg)
            self._initialized = False
            return IntegrationResult.error_result(error=error_msg, message=error_msg)

    def initialize(self) -> IntegrationResult:
        """Initialize the ffmpeg integration.

        This method:
        1. Loads and validates ffmpeg-specific configuration.
        2. Creates the output directory if needed.
        3. Verifies ffmpeg/ffprobe binaries are resolvable via ffmpeg-zeo.

        Returns:
            IntegrationResult with success status and any error messages.
        """
        ffmpeg_config, config_error = self._load_ffmpeg_config()
        if config_error is not None or ffmpeg_config is None:
            fallback_msg = "Configuration loading failed"
            return config_error or IntegrationResult.error_result(
                error=fallback_msg, message=fallback_msg
            )

        fs_error = self._setup_output_directory(ffmpeg_config)
        if fs_error is not None:
            return fs_error

        binary_error = self._resolve_ffmpeg_binaries(ffmpeg_config)
        if binary_error is not None:
            return binary_error

        self._initialized = True
        logger.info("FFmpeg integration initialized successfully")
        return IntegrationResult(
            success=True,
            message="FFmpeg integration initialized successfully",
            content={"ffmpeg_bin": self._ffmpeg_bin, "ffprobe_bin": self._ffprobe_bin},
        )

    def is_available(self) -> bool:
        """Check if the ffmpeg integration is available.

        Returns:
            True if available, False otherwise.
        """
        return self._initialized and self._ffmpeg_bin is not None

    def get_ffmpeg_binary(self) -> str | None:
        """Get the path to the resolved ffmpeg binary.

        Returns:
            Path string, or None if not initialized.
        """
        return self._ffmpeg_bin

    def probe(self, input_path: str) -> IntegrationResult[dict[str, Any]]:
        """Inspect a media file and return its format/stream metadata.

        Args:
            input_path: Path to the media file to inspect.

        Returns:
            IntegrationResult[dict[str, Any]] with probed metadata, or error.
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error

        try:
            from ffmpeg_zeo import FFmpegError
            from ffmpeg_zeo import probe as ffmpeg_zeo_probe

            resolved_path = self._resolve_path_str(input_path)
            result = ffmpeg_zeo_probe(resolved_path)
            return IntegrationResult.success_result(
                _probe_result_to_dict(result),
                message=f"Successfully probed {resolved_path}",
            )
        except FFmpegError as e:
            error_msg = f"ffprobe failed for {input_path}: {str(e)}"
            logger.error(error_msg)
            return IntegrationResult.error_result(error=error_msg, message=error_msg)
        except Exception as e:
            error_msg = f"Probe failed: {str(e)}"
            logger.error(error_msg)
            return IntegrationResult.error_result(error=error_msg, message=error_msg)

    def _run_recipe(
        self,
        recipe_name: str,
        input_path: str,
        output_path: str,
        **kwargs: Any,  # noqa: ANN401 -- heterogeneous per-recipe kwargs (crf: int, preset: str, codec: str, time: float), forwarded verbatim to ffmpeg_zeo.run_recipe
    ) -> IntegrationResult[str]:
        """Run one of ffmpeg-zeo's named recipes and wrap the result.

        Shared implementation for `convert`, `transcode_h264`, `extract_audio`,
        and `thumbnail` -- each just supplies the recipe name and its own
        extra kwargs (crf/preset, codec, time, ...).

        Args:
            recipe_name: Name of the recipe in `ffmpeg_zeo.recipes.RECIPES`.
            input_path: Resolved path to the source media file.
            output_path: Resolved destination path.
            **kwargs: Extra keyword arguments forwarded to the recipe function.

        Returns:
            IntegrationResult[str] with the output path, or error.
        """
        try:
            from ffmpeg_zeo import FFmpegError
            from ffmpeg_zeo import run as ffmpeg_zeo_run
            from ffmpeg_zeo import run_recipe as ffmpeg_zeo_run_recipe

            self.metrics.total_attempts += 1

            graph = ffmpeg_zeo_run_recipe(
                recipe_name, src=input_path, dst=output_path, **kwargs
            )
            timeout = self.config.timeout_sec if self.config else 600.0
            ffmpeg_zeo_run(graph, timeout=timeout)

            self.metrics.successful_renders += 1
            return IntegrationResult.success_result(
                output_path,
                message=f"Successfully rendered {input_path} to {output_path}",
            )
        except FFmpegError as e:
            error_msg = f"ffmpeg {recipe_name} failed: {str(e)}"
            logger.error(error_msg)
            self.metrics.failed_renders += 1
            self.metrics.errors[input_path] = error_msg
            return IntegrationResult.error_result(error=error_msg, message=error_msg)
        except Exception as e:
            error_msg = f"{recipe_name} failed: {str(e)}"
            logger.error(error_msg)
            self.metrics.failed_renders += 1
            self.metrics.errors[input_path] = error_msg
            return IntegrationResult.error_result(error=error_msg, message=error_msg)

    def convert(
        self, input_path: str, output_path: str | None = None
    ) -> IntegrationResult[str]:
        """Convert a media file to the format implied by `output_path`'s extension.

        Args:
            input_path: Path to the source media file.
            output_path: Optional destination path.

        Returns:
            IntegrationResult[str] with the output file path, or error.
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error

        resolved_input = self._resolve_path_str(input_path)
        resolved_output = (
            self._resolve_path_str(output_path)
            if output_path
            else self._default_output_path(resolved_input, ".mp4")
        )
        return self._run_recipe("convert", resolved_input, resolved_output)

    def transcode_h264(
        self,
        input_path: str,
        output_path: str | None = None,
        *,
        crf: int = 23,
        preset: str = "medium",
    ) -> IntegrationResult[str]:
        """Transcode a video to H.264/AAC.

        Args:
            input_path: Path to the source video file.
            output_path: Optional destination path.
            crf: Constant rate factor (lower is higher quality).
            preset: x264 encoder preset.

        Returns:
            IntegrationResult[str] with the output file path, or error.
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error

        resolved_input = self._resolve_path_str(input_path)
        resolved_output = (
            self._resolve_path_str(output_path)
            if output_path
            else self._default_output_path(resolved_input, ".h264.mp4")
        )
        return self._run_recipe(
            "transcode_h264", resolved_input, resolved_output, crf=crf, preset=preset
        )

    def extract_audio(
        self, input_path: str, output_path: str | None = None, *, codec: str = "copy"
    ) -> IntegrationResult[str]:
        """Extract the audio track from a media file.

        Args:
            input_path: Path to the source media file.
            output_path: Optional destination path.
            codec: Audio codec to encode with, or "copy" for a stream copy.

        Returns:
            IntegrationResult[str] with the output file path, or error.
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error

        resolved_input = self._resolve_path_str(input_path)
        extension = ".m4a" if codec != "copy" else ".aac"
        resolved_output = (
            self._resolve_path_str(output_path)
            if output_path
            else self._default_output_path(resolved_input, extension)
        )
        return self._run_recipe(
            "extract_audio", resolved_input, resolved_output, codec=codec
        )

    def thumbnail(
        self, input_path: str, output_path: str | None = None, *, time: float = 1.0
    ) -> IntegrationResult[str]:
        """Extract a single-frame thumbnail from a video.

        Args:
            input_path: Path to the source video file.
            output_path: Optional destination path.
            time: Timestamp in seconds to grab the frame from.

        Returns:
            IntegrationResult[str] with the output file path, or error.
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error

        resolved_input = self._resolve_path_str(input_path)
        resolved_output = (
            self._resolve_path_str(output_path)
            if output_path
            else self._default_output_path(resolved_input, ".thumb.jpg")
        )
        return self._run_recipe("thumbnail", resolved_input, resolved_output, time=time)


# Factory function for creating integration instance
def create_integration(**kwargs: Any) -> FFmpegIntegration:  # noqa: ANN401 -- forwarded verbatim to FFmpegIntegration.__init__
    """Create a new FFmpeg integration instance.

    Args:
        **kwargs: Arguments to pass to FFmpegIntegration constructor.

    Returns:
        Configured FFmpegIntegration instance.
    """
    return FFmpegIntegration(**kwargs)
