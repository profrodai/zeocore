# === QV-LLM:BEGIN ===
# path: quack-core/examples/toolkit_usage.py
# role: module
# neighbors: config_tooling_test.py, explicit_plugin_loading_example.py, http_adapter_usage.py
# exports: ExampleTool, main
# git_branch: refactor/toolkitWorkflow
# git_commit: 66ff061
# === QV-LLM:END ===

"""
Example usage of the QuackCore capabilities.

This example demonstrates how to create a custom QuackTool plugin
using the QuackCore capabilities.
"""

import json
from typing import Any

from quack_core.integrations.core import IntegrationResult
# Import the specific Google Drive service
# Note: This is just for the example, in a real implementation you'd
# use the actual import path for GoogleDriveService
from quack_core.integrations.google.drive import GoogleDriveService
from quack_core.capabilities import (
    BaseQuackToolPlugin,
    IntegrationEnabledMixin,
    OutputFormatMixin,
    QuackToolLifecycleMixin,
)
from quack_core.workflow.output import YAMLOutputWriter


class ExampleTool(
    IntegrationEnabledMixin[GoogleDriveService],
    OutputFormatMixin,
    QuackToolLifecycleMixin,
    BaseQuackToolPlugin,
):
    """
    Example QuackTool plugin that demonstrates the QuackCore capabilities.

    This tool:
    1. Reads a JSON file
    2. Transforms the data in a simple way
    3. Outputs the result as YAML
    4. Optionally uploads to Google Drive if integration is available
    """

    def __init__(self):
        """
        Initialize the ExampleTool.
        """
        super().__init__("example_tool", "1.0.0")

    def initialize_plugin(self):
        """
        Initialize plugin-specific resources and dependencies.
        """
        # Resolve the Google Drive integration service
        self._drive_service = self.resolve_integration(GoogleDriveService)

        if self._drive_service:
            self.logger.info("Google Drive integration is available")
        else:
            self.logger.info("Google Drive integration is not available")

    def _get_output_extension(self) -> str:
        """
        Get the file extension for output files.

        Returns:
            str: File extension (with leading dot) for output files
        """
        return ".yaml"

    def get_output_writer(self) -> YAMLOutputWriter:
        """
        Get the output writer for this tool.

        Returns:
            YAMLOutputWriter: A YAML output writer
        """
        return YAMLOutputWriter()

    def process_content(self, content: Any, options: dict[str, Any]) -> dict[str, Any]:
        """
        Process content with this tool.

        This method takes the content of a JSON file and transforms it
        by adding a "processed_by" field and calculating statistics.

        Args:
            content: The loaded content to process (JSON data)
            options: Dictionary of processing options

        Returns:
            dict[str, Any]: The processed content
        """
        self.logger.info(f"Processing content with options: {options}")

        # If content is a string (raw JSON), parse it
        if isinstance(content, str):
            content = json.loads(content)

        # Add processing metadata
        result = {
            "processed_by": f"{self.name} v{self.version}",
            "original_data": content,
        }

        # Add statistics if requested
        if options.get("calculate_stats", False):
            stats = self._calculate_statistics(content)
            result["statistics"] = stats

        return result

    def _calculate_statistics(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate statistics from the data.

        This is a simple example that calculates:
        - Number of keys in the data
        - Types of values
        - Depth of the data structure

        Args:
            data: The data to analyze

        Returns:
            dict[str, Any]: The calculated statistics
        """
        # Count keys
        num_keys = len(data)

        # Count value types
        value_types = {}
        for value in data.values():
            value_type = type(value).__name__
            value_types[value_type] = value_types.get(value_type, 0) + 1

        # Calculate depth
        def get_depth(d, level=1):
            if not isinstance(d, dict):
                return level
            if not d:
                return level
            return max(get_depth(v, level + 1) for v in d.values())

        depth = get_depth(data)

        return {
            "num_keys": num_keys,
            "value_types": value_types,
            "depth": depth,
        }

    def pre_run(self) -> IntegrationResult:
        """
        Prepare before running the tool.

        Returns:
            IntegrationResult: Result of the preparation process
        """
        self.logger.info("Running pre-run checks...")
        return IntegrationResult.success_result(
            message="Pre-run checks completed successfully"
        )

    def post_run(self) -> IntegrationResult:
        """
        Clean up after running the tool.

        Returns:
            IntegrationResult: Result of the cleanup process
        """
        self.logger.info("Running post-run cleanup...")
        return IntegrationResult.success_result(
            message="Post-run cleanup completed successfully"
        )

    def upload(self, file_path: str, destination: str | None = None) -> IntegrationResult:
        """
        Upload a file to Google Drive.

        Args:
            file_path: Path to the file to upload
            destination: Optional folder ID in Google Drive

        Returns:
            IntegrationResult: Result of the upload operation
        """
        if not self._drive_service:
            return IntegrationResult.error_result(
                error="Google Drive integration not available",
                message="Cannot upload file without Google Drive integration"
            )

        try:
            self.logger.info(f"Uploading {file_path} to Google Drive...")

            # Use the drive service to upload the file
            upload_result = self._drive_service.upload_file(
                file_path=file_path,
                folder_id=destination,
            )

            if upload_result.success:
                return IntegrationResult.success_result(
                    content=upload_result.content,
                    message="File uploaded successfully to Google Drive"
                )
            else:
                return IntegrationResult.error_result(
                    error=upload_result.error,
                    message="Failed to upload file to Google Drive"
                )
        except Exception as e:
            self.logger.exception("Error uploading file to Google Drive")
            return IntegrationResult.error_result(
                error=str(e),
                message="Error uploading file to Google Drive"
            )


def main():
    """
    Example of using the ExampleTool.
    """
    # Create an instance of the tool
    tool = ExampleTool()

    # Initialize the tool
    init_result = tool.initialize()
    if not init_result.success:
        print(f"Failed to initialize tool: {init_result.error}")
        return

    print(f"Tool initialized: {init_result.message}")

    # Process a file
    process_result = tool.process_file(
        "example_data.json",
        options={"calculate_stats": True}
    )

    if not process_result.success:
        print(f"Failed to process file: {process_result.error}")
        return

    print(f"File processed: {process_result.message}")
    print(f"Output file: {process_result.content.output_file}")

    # Optionally upload the result
    if tool.integration:
        upload_result = tool.upload(
            process_result.content.output_file,
            destination="my_folder_id"
        )

        if upload_result.success:
            print(f"File uploaded: {upload_result.message}")
        else:
            print(f"Failed to upload file: {upload_result.error}")


if __name__ == "__main__":
    main()