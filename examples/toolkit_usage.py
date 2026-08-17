"""
Example usage of the zeo_core.tools capability-authoring framework
(Ring B, Doctrine v3).

This example demonstrates how to build a custom, doctrine-compliant tool:

1. A tool subclassing BaseZeoTool that implements run(request, ctx).
2. JSON transform + statistics business logic (process_content /
   _calculate_statistics -- plain Python, no framework coupling).
3. Optional Google Drive integration via IntegrationEnabledMixin, reading
   the service out of ctx.services (runner-provided) rather than resolving
   it itself.
4. Pre/post-run hooks via LifecycleMixin.
5. A runnable main() that stands in for what a real runner (Ring C) would
   do: build a ToolContext, construct a request, call tool.run(), and
   persist the CapabilityResult's data.

NOTE ON TOOL VS. RUNNER RESPONSIBILITIES:
Doctrine v3 has no OutputFormatMixin (see
zeo_core.tools.mixins.output_handler's own module docstring) -- output
persistence is the exclusive responsibility of the runner (Ring C), not the
tool. This example's tool therefore never picks an output format or writes
files itself; instead run() returns structured data inside CapabilityResult,
and main() (playing the runner's role) is the one that decides to serialize
it to disk.

Run this file directly to see it work end to end against a small, real
JSON fixture:

    python examples/toolkit_usage.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from zeo_core.config.tooling.logger import get_logger
from zeo_core.contracts import CapabilityResult
from zeo_core.core.fs import get_service as get_fs_service
from zeo_core.integrations.google.drive import GoogleDriveService
from zeo_core.tools import (
    BaseZeoTool,
    IntegrationEnabledMixin,
    LifecycleMixin,
    ToolContext,
)


class ExampleToolRequest(BaseModel):
    """
    Request model for ExampleTool.run().

    Args:
        input_path: Path to a JSON file to read and process.
        calculate_stats: Whether to compute statistics over the data.
        upload_to_drive: Whether to attempt a Google Drive upload of the
            processed result (requires a "google_drive" service in
            ctx.services; silently skipped, not an error, if absent).
        drive_folder_id: Optional destination folder ID for the upload.
    """

    input_path: str
    calculate_stats: bool = True
    upload_to_drive: bool = False
    drive_folder_id: str | None = None


class ExampleToolResponse(BaseModel):
    """Response payload carried inside CapabilityResult.data."""

    processed: dict[str, Any]
    uploaded_file_id: str | None = None


class ExampleTool(IntegrationEnabledMixin, LifecycleMixin, BaseZeoTool):
    """
    Example doctrine-compliant tool.

    This tool:
    1. Reads a JSON file (path supplied via the request).
    2. Transforms the data by attaching identity metadata and, optionally,
       computed statistics.
    3. Optionally uploads the transformed result to Google Drive, if a
       "google_drive" service was provided by the runner in
       ctx.services and the request asks for it.

    Demonstrates IntegrationEnabledMixin (service lookup from ctx.services)
    and LifecycleMixin (pre_run/post_run hooks) alongside BaseZeoTool's
    required run(request, ctx) contract.
    """

    name = "example_tool"
    version = "1.0.0"

    def pre_run(
        self, request: ExampleToolRequest, ctx: ToolContext
    ) -> CapabilityResult[None]:
        """Log intent before running. Validation stays in run()/is_available()."""
        logger = ctx.require_logger()
        if logger is not None:
            logger.info(f"[{self.name}] pre-run: about to process {request.input_path}")
        return CapabilityResult.ok(data=None, msg="Pre-run checks passed")

    def post_run(
        self,
        request: ExampleToolRequest,
        result: CapabilityResult[Any],
        ctx: ToolContext,
    ) -> CapabilityResult[Any]:
        """Log outcome after running. Passes the result through unchanged."""
        logger = ctx.require_logger()
        if logger is not None:
            logger.info(f"[{self.name}] post-run: status={result.status}")
        return result

    def run(
        self, request: ExampleToolRequest, ctx: ToolContext
    ) -> CapabilityResult[ExampleToolResponse]:
        """
        Execute the example capability: read, transform, optionally upload.

        Args:
            request: Typed request naming the input file and options.
            ctx: Runner-provided, immutable tool context.

        Returns:
            CapabilityResult wrapping an ExampleToolResponse.
        """
        logger = ctx.require_logger()

        try:
            raw = Path(request.input_path).read_text(encoding="utf-8")
        except OSError as e:
            return CapabilityResult.fail_from_exc(
                msg=f"Could not read input file: {request.input_path}",
                code="QC_IO_NOT_FOUND",
                exc=e,
            )

        try:
            content = json.loads(raw)
        except json.JSONDecodeError as e:
            return CapabilityResult.fail_from_exc(
                msg=f"Input file is not valid JSON: {request.input_path}",
                code="QC_VAL_INVALID_JSON",
                exc=e,
            )

        processed = self.process_content(
            content, {"calculate_stats": request.calculate_stats}
        )

        uploaded_file_id: str | None = None
        if request.upload_to_drive:
            drive = self.get_service(
                "google_drive", ctx, expected_type=GoogleDriveService
            )
            if drive is None:
                if logger is not None:
                    logger.info(
                        f"[{self.name}] Google Drive upload requested but no "
                        "'google_drive' service was provided in ctx.services "
                        "-- skipping upload, not treated as an error."
                    )
            else:
                upload_result = self._upload_processed(
                    drive, processed, request.drive_folder_id, ctx
                )
                if upload_result.success:
                    uploaded_file_id = upload_result.content
                elif logger is not None:
                    logger.warning(
                        f"[{self.name}] Google Drive upload failed: "
                        f"{upload_result.error}"
                    )

        return CapabilityResult.ok(
            data=ExampleToolResponse(
                processed=processed, uploaded_file_id=uploaded_file_id
            ),
            msg="Processing completed",
            metadata={"tool": f"{self.name} v{self.version}"},
        )

    def process_content(
        self,
        content: Any,  # noqa: ANN401 -- genuinely dynamic: raw loaded content, may be a JSON string or already-parsed JSON (dict/list/scalar)
        options: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Process content with this tool.

        Takes the content of a JSON file and transforms it by adding a
        "processed_by" field and, optionally, calculated statistics.

        Args:
            content: The loaded content to process (JSON data).
            options: Dictionary of processing options.

        Returns:
            The processed content.
        """
        # If content is a string (raw JSON), parse it
        if isinstance(content, str):
            content = json.loads(content)

        result: dict[str, Any] = {
            "processed_by": f"{self.name} v{self.version}",
            "original_data": content,
        }

        if options.get("calculate_stats", False) and isinstance(content, dict):
            result["statistics"] = self._calculate_statistics(content)

        return result

    def _calculate_statistics(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate statistics from the data.

        Computes:
        - Number of keys in the data
        - Types of values
        - Depth of the data structure

        Args:
            data: The data to analyze.

        Returns:
            The calculated statistics.
        """
        num_keys = len(data)

        value_types: dict[str, int] = {}
        for value in data.values():
            value_type = type(value).__name__
            value_types[value_type] = value_types.get(value_type, 0) + 1

        def get_depth(d: Any, level: int = 1) -> int:  # noqa: ANN401 -- genuinely dynamic: recurses into arbitrary JSON-shaped values (dict/list/scalar), same data domain as content above
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

    def _upload_processed(
        self,
        drive: GoogleDriveService,
        processed: dict[str, Any],
        folder_id: str | None,
        ctx: ToolContext,
    ) -> Any:  # noqa: ANN401 -- returns GoogleDriveService.upload_file's own IntegrationResult[str]; not re-exported through this module's typed surface
        """
        Write the processed result to a temp file and upload it to Drive.

        Args:
            drive: Resolved Google Drive integration service.
            processed: The processed content to upload.
            folder_id: Optional destination folder ID.
            ctx: Tool context (used for the work directory).

        Returns:
            IntegrationResult from GoogleDriveService.upload_file.
        """
        upload_path = Path(ctx.work_dir) / f"{self.name}_output.json"
        upload_path.write_text(json.dumps(processed, indent=2), encoding="utf-8")
        return drive.upload_file(
            file_path=str(upload_path),
            parent_folder_id=folder_id,
        )


def main() -> None:
    """
    Example of using ExampleTool end to end.

    Plays the role a real runner (Ring C) would play: builds a ToolContext,
    constructs a request, invokes the tool's lifecycle (pre_run -> run ->
    post_run), and persists the result -- none of which the tool itself is
    responsible for under Doctrine v3.
    """
    with tempfile.TemporaryDirectory(prefix="zeo_toolkit_usage_") as tmp:
        tmp_dir = Path(tmp)
        work_dir = tmp_dir / "work"
        output_dir = tmp_dir / "output"
        work_dir.mkdir()
        output_dir.mkdir()

        # Write a small, realistic input fixture.
        input_path = tmp_dir / "example_data.json"
        input_path.write_text(
            json.dumps(
                {
                    "project": "zeocore",
                    "version": 3,
                    "tags": ["doctrine", "example"],
                    "nested": {"enabled": True},
                }
            ),
            encoding="utf-8",
        )

        logger = get_logger("example_tool")
        fs = get_fs_service()

        ctx = ToolContext(
            run_id="example-run-001",
            tool_name="example_tool",
            tool_version="1.0.0",
            logger=logger,
            fs=fs,
            work_dir=str(work_dir),
            output_dir=str(output_dir),
            # No "google_drive" entry: demonstrates the graceful-skip path.
            # A real runner wires ctx.services={"google_drive": GoogleDriveService(...)}
            # once the integration is configured.
            services={},
        )

        tool = ExampleTool()

        init_result = tool.initialize(ctx)
        if init_result.status != "success":
            print(f"Failed to initialize tool: {init_result.human_message}")
            return
        print(f"Tool initialized: {init_result.human_message}")

        request = ExampleToolRequest(
            input_path=str(input_path),
            calculate_stats=True,
            upload_to_drive=True,  # will gracefully skip: no drive service wired
        )

        pre_result = tool.pre_run(request, ctx)
        if pre_result.status != "success":
            print(f"Pre-run failed: {pre_result.human_message}")
            return

        run_result = tool.run(request, ctx)
        run_result = tool.post_run(request, run_result, ctx)

        if run_result.status != "success":
            print(f"Failed to process file: {run_result.human_message}")
            return

        assert run_result.data is not None  # noqa: S101 -- narrows Optional for the demo print below; status==success guarantees data is populated per run()'s own contract
        print(f"File processed: {run_result.human_message}")
        print(f"Uploaded file id: {run_result.data.uploaded_file_id!r}")

        # The runner's job, not the tool's: persist the result.
        output_file = output_dir / "example_data.processed.json"
        output_file.write_text(
            json.dumps(run_result.data.processed, indent=2), encoding="utf-8"
        )
        print(f"Output written to: {output_file}")


if __name__ == "__main__":
    main()
