"""Jupytext Integration Service

This module provides the main integration service for jupytext notebook
conversion. It handles initialization, configuration, and delegates
conversion _ops to the ``NotebookConverter``. Structurally mirrors
``zeo_core.integrations.pandoc.service.PandocIntegration``.
"""

import logging
import os
from typing import Any

from zeo_core.core.errors import ZeoConfigurationError, ZeoIntegrationError
from zeo_core.core.fs.service import FileSystemService
from zeo_core.core.logging import LOG_LEVELS, LogLevel
from zeo_core.core.paths.service import PathService
from zeo_core.integrations.core.base import BaseIntegrationService
from zeo_core.integrations.core.protocols import ConfigProviderProtocol
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.jupytext.config import JupytextConfig, JupytextConfigProvider
from zeo_core.integrations.jupytext.converter import NotebookConverter
from zeo_core.integrations.jupytext.operations.utils import verify_jupytext

logger = logging.getLogger(__name__)


class JupytextIntegration(BaseIntegrationService):
    """Main integration service for jupytext notebook conversion.

    Provides a high-level interface for converting between paired
    jupytext script/markdown formats and Jupyter notebooks (``.ipynb``).
    This is the concrete operation the org's own quackslides app hand-rolls
    today via a direct ``jupytext``/``nbformat`` dependency
    (``quackslides/notebook/converter.py``); this integration gives future
    (and, potentially, migrated) consumers the same capability through
    zeocore's integration surface instead.

    Attributes:
        converter: Notebook converter instance (available after initialization)
        _config_loaded: Flag indicating if configuration was loaded successfully
        _jupytext_version: Cached jupytext version string
    """

    def __init__(
        self,
        config_path: str | None = None,
        output_dir: str | None = None,
        config_provider: JupytextConfigProvider | None = None,
        paths_service: PathService | None = None,
        fs_service: FileSystemService | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
    ) -> None:
        """Initialize the jupytext integration service.

        Args:
            config_path: Optional path to configuration file
            output_dir: Optional output directory override
            config_provider: Optional custom config provider
            paths_service: Optional paths service instance
            fs_service: Optional filesystem service instance
            log_level: Logging level
        """
        if config_provider is None:
            config_provider = JupytextConfigProvider(log_level=log_level)

        super().__init__(
            config_provider=config_provider,
            auth_provider=None,
            config=None,
            config_path=config_path,
            log_level=log_level,
        )

        self.paths_service = paths_service or PathService()

        # Use /tmp as fallback base_dir to avoid issues when cwd is deleted
        # (common in tests) -- same precedent as PandocIntegration.__init__.
        try:
            self.fs_service = fs_service or FileSystemService()
        except FileNotFoundError, OSError:
            import tempfile

            self.fs_service = fs_service or FileSystemService(
                base_dir=tempfile.gettempdir()
            )

        self._init_output_dir = output_dir
        self._config_path = config_path

        self.converter: NotebookConverter | None = None
        self._config_loaded = False
        self._jupytext_version: str | None = None

    @property
    def name(self) -> str:
        """Name of the integration."""
        return "Jupytext"

    @property
    def version(self) -> str:
        """Version of the integration."""
        return "1.0.0"

    def _ensure_initialized(self) -> IntegrationResult | None:
        """Ensure the integration is initialized.

        Returns:
            IntegrationResult error if not initialized, None if initialized
        """
        if not self._initialized:
            logger.error("Jupytext integration is not initialized")
            not_initialized_msg = (
                "Jupytext integration is not initialized. Call initialize() first."
            )
            return IntegrationResult.error_result(
                error=not_initialized_msg,
                message=not_initialized_msg,
            )
        return None

    def _resolve_path_str(self, path: str) -> str:
        """Resolve a path to the project root, falling back to the original string.

        Args:
            path: Path to resolve.

        Returns:
            str: The resolved path as a string, or the original `path` unchanged.
        """
        result = self.paths_service.resolve_project_path(path)
        if result.success and result.path is not None:
            return str(result.path)
        return path

    def _default_output_path(self, input_path: str, extension: str) -> str:
        """Synthesize an output path when the caller did not supply one.

        Same directory and base filename as `input_path`, with `extension`
        (e.g. ".ipynb", ".py") swapped in.

        Args:
            input_path: Resolved path to the source file.
            extension: Target extension, including the leading dot.

        Returns:
            str: The synthesized output path.
        """
        directory = os.path.dirname(input_path)
        name, _ = os.path.splitext(os.path.basename(input_path))
        return os.path.join(directory, name + extension)

    def _require_config_provider(self) -> ConfigProviderProtocol:
        """Return `self.config_provider`, narrowed to non-None.

        `__init__` always sets a concrete `JupytextConfigProvider` (never
        `None`) -- the base class types `config_provider` nullable for the
        general integration case. Raises if that invariant is ever violated
        (defensive, not expected).
        """
        if self.config_provider is None:
            raise ZeoIntegrationError(
                "JupytextIntegration.config_provider is unexpectedly None"
            )
        return self.config_provider

    def _load_config_dict(self) -> dict[str, Any]:
        """Load the raw jupytext config dict from the config provider.

        No config file present is the common case for this integration --
        jupytext is a pure-Python library with no external binary to gate on
        (unlike pandoc, whose own step 1 fails first in that scenario and
        never reaches this point) -- so a missing config file falls back to
        an empty dict (later validated into `JupytextConfig()`'s defaults)
        rather than raising. A real, present-but-invalid config file still
        surfaces via `JupytextConfig(**config_dict)` validation downstream.

        Returns:
            dict[str, Any]: Raw config data (possibly empty).
        """
        config_provider = self._require_config_provider()
        try:
            config_result = config_provider.load_config(config_path=self._config_path)
        except ZeoConfigurationError as e:
            logger.info(f"No config file found, using defaults: {e}")
            return {}

        if not config_result.success:
            logger.warning(f"Failed to load config: {config_result.error}")
            return {}
        return config_result.content or {}

    def _initialize_config(self) -> IntegrationResult | None:
        """Step 2 of initialize(): load, override, and validate configuration.

        Returns:
            IntegrationResult error if configuration is invalid, None on success.
        """
        try:
            config_dict = self._load_config_dict()

            if self._init_output_dir:
                config_dict["output_dir"] = self._init_output_dir

            notebook_config = JupytextConfig(**config_dict)
            self._config_loaded = True

            # Base class types this dict[str, Any] | None for the general
            # integration case; this subclass deliberately stores the
            # validated JupytextConfig object instead (same pattern as
            # PandocIntegration.initialize()).
            self.config = notebook_config  # type: ignore[assignment]
            return None
        except Exception as e:
            error_msg = f"Invalid configuration: {str(e)}"
            logger.error(error_msg)
            self._initialized = False
            return IntegrationResult.error_result(error=error_msg, message=error_msg)

    def initialize(self) -> IntegrationResult:
        """Initialize the jupytext integration.

        This method:
        1. Verifies jupytext is available
        2. Loads and validates jupytext-specific configuration
        3. Creates output directory if needed
        4. Initializes the notebook converter

        Returns:
            IntegrationResult with success status and any error messages
        """
        # 1. Verify jupytext availability
        try:
            jupytext_version = verify_jupytext()
            self._jupytext_version = jupytext_version
            logger.info(f"jupytext version {jupytext_version} detected")
        except Exception as e:
            error_msg = f"jupytext not available: {str(e)}"
            logger.error(error_msg)
            self._initialized = False
            return IntegrationResult.error_result(error=error_msg, message=error_msg)

        # 2. Load configuration
        config_error = self._initialize_config()
        if config_error:
            return config_error
        if not isinstance(self.config, JupytextConfig):
            # Defensive: _initialize_config() only returns None (success) after
            # setting self.config to a validated JupytextConfig; this narrows
            # that invariant for mypy without an assert-as-control-flow.
            error_msg = (
                "JupytextIntegration.config is unexpectedly not a JupytextConfig"
            )
            logger.error(error_msg)
            self._initialized = False
            return IntegrationResult.error_result(error=error_msg, message=error_msg)
        notebook_config: JupytextConfig = self.config

        # 3. Setup file system (output directory)
        try:
            output_dir = notebook_config.output_dir
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

        except Exception as e:
            error_msg = f"File system initialization failed: {str(e)}"
            logger.error(error_msg)
            self._initialized = False
            return IntegrationResult.error_result(error=error_msg, message=error_msg)

        # 4. Initialize converter
        try:
            self.converter = NotebookConverter(config=notebook_config)

            self._initialized = True
            logger.info("Jupytext integration initialized successfully")

            return IntegrationResult(
                success=True,
                message="Jupytext integration initialized successfully",
                content={"version": jupytext_version},
            )
        except Exception as e:
            error_msg = f"Failed to initialize converter: {str(e)}"
            logger.error(error_msg)
            self._initialized = False
            return IntegrationResult.error_result(error=error_msg, message=error_msg)

    def is_available(self) -> bool:
        """Check if the jupytext integration is available.

        Returns:
            True if available, False otherwise
        """
        return self._initialized and self.converter is not None

    def get_jupytext_version(self) -> str | None:
        """Get the version of jupytext being used.

        Returns:
            jupytext version string, or None if not initialized
        """
        return self._jupytext_version

    def is_jupytext_available(self) -> bool:
        """Check if jupytext is available on the system.

        Returns:
            True if jupytext is available, False otherwise
        """
        try:
            version = verify_jupytext()
            if not self._jupytext_version:
                self._jupytext_version = version
            return True
        except Exception:
            return False

    def script_to_notebook(
        self,
        input_path: str,
        output_path: str | None = None,
    ) -> IntegrationResult:
        """Convert a paired script/markdown file to a Jupyter notebook.

        This is the exact operation quackslides needs today: percent-format
        ``.py`` in, ``.ipynb`` out.

        Args:
            input_path: Path to input script/markdown file
            output_path: Optional output path for the .ipynb file

        Returns:
            IntegrationResult with output path or error
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error

        try:
            input_path = self._resolve_path_str(input_path)
            if output_path:
                output_path = self._resolve_path_str(output_path)
            else:
                output_path = self._default_output_path(input_path, ".ipynb")

            if self.converter is None:
                raise ZeoIntegrationError(
                    "JupytextIntegration.converter is unexpectedly None after "
                    "_ensure_initialized() passed"
                )
            return self.converter.convert_file(input_path, output_path, "ipynb")

        except Exception as e:
            error_msg = f"Script to notebook conversion failed: {str(e)}"
            logger.error(error_msg)
            return IntegrationResult.error_result(error=error_msg, message=error_msg)

    def notebook_to_script(
        self,
        input_path: str,
        output_path: str | None = None,
        script_format: str | None = None,
    ) -> IntegrationResult:
        """Convert a Jupyter notebook to a paired script/markdown file.

        Args:
            input_path: Path to input .ipynb file
            output_path: Optional output path for the script/markdown file
            script_format: Optional jupytext format id (defaults to the
                configured default_script_format)

        Returns:
            IntegrationResult with output path or error
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error

        try:
            input_path = self._resolve_path_str(input_path)
            fmt = script_format or (
                self.converter.config.default_script_format
                if self.converter
                else "py:percent"
            )
            extension = ".md" if fmt.startswith("md") else ".py"

            if output_path:
                output_path = self._resolve_path_str(output_path)
            else:
                output_path = self._default_output_path(input_path, extension)

            if self.converter is None:
                raise ZeoIntegrationError(
                    "JupytextIntegration.converter is unexpectedly None after "
                    "_ensure_initialized() passed"
                )
            return self.converter.convert_file(input_path, output_path, fmt)

        except Exception as e:
            error_msg = f"Notebook to script conversion failed: {str(e)}"
            logger.error(error_msg)
            return IntegrationResult.error_result(error=error_msg, message=error_msg)

    def _verify_convert_directory(self, input_dir: str) -> IntegrationResult | None:
        """Verify that the input directory exists and is a directory."""
        dir_info = self.fs_service.get_file_info(input_dir)
        if not dir_info.success or not dir_info.exists:
            return IntegrationResult.error_result(
                error=f"Input directory not found: {input_dir}",
                message=f"Input directory not found: {input_dir}",
            )
        if not dir_info.is_dir:
            return IntegrationResult.error_result(
                error=f"Path is not a directory: {input_dir}",
                message=f"Path is not a directory: {input_dir}",
            )
        return None

    def _build_conversion_tasks(
        self, input_files: list[str], output_format: str
    ) -> list[Any]:
        """Build ConversionTask objects for each discovered input file."""
        from zeo_core.integrations.jupytext.models import ConversionTask
        from zeo_core.integrations.jupytext.operations import get_file_info

        tasks = []
        for file_path in input_files:
            try:
                file_info = get_file_info(file_path)
                tasks.append(
                    ConversionTask(
                        source=file_info,
                        target_format=output_format,
                        output_path=None,
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to create task for {file_path}: {e}")
                continue
        return tasks

    def convert_directory(
        self,
        input_dir: str,
        output_format: str,
        output_dir: str | None = None,
        pattern: str = "*",
    ) -> IntegrationResult:
        """Convert all matching files in a directory.

        Args:
            input_dir: Directory containing input files
            output_format: Target jupytext format id (e.g. "ipynb")
            output_dir: Optional output directory (uses config default if not provided)
            pattern: File pattern to match (default: "*")

        Returns:
            IntegrationResult with list of output paths or error
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error

        try:
            input_dir = self._resolve_path_str(input_dir)
            if output_dir:
                output_dir = self._resolve_path_str(output_dir)

            verify_error = self._verify_convert_directory(input_dir)
            if verify_error:
                return verify_error

            find_result = self.fs_service.find_files(path=input_dir, pattern=pattern)
            if not find_result.success:
                return IntegrationResult.error_result(
                    error=f"Failed to find files: {find_result.error}",
                    message=f"Failed to find files: {find_result.error}",
                )

            input_files = [str(p) for p in (find_result.files or [])]
            if not input_files:
                return IntegrationResult(
                    success=True, message="No files found matching pattern", content=[]
                )

            tasks = self._build_conversion_tasks(input_files, output_format)
            if not tasks:
                return IntegrationResult.error_result(
                    error="No valid conversion tasks could be created",
                    message="No valid conversion tasks could be created",
                )

            if self.converter is None:
                raise ZeoIntegrationError(
                    "JupytextIntegration.converter is unexpectedly None after "
                    "_ensure_initialized() passed"
                )
            return self.converter.convert_batch(tasks=tasks, output_dir=output_dir)

        except Exception as e:
            error_msg = f"Directory conversion failed: {str(e)}"
            logger.error(error_msg)
            return IntegrationResult.error_result(error=error_msg, message=error_msg)


# Factory function for creating integration instance
def create_integration(**kwargs: Any) -> JupytextIntegration:  # noqa: ANN401 -- forwarded verbatim to JupytextIntegration.__init__
    """Create a new jupytext integration instance.

    Args:
        **kwargs: Arguments to pass to JupytextIntegration constructor

    Returns:
        Configured JupytextIntegration instance
    """
    return JupytextIntegration(**kwargs)
