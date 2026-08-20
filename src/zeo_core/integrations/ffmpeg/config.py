"""
Configuration models for the ffmpeg integration.

This module provides Pydantic models and a configuration provider for the ffmpeg
integration, following the same shape as
`zeo_core.integrations.pandoc.config` -- settings for media probing/transcoding
via the `ffmpeg-zeo` package (not the raw ffmpeg binary directly).
"""

import json
import os
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from zeo_core.config.models import LoggingConfig
from zeo_core.core.logging import LOG_LEVELS, LogLevel, get_logger
from zeo_core.integrations.core.base import BaseConfigProvider

logger = get_logger(__name__)

# Import fs module with error handling. `fs` is deliberately duck-typed here: the
# except branch swaps in a SimpleNamespace whose lambda attributes mimic the real
# module's callable surface (same success/data/path shape) but not its precise
# per-function return types -- annotated `Any` at the declaration site rather than
# per-call-site ignores, matching pandoc/config.py's own fs-stub precedent.
fs: Any
try:
    from zeo_core.core.fs.service import standalone as fs
except ImportError:
    logger.error("Could not import zeo_core.core.fs.service")
    from types import SimpleNamespace

    fs = SimpleNamespace(
        get_path_info=lambda path: SimpleNamespace(success=True),
        normalize_path_with_info=lambda path: SimpleNamespace(success=True, path=path),
        expand_user_vars=lambda path: (
            path if not path or not isinstance(path, str) else os.path.expanduser(path)
        ),
    )


class FFmpegConfig(BaseModel):
    """Main configuration for the ffmpeg integration."""

    output_dir: str = Field(
        default="./output", description="Output directory for rendered media"
    )
    timeout_sec: float = Field(
        default=600.0,
        description="Default subprocess timeout in seconds for ffmpeg/ffprobe runs",
    )
    overwrite: bool = Field(
        default=True,
        description="Whether to overwrite existing output files by default",
    )
    download_missing_binaries: bool = Field(
        default=False,
        description=(
            "Whether ffmpeg-zeo may download LGPL static ffmpeg/ffprobe builds "
            "(Linux/Windows only) when no binary is found on PATH or via env vars."
        ),
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )

    @property
    def download_binaries(self) -> bool:
        """Alias matching ffmpeg-zeo's own `download=` kwarg naming."""
        return self.download_missing_binaries


class FFmpegConfigProvider(BaseConfigProvider):
    """Configuration provider for the ffmpeg integration."""

    # Deliberately unannotated (matches BaseConfigProvider's own declaration
    # style, and the pandoc/google/llms sibling config providers) -- an
    # explicit ClassVar[...] here conflicts with mypy's view of the base
    # class's un-annotated attribute of the same name.
    DEFAULT_CONFIG_LOCATIONS = [
        "./config/ffmpeg_config.yaml",
        "./config/zeo_config.yaml",
        "./zeo_config.yaml",
        "~/.zeo/ffmpeg_config.yaml",
    ]
    ENV_PREFIX: ClassVar[str] = "ZEO_FFMPEG_"

    def __init__(self, log_level: int = LOG_LEVELS[LogLevel.INFO]) -> None:
        super().__init__(log_level)

    @property
    def name(self) -> str:
        """Get the name of the configuration provider."""
        return "FFmpegConfig"

    def _extract_config(self, config_data: dict[str, Any]) -> dict[str, Any]:
        if "ffmpeg" in config_data and isinstance(config_data["ffmpeg"], dict):
            return config_data["ffmpeg"]
        return config_data

    def validate_config(self, config: dict[str, Any]) -> bool:
        try:
            FFmpegConfig.model_validate(config)

            if "output_dir" in config:
                path = config["output_dir"]
                if not isinstance(path, str) or path.strip() == "":
                    self.logger.warning(f"Output directory path is invalid: {path}")
                    return False
                if any(char in path for char in ["?", "*", "<", ">", "|"]):
                    self.logger.warning(
                        f"Output directory path contains invalid characters: {path}"
                    )
                    return False

            return True
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False

    def get_default_config(self) -> dict[str, Any]:
        default_config = FFmpegConfig().model_dump()
        output_dir = default_config.get("output_dir")
        if output_dir and hasattr(fs, "normalize_path_with_info"):
            try:
                normalized_path = fs.normalize_path_with_info(output_dir)
                if getattr(normalized_path, "success", False):
                    default_config["output_dir"] = normalized_path.path
            except Exception as e:
                self.logger.warning(f"Failed to normalize output dir path: {e}")
        return default_config

    def load_from_environment(self) -> dict[str, Any]:
        config: dict[str, Any] = {}
        for key, value in os.environ.items():
            if key.startswith(self.ENV_PREFIX):
                config_key = key[len(self.ENV_PREFIX) :].lower()

                if value.startswith(("[", "{")) or value.lower() in ("true", "false"):
                    try:
                        config[config_key] = json.loads(value)
                    except json.JSONDecodeError:
                        config[config_key] = value
                elif config_key == "output_dir" or config_key.endswith("_path"):
                    try:
                        if hasattr(fs, "expand_user_vars") and callable(
                            fs.expand_user_vars
                        ):
                            try:
                                expanded_path = fs.expand_user_vars(value)
                                config[config_key] = os.path.abspath(expanded_path)
                            except Exception:
                                config[config_key] = os.path.abspath(
                                    os.path.expanduser(value)
                                )
                        else:
                            config[config_key] = os.path.abspath(
                                os.path.expanduser(value)
                            )
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to normalize path from env var: {e}"
                        )
                        config[config_key] = value
                else:
                    config[config_key] = value
        return config
