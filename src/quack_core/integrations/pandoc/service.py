# quack-core/src/quack_core/integrations/pandoc/service.py
"""Pandoc Integration Service

This module provides the main integration service for Pandoc document conversion.
It handles initialization, configuration, and delegates conversion operations to
specialized converters.
"""

import logging
from typing import Any, Optional

from quack_core.fs.service import FileSystemService
from quack_core.integrations.core.base import BaseIntegrationService
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.pandoc.config import PandocConfig, PandocConfigProvider
from quack_core.integrations.pandoc.converter import DocumentConverter
from quack_core.integrations.pandoc.operations.utils import verify_pandoc
from quack_core.paths.service import PathService

logger = logging.getLogger(__name__)


class PandocIntegration(BaseIntegrationService):
    """Main integration service for Pandoc document conversion.

    This service provides a high-level interface for converting documents
    using Pandoc. It manages configuration, initialization, and delegates
    conversion operations to specialized converters.

    Attributes:
        converter: Document converter instance (available after initialization)
        _config_loaded: Flag indicating if configuration was loaded successfully
        _pandoc_version: Cached Pandoc version string
    """

    def __init__(
            self,
            config_path: Optional[str] = None,
            output_dir: Optional[str] = None,
            config_provider: Optional[PandocConfigProvider] = None,
            paths_service: Optional[PathService] = None,
            fs_service: Optional[FileSystemService] = None,
            log_level: int | str | None = None,
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
        # Define a default log level for when None is provided
        default_log_level = "INFO"
        effective_log_level = log_level or default_log_level

        # Initialize config provider
        if config_provider is None:
            config_provider = PandocConfigProvider(log_level=effective_log_level)

        # Initialize base with proper parameters
        super().__init__(
            config_provider=config_provider,
            auth_provider=None,
            config=None,
            config_path=config_path,
            log_level=effective_log_level
        )

        # Store service instances
        self.paths_service = paths_service or PathService()

        # Use /tmp as fallback base_dir to avoid issues when cwd is deleted (common in tests)
        try:
            self.fs_service = fs_service or FileSystemService()
        except (FileNotFoundError, OSError):
            # If cwd() fails (e.g., in tests), use /tmp as base directory
            import tempfile
            self.fs_service = fs_service or FileSystemService(
                base_dir=tempfile.gettempdir())

        # Store initialization parameters
        self._init_output_dir = output_dir
        self._config_path = config_path

        # Will be set during initialization
        self.converter: Optional[DocumentConverter] = None
        self._config_loaded = False
        self._pandoc_version: Optional[str] = None

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
            return IntegrationResult.error_result(
                error="Pandoc integration is not initialized. Call initialize() first.",
                message="Pandoc integration is not initialized. Call initialize() first.",
            )
        return None

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
        try:
            # Verify Pandoc is available and cache version
            try:
                pandoc_version = verify_pandoc()
                self._pandoc_version = pandoc_version
                logger.info(f"Pandoc version {pandoc_version} detected")
            except Exception as e:
                error_msg = f"Pandoc not available: {str(e)}"
                logger.error(error_msg)
                self._initialized = False
                return IntegrationResult.error_result(
                    error=error_msg,
                    message=error_msg
                )

            # Load configuration using config provider
            config_result = self.config_provider.load_config(
                config_path=self._config_path
            )

            # Extract config content from result
            config_dict = {}
            if config_result.success:
                config_dict = config_result.content or {}
            else:
                # If config loading failed, log warning but continue with defaults
                logger.warning(f"Failed to load config: {config_result.error}")
                config_dict = {}

            # Apply initialization overrides
            if self._init_output_dir:
                config_dict['output_dir'] = self._init_output_dir

            # Validate and create PandocConfig
            try:
                conversion_config = PandocConfig(**config_dict)
                self._config_loaded = True
            except Exception as e:
                error_msg = f"Invalid configuration: {str(e)}"
                logger.error(error_msg)
                self._initialized = False
                return IntegrationResult.error_result(
                    error=error_msg,
                    message=error_msg
                )

            # Store config in self.config for compatibility
            self.config = conversion_config

            # Ensure output directory exists
            output_dir = conversion_config.output_dir
            if output_dir:
                # Expand user vars - returns a string directly, not a result
                from quack_core.fs.service import standalone
                expanded_dir = standalone.expand_user_vars(output_dir)
                if hasattr(expanded_dir, 'data'):
                    expanded_dir = expanded_dir.data

                # Create directory
                create_result = self.fs_service.create_directory(expanded_dir)
                if not create_result.success:
                    error_msg = f"Failed to create output directory: {create_result.error}"
                    logger.error(error_msg)
                    self._initialized = False
                    return IntegrationResult.error_result(
                        error=error_msg,
                        message=error_msg
                    )

                logger.info(f"Output directory ready: {expanded_dir}")

            # Initialize converter
            self.converter = DocumentConverter(
                config=conversion_config
            )

            # Mark as initialized BEFORE returning success
            self._initialized = True
            logger.info("Pandoc integration initialized successfully")

            return IntegrationResult(
                success=True,
                message="Pandoc integration initialized successfully",
                content={"version": pandoc_version}
            )

        except Exception as e:
            error_msg = f"Failed to initialize Pandoc integration: {str(e)}"
            logger.error(error_msg)
            self._initialized = False
            return IntegrationResult.error_result(
                error=error_msg,
                message=error_msg
            )

    def is_available(self) -> bool:
        """Check if the Pandoc integration is available.

        Returns:
            True if available, False otherwise
        """
        return self._initialized and self.converter is not None

    def get_pandoc_version(self) -> Optional[str]:
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
            output_path: Optional[str] = None,
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
            input_result = self.paths_service.resolve_project_path(input_path)
            input_path = input_result.path if input_result.success else input_path

            if output_path:
                output_result = self.paths_service.resolve_project_path(output_path)
                output_path = output_result.path if output_result.success else output_path

            # Use converter - signature is: convert_file(input_path, output_path, output_format)
            return self.converter.convert_file(
                input_path,
                output_path,
                "markdown"
            )

        except Exception as e:
            error_msg = f"HTML to Markdown conversion failed: {str(e)}"
            logger.error(error_msg)
            return IntegrationResult.error_result(
                error=error_msg,
                message=error_msg
            )

    def markdown_to_docx(
            self,
            input_path: str,
            output_path: Optional[str] = None,
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
            input_result = self.paths_service.resolve_project_path(input_path)
            input_path = input_result.path if input_result.success else input_path

            if output_path:
                output_result = self.paths_service.resolve_project_path(output_path)
                output_path = output_result.path if output_result.success else output_path

            # Use converter - signature is: convert_file(input_path, output_path, output_format)
            return self.converter.convert_file(
                input_path,
                output_path,
                "docx"
            )

        except Exception as e:
            error_msg = f"Markdown to DOCX conversion failed: {str(e)}"
            logger.error(error_msg)
            return IntegrationResult.error_result(
                error=error_msg,
                message=error_msg
            )

    def convert_directory(
            self,
            input_dir: str,
            output_format: str,
            output_dir: Optional[str] = None,
            pattern: str = "*",
            **options: Any
    ) -> IntegrationResult:
        """Convert all matching files in a directory.

        Args:
            input_dir: Directory containing input files
            output_format: Target format (e.g., 'markdown', 'docx')
            output_dir: Optional output directory (uses config default if not provided)
            pattern: File pattern to match (default: "*")
            **options: Additional conversion options

        Returns:
            IntegrationResult with list of output paths or error
        """
        init_error = self._ensure_initialized()
        if init_error:
            return init_error

        try:
            # Resolve paths
            input_result = self.paths_service.resolve_project_path(input_dir)
            input_dir = input_result.path if input_result.success else input_dir

            if output_dir:
                output_result = self.paths_service.resolve_project_path(output_dir)
                output_dir = output_result.path if output_result.success else output_dir

            # Verify input directory exists
            dir_info = self.fs_service.get_file_info(input_dir)
            if not dir_info.success or not dir_info.exists:
                return IntegrationResult.error_result(
                    error=f"Input directory not found: {input_dir}",
                    message=f"Input directory not found: {input_dir}"
                )

            if not dir_info.is_dir:
                return IntegrationResult.error_result(
                    error=f"Path is not a directory: {input_dir}",
                    message=f"Path is not a directory: {input_dir}"
                )

            # Find files matching pattern
            find_result = self.fs_service.find_files(
                directory=input_dir,
                pattern=pattern
            )

            if not find_result.success:
                return IntegrationResult.error_result(
                    error=f"Failed to find files: {find_result.error}",
                    message=f"Failed to find files: {find_result.error}"
                )

            input_files = find_result.files or []
            if not input_files:
                return IntegrationResult(
                    success=True,
                    message="No files found matching pattern",
                    content=[]
                )

            # Create ConversionTask objects for each file
            from quack_core.integrations.pandoc.models import ConversionTask
            from quack_core.integrations.pandoc.operations import get_file_info

            tasks = []
            for file_path in input_files:
                try:
                    file_info = get_file_info(file_path)
                    task = ConversionTask(
                        source=file_info,
                        target_format=output_format,
                        output_path=None  # Let converter determine output path
                    )
                    tasks.append(task)
                except Exception as e:
                    logger.warning(f"Failed to create task for {file_path}: {e}")
                    continue

            if not tasks:
                return IntegrationResult.error_result(
                    error="No valid conversion tasks could be created",
                    message="No valid conversion tasks could be created"
                )

            # Use converter for batch processing
            return self.converter.convert_batch(
                tasks=tasks,
                output_dir=output_dir
            )

        except Exception as e:
            error_msg = f"Directory conversion failed: {str(e)}"
            logger.error(error_msg)
            return IntegrationResult.error_result(
                error=error_msg,
                message=error_msg
            )


# Factory function for creating integration instance
def create_integration(**kwargs: Any) -> PandocIntegration:
    """Create a new Pandoc integration instance.

    Args:
        **kwargs: Arguments to pass to PandocIntegration constructor

    Returns:
        Configured PandocIntegration instance
    """
    return PandocIntegration(**kwargs)