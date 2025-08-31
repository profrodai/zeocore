# quack-core/src/quack-core/integrations/pandoc/service.py
"""
Pandoc integration service for quack_core.

This module provides the main service class for Pandoc integration,
handling document conversion between various formats.
All file path parameters and return types are represented as strings.
Filesystem _operations such as resolution and joining are delegated to quack-core.fs.
"""

import os
from collections.abc import Sequence
from datetime import datetime
from typing import cast

from quack_core.errors import QuackIntegrationError
from quack_core.integrations.core.base import BaseIntegrationService
from quack_core.integrations.core.results import IntegrationResult
from quack_core.integrations.pandoc.config import PandocConfig, PandocConfigProvider
from quack_core.integrations.pandoc.converter import DocumentConverter
from quack_core.integrations.pandoc.models import (
    ConversionMetrics,
    ConversionTask,
    FileInfo,
)
from quack_core.integrations.pandoc.operations import (
    get_file_info,
    verify_pandoc,
)
from quack_core.integrations.pandoc.protocols import PandocConversionProtocol
from quack_core.logging import LOG_LEVELS, LogLevel, get_logger

logger = get_logger(__name__)

# Import fs module with error handling
try:
    from quack_core.fs.service import standalone as fs
except ImportError:
    logger.error("Could not import quack-core.fs.service")
    from types import SimpleNamespace
    # Create a minimal fs stub if the module isn't available (for tests)
    fs = SimpleNamespace(
        get_file_info=lambda path: SimpleNamespace(success=True, exists=True, size=100),
        create_directory=lambda path, exist_ok=True: SimpleNamespace(success=True),
        join_path=lambda *parts: SimpleNamespace(success=True, data=os.path.join(*parts)),
        split_path=lambda path: SimpleNamespace(success=True, data=path.split(os.sep) if isinstance(path, str) else []),
        get_extension=lambda path: SimpleNamespace(success=True, data=path.split('.')[-1] if isinstance(path, str) and '.' in path else ""),
        read_text=lambda path, encoding=None: SimpleNamespace(success=True, content="")
    )

# Import paths module with error handling
try:
    from quack_core.paths import service as paths
except ImportError:
    logger.error("Could not import quack-core.paths")
    from types import SimpleNamespace
    # Create a minimal paths stub if the module isn't available (for tests)
    paths = SimpleNamespace(
        resolve_project_path=lambda path, *args: path,
        expand_user_vars=lambda path: path if not path or not isinstance(path, str) else os.path.expanduser(path)
    )


class PandocIntegration(BaseIntegrationService, PandocConversionProtocol):
    """
    Integration service for Pandoc document conversion.

    This service provides functionality for converting documents between
    various formats using Pandoc, with a focus on HTML to Markdown and
    Markdown to DOCX conversion.
    All file paths are handled as strings.
    """

    def __init__(
            self,
            config_path: str | None = None,
            output_dir: str | None = None,
            log_level: int = LOG_LEVELS[LogLevel.INFO],
    ) -> None:
        """
        Initialize the Pandoc integration service.

        Args:
            config_path: Path to the configuration file (as a string)
            output_dir: Directory to save converted files (as a string)
            log_level: Logging level
        """
        config_provider = PandocConfigProvider(log_level)

        # Initialize parent class
        super().__init__(
            config_provider=config_provider,
            auth_provider=None,
            config=None,
            config_path=config_path,
            log_level=log_level)

        # Store output_dir as a string
        self.output_dir: str | None = output_dir if output_dir else None
        self.metrics = ConversionMetrics(start_time=datetime.now())
        self.converter: DocumentConverter | None = None
        self._pandoc_version: str | None = None
        self._config_loaded = False

    @property
    def name(self) -> str:
        """Get the name of the integration."""
        return "Pandoc"

    @property
    def version(self) -> str:
        """Get the version of the integration."""
        return "1.0.0"

    def initialize(self) -> IntegrationResult:
        """
        Initialize the Pandoc integration.

        This method verifies Pandoc availability and loads configuration.

        Returns:
            IntegrationResult: Result of initialization.
        """
        try:
            # Call parent initialization
            init_result = super().initialize()
            if not init_result.success:
                return init_result

            # Load configuration as a dictionary
            config_dict = self.config or {}
            try:
                conversion_config = PandocConfig(**config_dict)
                self._config_loaded = True
            except Exception as e:
                logger.error(f"Invalid configuration: {str(e)}")
                return IntegrationResult.error_result(
                    f"Invalid configuration: {str(e)}"
                )

            # Override output directory if specified
            if self.output_dir:
                conversion_config.output_dir = self.output_dir

            # Verify Pandoc installation
            try:
                self._pandoc_version = verify_pandoc()
            except QuackIntegrationError as e:
                logger.error(f"Pandoc verification failed: {str(e)}")
                return IntegrationResult.error_result(
                    f"Pandoc verification failed: {str(e)}"
                )

            # Create converter instance
            self.converter = DocumentConverter(conversion_config)

            # Ensure output directory exists
            try:
                dir_result = fs.create_directory(conversion_config.output_dir,
                                               exist_ok=True)
                if not getattr(dir_result, 'success', False):
                    return IntegrationResult.error_result(
                        f"Failed to create output directory: {getattr(dir_result, 'error', 'Unknown error')}"
                    )
            except Exception as dir_err:
                logger.error(f"Failed to create output directory: {str(dir_err)}")
                return IntegrationResult.error_result(
                    f"Failed to create output directory: {str(dir_err)}"
                )

            self._initialized = True
            logger.info(
                f"Pandoc integration initialized successfully. Version: {self._pandoc_version}"
            )
            return IntegrationResult.success_result(
                message=f"Pandoc integration initialized successfully. Version: {self._pandoc_version}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Pandoc integration: {str(e)}")
            return IntegrationResult.error_result(
                f"Failed to initialize Pandoc integration: {str(e)}"
            )

    def html_to_markdown(
            self, html_path: str, output_path: str | None = None
    ) -> IntegrationResult[str]:
        """
        Convert HTML to Markdown.

        Args:
            html_path: Absolute path to the HTML file (as a string).
            output_path: Optional absolute path to save the Markdown file (as a string).

        Returns:
            IntegrationResult[str]: Result of the conversion with the output file path.
        """
        if not self._initialized:
            return cast(
                IntegrationResult[str],
                IntegrationResult.error_result("Pandoc integration not initialized"),
            )

        try:
            # Resolve paths
            try:
                html_path = paths.resolve_project_path(html_path)
            except Exception as e:
                # If path resolution fails, use the original path
                logger.warning(f"Failed to resolve project path: {str(e)}")

            # Handle output path
            if output_path is None and self.converter and hasattr(self.converter,
                                                                "config"):
                config = getattr(self.converter, "config", None)
                if isinstance(config, PandocConfig):
                    # Extract the basename from the path
                    try:
                        split_result = fs.split_path(html_path)
                        if not getattr(split_result, 'success', False):
                            return cast(
                                IntegrationResult[str],
                                IntegrationResult.error_result(
                                    f"Failed to extract filename from path: {getattr(split_result, 'error', 'Unknown error')}"
                                ),
                            )

                        # Get the filename and remove extension
                        filename = split_result.data[-1]
                        stem = os.path.splitext(filename)[0]

                        # Join with output directory
                        join_result = fs.join_path(config.output_dir, f"{stem}.md")
                        if not getattr(join_result, 'success', False):
                            return cast(
                                IntegrationResult[str],
                                IntegrationResult.error_result(
                                    f"Failed to join output path: {getattr(join_result, 'error', 'Unknown error')}"
                                ),
                            )

                        output_path = join_result.data
                    except Exception as path_err:
                        return cast(
                            IntegrationResult[str],
                            IntegrationResult.error_result(
                                f"Failed to determine output path: {str(path_err)}"
                            ),
                        )
                else:
                    return cast(
                        IntegrationResult[str],
                        IntegrationResult.error_result(
                            "Cannot determine output path, invalid converter configuration"
                        ),
                    )
            elif output_path:
                # Resolve output path if provided
                try:
                    output_path = paths.resolve_project_path(output_path)
                except Exception as e:
                    # If resolution fails, use the original path
                    logger.warning(f"Failed to resolve output path: {str(e)}")
            else:
                return cast(
                    IntegrationResult[str],
                    IntegrationResult.error_result(
                        "Cannot determine output path, converter not initialized"
                    ),
                )

            if self.converter:
                return self.converter.convert_file(html_path, output_path, "markdown")
            else:
                return cast(
                    IntegrationResult[str],
                    IntegrationResult.error_result("Converter not initialized"),
                )
        except Exception as e:
            logger.error(f"Error in HTML to Markdown conversion: {str(e)}")
            return cast(
                IntegrationResult[str],
                IntegrationResult.error_result(
                    f"Error in HTML to Markdown conversion: {str(e)}"
                ),
            )

    def markdown_to_docx(
            self, markdown_path: str, output_path: str | None = None
    ) -> IntegrationResult[str]:
        """
        Convert Markdown to DOCX.

        Args:
            markdown_path: Absolute path to the Markdown file (as a string).
            output_path: Optional absolute path to save the DOCX file (as a string).

        Returns:
            IntegrationResult[str]: Result of the conversion with the output file path.
        """
        if not self._initialized:
            return cast(
                IntegrationResult[str],
                IntegrationResult.error_result("Pandoc integration not initialized"),
            )

        try:
            # Resolve markdown path
            try:
                markdown_path = paths.resolve_project_path(markdown_path)
            except Exception as e:
                # If resolution fails, use the original path
                logger.warning(f"Failed to resolve project path: {str(e)}")

            # Handle output path
            if output_path is None and self.converter and hasattr(self.converter,
                                                                "config"):
                config = getattr(self.converter, "config", None)
                if isinstance(config, PandocConfig):
                    # Extract the basename from the path
                    try:
                        split_result = fs.split_path(markdown_path)
                        if not getattr(split_result, 'success', False):
                            return cast(
                                IntegrationResult[str],
                                IntegrationResult.error_result(
                                    f"Failed to extract filename from path: {getattr(split_result, 'error', 'Unknown error')}"
                                ),
                            )

                        # Get the filename and remove extension
                        filename = split_result.data[-1]
                        stem = os.path.splitext(filename)[0]

                        # Join with output directory
                        join_result = fs.join_path(config.output_dir, f"{stem}.docx")
                        if not getattr(join_result, 'success', False):
                            return cast(
                                IntegrationResult[str],
                                IntegrationResult.error_result(
                                    f"Failed to join output path: {getattr(join_result, 'error', 'Unknown error')}"
                                ),
                            )

                        output_path = join_result.data
                    except Exception as path_err:
                        return cast(
                            IntegrationResult[str],
                            IntegrationResult.error_result(
                                f"Failed to determine output path: {str(path_err)}"
                            ),
                        )
                else:
                    return cast(
                        IntegrationResult[str],
                        IntegrationResult.error_result(
                            "Cannot determine output path, invalid converter configuration"
                        ),
                    )
            elif output_path:
                # Resolve output path if provided
                try:
                    output_path = paths.resolve_project_path(output_path)
                except Exception as e:
                    # If resolution fails, use the original path
                    logger.warning(f"Failed to resolve output path: {str(e)}")
            else:
                return cast(
                    IntegrationResult[str],
                    IntegrationResult.error_result(
                        "Cannot determine output path, converter not initialized"
                    ),
                )

            if self.converter:
                return self.converter.convert_file(markdown_path, output_path, "docx")
            else:
                return cast(
                    IntegrationResult[str],
                    IntegrationResult.error_result("Converter not initialized"),
                )
        except Exception as e:
            logger.error(f"Error in Markdown to DOCX conversion: {str(e)}")
            return cast(
                IntegrationResult[str],
                IntegrationResult.error_result(
                    f"Error in Markdown to DOCX conversion: {str(e)}"
                ),
            )

    def convert_directory(
            self,
            input_dir: str,
            output_format: str,
            output_dir: str | None = None,
            file_pattern: str | None = None,
            recursive: bool = False,
    ) -> IntegrationResult[list[str]]:
        """
        Convert all files in a directory.

        Args:
            input_dir: Absolute path to the directory containing files to convert (as a string).
            output_format: Target format ("markdown" or "docx").
            output_dir: Optional absolute path to the directory in which to save converted files (as a string).
            file_pattern: Optional pattern to match files (e.g., "*.html").
            recursive: Whether to search subdirectories.

        Returns:
            IntegrationResult[list[str]]: Result of the conversion with a list of output file paths.
        """
        if not self._initialized:
            return cast(
                IntegrationResult[list[str]],
                IntegrationResult.error_result("Pandoc integration not initialized"),
            )

        try:
            # Resolve input directory path
            try:
                input_dir = paths.resolve_project_path(input_dir)
            except Exception as e:
                # If resolution fails, use the original path
                logger.warning(f"Failed to resolve project path: {str(e)}")

            # Check if input directory exists
            input_dir_info = fs.get_file_info(input_dir)
            if (
                    not getattr(input_dir_info, 'success', False)
                    or not getattr(input_dir_info, 'exists', False)
                    or not getattr(input_dir_info, 'is_dir', False)
            ):
                return cast(
                    IntegrationResult[list[str]],
                    IntegrationResult.error_result(
                        f"Input directory does not exist or is not a directory: {input_dir}"
                    ),
                )

            # Determine output directory
            if self.converter and hasattr(self.converter, "config"):
                config = getattr(self.converter, "config", None)
                if isinstance(config, PandocConfig):
                    if output_dir:
                        try:
                            output_dir = paths.resolve_project_path(output_dir)
                        except Exception as e:
                            logger.warning(f"Failed to resolve output path: {str(e)}")
                    else:
                        output_dir = config.output_dir
                else:
                    return cast(
                        IntegrationResult[list[str]],
                        IntegrationResult.error_result(
                            "Invalid converter configuration"
                        ),
                    )
            else:
                return cast(
                    IntegrationResult[list[str]],
                    IntegrationResult.error_result("Converter not initialized"),
                )

            # Create output directory if it doesn't exist
            dir_result = fs.create_directory(output_dir, exist_ok=True)
            if not getattr(dir_result, 'success', False):
                return cast(
                    IntegrationResult[list[str]],
                    IntegrationResult.error_result(
                        f"Failed to create output directory: {getattr(dir_result, 'error', 'Unknown error')}"
                    ),
                )

            # Determine conversion parameters based on output format
            params = self._determine_conversion_params(output_format, file_pattern)
            if params is None:
                return cast(
                    IntegrationResult[list[str]],
                    IntegrationResult.error_result(
                        f"Unsupported output format: {output_format}"
                    ),
                )
            source_format, extension_pattern = params

            # Find matching files in the directory
            find_result = fs.find_files(input_dir, extension_pattern, recursive)
            if not getattr(find_result, 'success', False):
                return cast(
                    IntegrationResult[list[str]],
                    IntegrationResult.error_result(
                        f"Failed to find files: {getattr(find_result, 'error', 'Unknown error')}"
                    ),
                )
            if not getattr(find_result, 'files', []):
                return cast(
                    IntegrationResult[list[str]],
                    IntegrationResult.error_result(
                        f"No matching files found in {input_dir}"
                    ),
                )

            # Convert Path objects to strings for downstream compatibility
            file_paths: list[str] = [str(p) for p in getattr(find_result, 'files', [])]

            # Create conversion tasks for each file
            tasks = self._create_conversion_tasks(
                file_paths, source_format, output_format, output_dir
            )
            if not tasks:
                return cast(
                    IntegrationResult[list[str]],
                    IntegrationResult.error_result(
                        "No valid files found for conversion"
                    ),
                )

            # Perform batch conversion
            if self.converter:
                return self.converter.convert_batch(tasks, output_dir)
            else:
                return cast(
                    IntegrationResult[list[str]],
                    IntegrationResult.error_result("Converter not initialized"),
                )
        except Exception as e:
            logger.error(f"Error in directory conversion: {str(e)}")
            return cast(
                IntegrationResult[list[str]],
                IntegrationResult.error_result(
                    f"Error in directory conversion: {str(e)}"
                ),
            )

    def _determine_conversion_params(
            self, output_format: str, file_pattern: str | None
    ) -> tuple[str, str] | None:
        """
        Determine the source format and file extension pattern based on the target output format.

        Args:
            output_format: Desired target format ("markdown" or "docx").
            file_pattern: Optional file pattern override.

        Returns:
            tuple: (source_format, extension_pattern) or None if output_format is unsupported.
        """
        if output_format == "markdown":
            return "html", file_pattern or "*.html"
        elif output_format == "docx":
            return "markdown", file_pattern or "*.md"
        return None

    def _create_conversion_tasks(
            self,
            files: Sequence[str],
            source_format: str,
            output_format: str,
            output_dir: str,
    ) -> list[ConversionTask]:
        """
        Create a list of conversion tasks from the found files.

        Args:
            files: List of file paths found (as strings).
            source_format: Source format (e.g., "html" or "markdown").
            output_format: Target format (e.g., "markdown" or "docx").
            output_dir: Directory to save converted files (as a string).

        Returns:
            list[ConversionTask]: List of conversion tasks.
        """
        tasks: list[ConversionTask] = []

        for file_path in files:
            try:
                # Get file information
                file_info: FileInfo = get_file_info(file_path, source_format)

                # Extract the base filename safely
                split_result = fs.split_path(file_path)
                if not getattr(split_result, 'success', False):
                    logger.warning(
                        f"Failed to split path '{file_path}': {getattr(split_result, 'error', 'Unknown error')}")
                    continue

                # Get the filename and stem
                filename = split_result.data[-1]
                stem = os.path.splitext(filename)[0]

                # Determine output file extension
                extension = ".md" if output_format == "markdown" else ".docx"

                # Create the output file path
                output_file = os.path.join(output_dir, f"{stem}{extension}")

                # Create the conversion task
                task = ConversionTask(
                    source=file_info,
                    target_format=output_format,
                    output_path=output_file,
                )
                tasks.append(task)
            except Exception as e:
                logger.warning(f"Skipping file {file_path}: {str(e)}")

        return tasks

    def is_pandoc_available(self) -> bool:
        """
        Check if pandoc is available.

        Returns:
            bool: True if pandoc is available, False otherwise.
        """
        try:
            # If we already have a cached version, return True
            if self._pandoc_version:
                return True

            # Otherwise, try to verify pandoc
            verify_pandoc()
            return True
        except (QuackIntegrationError, ImportError, OSError):
            return False

    def get_pandoc_version(self) -> str | None:
        """
        Get the pandoc version.

        Returns:
            str | None: Pandoc version string or None if not available.
        """
        if self._pandoc_version:
            return self._pandoc_version

        try:
            self._pandoc_version = verify_pandoc()
            return self._pandoc_version
        except (QuackIntegrationError, ImportError, OSError):
            return None

    def get_metrics(self) -> ConversionMetrics:
        """
        Get conversion metrics.

        Returns:
            ConversionMetrics: Current conversion metrics.
        """
        if self.converter and hasattr(self.converter, "metrics"):
            return getattr(self.converter, "metrics", self.metrics)
        return self.metrics
