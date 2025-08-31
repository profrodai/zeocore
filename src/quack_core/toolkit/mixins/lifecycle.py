# quack-core/src/quack-core/toolkit/mixins/lifecycle.py
"""
Lifecycle mixin for QuackTool plugins.

This module provides a mixin that adds lifecycle methods to QuackTool plugins,
such as run, validate, upload, pre_run, and post_run.
"""

from typing import Any

from quack_core.integrations.core import IntegrationResult


class QuackToolLifecycleMixin:
    """
    Mixin that provides lifecycle methods for QuackTool plugins.

    This mixin adds optional lifecycle methods such as run, validate, upload,
    pre_run, and post_run to QuackTool plugins. These methods can be overridden
    by concrete plugin classes to provide custom behavior.
    """

    def pre_run(self) -> IntegrationResult:
        """
        Prepare before running the tool.

        This method is called before the tool is run. Override this method
        to perform any preparation tasks such as checking prerequisites.

        Returns:
            IntegrationResult: Result of the preparation process
        """
        return IntegrationResult.success_result(
            message="Pre-run completed successfully"
        )

    def post_run(self) -> IntegrationResult:
        """
        Clean up or finalize after running the tool.

        This method is called after the tool is run. Override this method
        to perform any clean-up or finalization tasks.

        Returns:
            IntegrationResult: Result of the finalization process
        """
        return IntegrationResult.success_result(
            message="Post-run completed successfully"
        )

    def run(self, options: dict[str, Any] | None = None) -> IntegrationResult:
        """
        Run the tool with the given options.

        This method is a high-level runner that executes the full logic of the tool.
        Override this method to provide custom run behavior.

        Args:
            options: Optional dictionary of options for the run

        Returns:
            IntegrationResult: Result of the run
        """
        return IntegrationResult.success_result(
            message="Run method not implemented"
        )

    def validate(self, input_path: str | None = None,
                 output_path: str | None = None) -> IntegrationResult:
        """
        Validate input and/or output files.

        This method validates the input and/or output files for correctness.
        Override this method to provide custom validation logic.

        Args:
            input_path: Optional path to the input file to validate
            output_path: Optional path to the output file to validate

        Returns:
            IntegrationResult: Result of the validation
        """
        return IntegrationResult.success_result(
            message="Validation method not implemented"
        )

    def upload(self, file_path: str,
               destination: str | None = None) -> IntegrationResult:
        """
        Upload a file to a destination.

        This method uploads a file to a destination such as a remote service.
        Override this method to provide custom upload logic.

        Args:
            file_path: Path to the file to upload
            destination: Optional destination path or identifier

        Returns:
            IntegrationResult: Result of the upload
        """
        return IntegrationResult.success_result(
            message="Upload method not implemented"
        )
