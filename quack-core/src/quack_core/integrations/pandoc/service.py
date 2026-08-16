# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/pandoc/service.py
# === QV-LLM:END ===

"""Pandoc Integration Service

This module provides the main integration service for Pandoc document conversion.
It handles initialization, configuration, and delegates conversion _ops to
specialized converters.
"""

import logging
from typing import Any

from quack_core.core.errors import QuackIntegrationError
from quack_core.core.fs.service import FileSystemService
from quack_core.core.logging import LOG_LEVELS, LogLevel
from quack_core.core.paths.service import PathService
from quack_core.integrations.core.base import BaseIntegrationService
from quack_core.integrations.core.protocols import ConfigProviderProtocol
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.pandoc.config import PandocConfig, PandocConfigProvider
from quack_core.integrations.pandoc.converter import DocumentConverter
from quack_core.integrations.pandoc.operations.utils import verify_pandoc

logger = logging.getLogger(__name__)


class PandocIntegration(BaseIntegrationService):
    """Main integration service for Pandoc document conversion.

    This service provides a high-level interface for converting documents
    using Pandoc. It manages configuration, initialization, and delegates
    conversion _ops to specialized converters.

    Attributes:
        converter: Document converter instance (available after initialization)
        _config_loaded: Flag indicating if configuration was loaded successfully
        _pandoc_version: Cached Pandoc version string
    """

    def __init__(
        self,
        config_path: str | None = None,
        output_dir: str | None = None,
        config_provider: PandocConfigProvider | None = None,
        paths_service: PathService | None = None,
        fs_service: FileSystemService | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
    ) -> None:
        """Initialize the Pandoc integration service.

        Args:
            config_path: Optional path to configuration file
            output_dir: Optional output directory override
            config_provider: Optional custom config provider
            paths_service: Optional paths service instance
            fs_service: Optional filesystem service instance
            log_level: Logging level
        """
        # Initialize config provider
        if config_provider is None:
            config_provider = PandocConfigProvider(log_level=log_level)

        # Initialize base with proper parameters
        super().__init__(
            config_provider=config_provider,
            auth_provider=None,
            config=None,
            config_path=config_path,
            log_level=log_level,
        )

        # Store service instances
        self.paths_service = paths_service or PathService()

        # Use /tmp as fallback base_dir to avoid issues when cwd is deleted
        # (common in tests)
        try:
            self.fs_service = fs_service or FileSystemService()
        except (FileNotFoundError, OSError):
            # If cwd() fails (e.g., in tests), use /tmp as base directory
            import tempfile

            self.fs_service = fs_service or FileSystemService(
                base_dir=tempfile.gettempdir()
            )

        # Store initialization parameters
        self._init_output_dir = output_dir
        self._config_path = config_path

        # Will be set during initialization
        self.converter: DocumentConverter | None = None
        self._config_loaded = False
        self._pandoc_version: str | None = None

    @property
    def name(self) -> str:
        """Name of the integration."""
        return "Pandoc"

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
            logger.error("Pandoc integration is not initialized")
            not_initialized_msg = (
                "Pandoc integration is not initialized. Call initialize() first."
            )
            return IntegrationResult.error_result(
                error=not_initialized_msg,
                message=not_initialized_msg,
            )
        return None

    def _resolve_path_str(self, path: str) -> str:
        """Resolve a path to the project root, falling back to the original string.

        `PathService.resolve_project_path` returns a `PathResult` whose `.path` is
        `Path | None` even on success (the model's general contract); this coerces
        to `str` and falls back to the original input on failure or a missing path.

        Args:
            path: Path to resolve.

        Returns:
            str: The resolved path as a string, or the original `path` unchanged.
        """
        result = self.paths_service.resolve_project_path(path)
        if result.success and result.path is not None:
            return str(result.path)
        return path

    def _require_config_provider(self) -> ConfigProviderProtocol:
        """Return `self.config_provider`, narrowed to non-None.

        `__init__` always sets a concrete `PandocConfigProvider` (never `None`) --
        the base class types `config_provider` nullable for the general integration
        case. Raises if that invariant is ever violated (defensive, not expected).
        """
        if self.config_provider is None:
            raise QuackIntegrationError(
                "PandocIntegration.config_provider is unexpectedly None"
            )
        return self.config_provider

    def initialize(self) -> IntegrationResult:
        """Initialize the Pandoc integration.

        This method:
        1. Verifies Pandoc is available
        2. Loads and validates Pandoc-specific configuration
        3. Creates output directory if needed
        4. Initializes the document converter

        Returns:
            IntegrationResult with success status and any error messages
        """
        # 1. Verify Pandoc Availability
        try:
            pandoc_version = verify_pandoc()
            self._pandoc_version = pandoc_version
            logger.info(f"Pandoc version {pandoc_version} detected")
        except Exception as e:
            # Catch ALL exceptions here (ImportError, OSError, QuackIntegrationError)
            # to ensure we return a result object rather than crashing
            error_msg = f"Pandoc not available: {str(e)}"
            logger.error(error_msg)
            self._initialized = False
            return IntegrationResult.error_result(error=error_msg, message=error_msg)

        # 2. Load Configuration
        try:
            config_provider = self._require_config_provider()
            config_result = config_provider.load_config(
                config_path=self._config_path
            )

            if not config_result.success:
                logger.warning(f"Failed to load config: {config_result.error}")

            # Assign directly to avoid unused variable warning
            config_dict = config_result.content or {}

            # Apply initialization overrides
            if self._init_output_dir:
                config_dict["output_dir"] = self._init_output_dir

            # Validate and create PandocConfig
            conversion_config = PandocConfig(**config_dict)
            self._config_loaded = True

            # Store config in self.config for compatibility. Base class types this
            # dict[str, Any] | None for the general integration case; this subclass
            # deliberately stores the validated PandocConfig object instead.
            self.config = conversion_config  # type: ignore[assignment]

        except Exception as e:
            error_msg = f"Invalid configuration: {str(e)}"
            logger.error(error_msg)
            self._initialized = False
            return IntegrationResult.error_result(error=error_msg, message=error_msg)

        # 3. Setup File System (Output Directory)
        try:
            output_dir = conversion_config.output_dir
            if output_dir:
                # Use fs_service for expand_user_vars
                expanded_dir_result = self.fs_service.expand_user_vars(output_dir)

                # Extract path string from DataResult
                if expanded_dir_result.success and expanded_dir_result.data:
                    expanded_dir = expanded_dir_result.data
                else:
                    # Fallback to original if expansion fails
                    expanded_dir = output_dir

                # Create directory
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

        # 4. Initialize Converter
        try:
            self.converter = DocumentConverter(config=conversion_config)

            # Mark as initialized BEFORE returning success
            self._initialized = True
            logger.info("Pandoc integration initialized successfully")

            return IntegrationResult(
                success=True,
                message="Pandoc integration initialized successfully",
                content={"version": pandoc_version},
            )
        except Exception as e:
            # Catch-all for unexpected errors during final converter setup
            error_msg = f"Failed to initialize converter: {str(e)}"
            logger.error(error_msg)
            self._initialized = False
            return IntegrationResult.error_result(error=error_msg, message=error_msg)

    def is_available(self) -> bool:
        """Check if the Pandoc integration is available.

        Returns:
            True if available, False otherwise
        """
        return self._initialized and self.converter is not None

    def get_pandoc_version(self) -> str | None:
        """Get the version of Pandoc being used.

        Returns:
            Pandoc version string, or None if not initialized
        """
        return self._pandoc_version

    def is_pandoc_available(self) -> bool:
        """Check if Pandoc is available on the system.

        Returns:
            True if Pandoc is available, False otherwise
        """
        try:
            version = verify_pandoc()
            if not self._pandoc_version:
                self._pandoc_version = version
            return True
        except Exception:
            return False

    def html_to_markdown(
        self,
        input_path: str,
        output_path: str | None = None,
    ) -> IntegrationResult:
        """Convert HTML file to Markdown.

        Args:
            input_path: Path to input HTML file
            output_path: Optional output path for Markdown file

        Returns:
            IntegrationResult with output path or error
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error

        try:
            # Resolve paths
            input_path = self._resolve_path_str(input_path)
            if output_path:
                output_path = self._resolve_path_str(output_path)

            # Use converter - signature is:
            # convert_file(input_path, output_path, output_format)
            if self.converter is None:
                raise QuackIntegrationError(
                    "PandocIntegration.converter is unexpectedly None after "
                    "_ensure_initialized() passed"
                )
            return self.converter.convert_file(input_path, output_path, "markdown")

        except Exception as e:
            error_msg = f"HTML to Markdown conversion failed: {str(e)}"
            logger.error(error_msg)
            return IntegrationResult.error_result(error=error_msg, message=error_msg)

    def markdown_to_docx(
        self,
        input_path: str,
        output_path: str | None = None,
    ) -> IntegrationResult:
        """Convert Markdown file to DOCX.

        Args:
            input_path: Path to input Markdown file
            output_path: Optional output path for DOCX file

        Returns:
            IntegrationResult with output path or error
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error

        try:
            # Resolve paths
            input_path = self._resolve_path_str(input_path)
            if output_path:
                output_path = self._resolve_path_str(output_path)

            # Use converter - signature is:
            # convert_file(input_path, output_path, output_format)
            if self.converter is None:
                raise QuackIntegrationError(
                    "PandocIntegration.converter is unexpectedly None after "
                    "_ensure_initialized() passed"
                )
            return self.converter.convert_file(input_path, output_path, "docx")

        except Exception as e:
            error_msg = f"Markdown to DOCX conversion failed: {str(e)}"
            logger.error(error_msg)
            return IntegrationResult.error_result(error=error_msg, message=error_msg)

    def _resolve_convert_directory_paths(
        self, input_dir: str, output_dir: str | None
    ) -> tuple[str, str | None]:
        """Resolve the input and output directories to project paths.

        Args:
            input_dir: Directory containing input files.
            output_dir: Optional output directory.

        Returns:
            Tuple of (resolved_input_dir, resolved_output_dir).
        """
        input_dir = self._resolve_path_str(input_dir)
        if output_dir:
            output_dir = self._resolve_path_str(output_dir)

        return input_dir, output_dir

    def _verify_convert_directory(self, input_dir: str) -> IntegrationResult | None:
        """Verify that the input directory exists and is a directory.

        Args:
            input_dir: Resolved directory containing input files.

        Returns:
            IntegrationResult error if verification fails, None if valid.
        """
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
        self, input_files: list[str], output_format: str, options: dict[str, Any]
    ) -> list[Any]:
        """Build ConversionTask objects for each discovered input file.

        Args:
            input_files: Paths to files to convert.
            output_format: Target format (e.g., 'markdown', 'docx').
            options: Additional conversion options passed to each task.

        Returns:
            list[ConversionTask]: Tasks successfully built. Files that fail
            to yield file info are skipped with a warning.
        """
        from quack_core.integrations.pandoc.models import ConversionTask
        from quack_core.integrations.pandoc.operations import get_file_info

        tasks = []
        for file_path in input_files:
            try:
                file_info = get_file_info(file_path)
                # Pass **options into the task
                task = ConversionTask(
                    source=file_info,
                    target_format=output_format,
                    output_path=None,  # Let converter determine output path
                    options=options,  # Pass user provided options
                )
                tasks.append(task)
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
        **options: Any,  # noqa: ANN401 -- arbitrary passthrough conversion options
    ) -> IntegrationResult:
        """Convert all matching files in a directory.

        Args:
            input_dir: Directory containing input files
            output_format: Target format (e.g., 'markdown', 'docx')
            output_dir: Optional output directory (uses config default if not provided)
            pattern: File pattern to match (default: "*")
            **options: Additional conversion options passed to the conversion task

        Returns:
            IntegrationResult with list of output paths or error
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error

        try:
            # Resolve paths
            input_dir, output_dir = self._resolve_convert_directory_paths(
                input_dir, output_dir
            )

            # Verify input directory exists
            verify_error = self._verify_convert_directory(input_dir)
            if verify_error:
                return verify_error

            # Find files matching pattern
            find_result = self.fs_service.find_files(
                path=input_dir, pattern=pattern
            )

            if not find_result.success:
                return IntegrationResult.error_result(
                    error=f"Failed to find files: {find_result.error}",
                    message=f"Failed to find files: {find_result.error}",
                )

            input_files = find_result.files or []
            if not input_files:
                return IntegrationResult(
                    success=True, message="No files found matching pattern", content=[]
                )

            # Create ConversionTask objects for each file
            tasks = self._build_conversion_tasks(input_files, output_format, options)

            if not tasks:
                return IntegrationResult.error_result(
                    error="No valid conversion tasks could be created",
                    message="No valid conversion tasks could be created",
                )

            # Use converter for batch processing
            return self.converter.convert_batch(tasks=tasks, output_dir=output_dir)

        except Exception as e:
            error_msg = f"Directory conversion failed: {str(e)}"
            logger.error(error_msg)
            return IntegrationResult.error_result(error=error_msg, message=error_msg)


# Factory function for creating integration instance
def create_integration(**kwargs: Any) -> PandocIntegration:  # noqa: ANN401 -- forwarded verbatim to PandocIntegration.__init__
    """Create a new Pandoc integration instance.

    Args:
        **kwargs: Arguments to pass to PandocIntegration constructor

    Returns:
        Configured PandocIntegration instance
    """
    return PandocIntegration(**kwargs)
