"""
Configuration models for the jupytext integration.

This module provides Pydantic models and a configuration provider for the
jupytext integration, handling settings for paired notebook/script
conversion (.ipynb <-> .py/.md/... and back).

Following the pandoc integration's convention: all file paths are handled
exclusively as strings, and any interaction with file paths (normalization,
validation, etc.) is delegated to the zeo_core.core.fs layer.
"""

import json
import os
from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator

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

    # Create a minimal fs stub if the module isn't available (for tests)
    fs = SimpleNamespace(
        is_valid_path=lambda path: True,
        normalize_path=lambda path: SimpleNamespace(success=True, path=path),
        normalize_path_with_info=lambda path: SimpleNamespace(success=True, path=path),
        get_path_info=lambda path: SimpleNamespace(success=True),
        expand_user_vars=lambda path: (
            path if not path or not isinstance(path, str) else os.path.expanduser(path)
        ),
        read_yaml=lambda path: SimpleNamespace(success=True, data={}),
    )


class ValidationConfig(BaseModel):
    """Configuration for notebook conversion validation."""

    verify_structure: bool = Field(
        default=True,
        description="Whether to verify the parsed notebook has at least one cell",
    )
    min_file_size: int = Field(
        default=10, description="Minimum output file size in bytes"
    )


class MetadataConfig(BaseModel):
    """Configuration for provenance metadata injected into converted notebooks."""

    inject_provenance: bool = Field(
        default=True,
        description="Whether to inject a 'zeocore' provenance block into "
        "notebook metadata (source path, tool name) on conversion to .ipynb",
    )
    default_kernelspec: dict[str, str] = Field(
        default_factory=lambda: {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        description="Kernelspec metadata applied when a parsed notebook has none",
    )


class JupytextConfig(BaseModel):
    """Main configuration for jupytext-based notebook conversion."""

    default_script_format: str = Field(
        default="py:percent",
        description="Default jupytext format id for script<->notebook conversion "
        "(e.g. 'py:percent', 'py:light', 'md')",
    )
    validation: ValidationConfig = Field(
        default_factory=ValidationConfig, description="Conversion validation settings"
    )
    metadata: MetadataConfig = Field(
        default_factory=MetadataConfig, description="Provenance metadata settings"
    )
    output_dir: str = Field(
        default="./output", description="Default output directory for converted files"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )

    @field_validator("output_dir")
    @classmethod
    def validate_output_dir(cls, v: str) -> str:
        """
        Validate that the output directory has a valid format.

        Delegates to zeo_core.core.fs to validate the path format.
        If fs service is not available, accepts any path.
        """
        try:
            if hasattr(fs, "get_path_info"):
                path_info = fs.get_path_info(v)
                if not getattr(path_info, "success", False):
                    raise ValueError(f"Invalid path format: {v}")
            return v
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            get_logger(__name__).warning(f"Path validation error: {str(e)}")
            return v


class JupytextConfigProvider(BaseConfigProvider):
    """Configuration provider for the jupytext integration."""

    # Deliberately unannotated class attribute, matching BaseConfigProvider's own
    # declaration style and the pandoc/google/llms sibling config providers -- an
    # explicit ClassVar[...] here conflicts with mypy's view of the base class's
    # un-annotated attribute of the same name.
    DEFAULT_CONFIG_LOCATIONS = [
        "./config/jupytext_config.yaml",
        "./config/zeo_config.yaml",
        "./zeo_config.yaml",
        "~/.zeo/jupytext_config.yaml",
    ]
    ENV_PREFIX: ClassVar[str] = "ZEO_JUPYTEXT_"

    def __init__(self, log_level: int = LOG_LEVELS[LogLevel.INFO]) -> None:
        """
        Initialize the jupytext configuration provider.

        Args:
            log_level: Logging level.
        """
        super().__init__(log_level)

    @property
    def name(self) -> str:
        """Get the name of the configuration provider."""
        return "JupytextConfig"

    def _extract_config(self, config_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract jupytext-specific configuration from the full configuration data.

        Args:
            config_data: Full configuration data.

        Returns:
            dict[str, Any]: Jupytext-specific configuration.
        """
        if "jupytext" in config_data and isinstance(config_data["jupytext"], dict):
            return config_data["jupytext"]
        if "notebook" in config_data and isinstance(config_data["notebook"], dict):
            return config_data["notebook"]
        return config_data

    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate configuration data against the jupytext configuration schema.

        Args:
            config: Configuration data to validate.

        Returns:
            bool: True if the configuration is valid, False otherwise.
        """
        try:
            JupytextConfig.model_validate(config)

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
        """
        Get default configuration values for jupytext.

        Returns:
            dict[str, Any]: Default configuration values.
        """
        default_config = JupytextConfig().model_dump()
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
        """
        Load configuration from environment variables.

        Returns:
            dict[str, Any]: Configuration from environment variables.
        """
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
