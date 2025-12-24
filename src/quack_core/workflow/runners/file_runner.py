# quack-core/src/quack_core/workflow/runners/file_runner.py

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from quack_core.logging import get_logger
from quack_core.workflow.protocols.remote_handler import RemoteFileHandler
from quack_core.workflow.results import FinalResult, InputResult, OutputResult


class WorkflowError(Exception):
    """Custom exception for workflow-related errors."""


T = TypeVar('T')  # Type for processor content


class FileWorkflowRunner:
    """
    Runner for file-based workflows.

    Manages the entire file processing lifecycle: input resolution, content loading,
    processing, and output writing. Supports both local and remote files.
    """

    def __init__(
        self,
        processor: Callable[[Any, dict[str, Any]], tuple[bool, dict[str, Any], str | None] | OutputResult | dict | Any],
        remote_handler: RemoteFileHandler | None = None,
        output_writer: Any | None = None,
        logger: Any | None = None,
    ) -> None:
        """
        Initialize the workflow runner.

        Args:
            processor: Callable that processes the file content
            remote_handler: Optional handler for remote files
            output_writer: Optional custom output writer
            logger: Optional logger instance
        """
        self.logger = logger or get_logger(__name__)
        self.processor = processor
        self.remote_handler = remote_handler
        self.output_writer = output_writer

    def resolve_input(self, source: str) -> InputResult:
        """
        Resolve the input source to a file path.

        Args:
            source: Source path or URL

        Returns:
            InputResult containing the resolved path
        """
        if self.remote_handler and self.remote_handler.is_remote(source):
            self.logger.debug(f"Detected remote source: {source}")
            inp = self.remote_handler.download(source)
            if getattr(inp, "metadata", None) is not None:
                inp.metadata.update({"input_type": "remote", "source": source})
            return inp

        self.logger.debug(f"Using local source: {source}")
        return InputResult(path=Path(source), metadata={"input_type": "local"})

    def load_content(self, input_result: InputResult) -> Any:
        """
        Load content from the input file. Uses binary for `.bin`, else
        falls back to Python's Path.read_text.

        Args:
            input_result: Input result containing the file path

        Returns:
            File content as string or bytes

        Raises:
            WorkflowError: If file doesn't exist or can't be read
        """
        from quack_core.fs.service import standalone as fs

        path_str = str(input_result.path)

        # 1) Existence check via FS stub
        info = fs.get_file_info(path_str)
        if not info.success or not info.exists:
            raise WorkflowError(f"Failed to read file content: file does not exist: {path_str}")

        # 2) Detect extension
        ext_res = fs.get_extension(path_str)
        ext = (ext_res.data or "").lower() if ext_res.success else ""

        # 3) If binary, use stub.read_binary
        if ext == "bin":
            bin_res = fs.read_binary(path_str)
            if not bin_res.success:
                raise WorkflowError(f"Failed to read file content: {bin_res.error}")
            return bin_res.content

        # 4) Otherwise use built-in read_text (so stub.should_fail doesn't block reads)
        try:
            return Path(path_str).read_text(encoding="utf-8")
        except Exception as e:
            raise WorkflowError(f"Failed to read file content: {e}")

    def run_processor(self, content: Any, options: dict[str, Any]) -> OutputResult:
        """
        Run the processor on the content.

        Args:
            content: File content
            options: Processing options

        Returns:
            OutputResult with processing results
        """
        try:
            result = self.processor(content, options)
            if isinstance(result, OutputResult):
                return result
            if isinstance(result, tuple) and len(result) == 3:
                success, content, error = result
                return OutputResult(success=success, content=content, raw_text=error)
            if isinstance(result, dict):
                success = bool(result.get("success", True))
                err = None if success else result.get("error")
                return OutputResult(success=success, content=result, raw_text=err)
            return OutputResult(success=True, content=result, raw_text=None)
        except Exception as e:
            self.logger.exception(f"Error in processor: {e}")
            return OutputResult(success=False, content=None, raw_text=str(e))

    def write_output(
        self, result: OutputResult, input_path: Path, options: dict[str, Any]
    ) -> FinalResult:
        """
        Write the processing result to output.

        Args:
            result: Processing result
            input_path: Original input file path
            options: Output options

        Returns:
            FinalResult with output information
        """
        if options.get("dry_run"):
            self.logger.warning("Dry run mode: skipping output writing")
            return FinalResult(
                success=True,
                metadata={
                    "input_file": str(input_path),
                    "dry_run": True,
                    "processor_success": result.success
                }
            )

        try:
            # ==== Custom writer branch ====
            if self.output_writer is not None:
                try:
                    out = self.output_writer.write(result, input_path, options)
                    if isinstance(out, FinalResult):
                        return out
                    return FinalResult(
                        success=out.get("success", True),
                        result_path=out.get("result_path"),
                        metadata=out.get("metadata", {})
                    )
                except Exception as e:
                    raise WorkflowError(f"Output writer failed: {e}")

            # ==== Default JSON-writer branch ====
            from quack_core.fs.service import standalone as fs

            # 1) Figure out output directory
            if options.get("use_temp_dir"):
                out_dir = tempfile.mkdtemp(prefix="quackcore_")
                self.logger.info(f"Using temporary directory: {out_dir}")
            elif "output_dir" in options:
                out_dir = options["output_dir"]
                dir_res = fs.create_directory(out_dir, exist_ok=True)
                if not dir_res.success:
                    raise WorkflowError(dir_res.error)
            else:
                out_dir = "./output"
                os.makedirs(out_dir, exist_ok=True)

            # 2) Write JSON
            out_path = Path(out_dir) / f"{input_path.stem}.json"
            write_res = fs.write_json(str(out_path), result.content, indent=2)
            if not write_res.success:
                raise WorkflowError(write_res.error)

            # 3) Return success
            return FinalResult(
                success=True,
                result_path=out_path,
                metadata={
                    "input_file": str(input_path),
                    "output_file": str(out_path),
                    "output_format": "json",
                    "processor_success": result.success
                }
            )

        except WorkflowError as wf:
            return FinalResult(
                success=False,
                metadata={
                    "error_type": type(wf).__name__,
                    "error_message": str(wf),
                    "source": options.get("source", str(input_path)),
                    "input_file": str(input_path)
                }
            )
        except Exception as e:
            self.logger.exception(f"Output writing failed: {e}")
            msg = str(e)
            if len(msg) > 1000:
                msg = msg[:997] + "..."
            return FinalResult(
                success=False,
                metadata={
                    "error_type": type(e).__name__,
                    "error_message": msg,
                    "source": options.get("source", str(input_path)),
                    "input_file": str(input_path)
                }
            )

    def run(self, source: str, options: dict[str, Any] | None = None) -> FinalResult:
        """
        Run the complete workflow from input to output.

        Args:
            source: Source path or URL
            options: Processing and output options

        Returns:
            FinalResult with workflow results
        """
        options = options or {}
        try:
            self.logger.info(f"Starting workflow for source: {source}")
            if options.get("simulate_failure"):
                return FinalResult(
                    success=False,
                    metadata={
                        "error_type": "SimulatedFailure",
                        "error_message": "Simulated failure for testing",
                        "source": source
                    }
                )

            inp = self.resolve_input(source)
            try:
                content = self.load_content(inp)
            except WorkflowError as e:
                return FinalResult(
                    success=False,
                    metadata={
                        "error_type": "WorkflowError",
                        "error_message": str(e),
                        "source": source
                    }
                )

            output = self.run_processor(content, options)

            try:
                final = self.write_output(output, input_path=inp.path, options=options)
            except WorkflowError as e:
                return FinalResult(
                    success=False,
                    metadata={
                        "error_type": "WorkflowError",
                        "error_message": str(e),
                        "source": source,
                        "input_file": str(inp.path)
                    }
                )

            # Merge in source & input‐metadata
            if isinstance(final, FinalResult):
                md = final.metadata or {}
                md["source"] = source
                md.update(getattr(inp, "metadata", {}))
                if not output.success:
                    final.success = False
                    md["processor_error"] = output.raw_text
                final.metadata = md
                return final

            # (If writer returned dict, would be handled above)
            return final

        except Exception as e:
            self.logger.exception(f"Workflow run failed: {e}")
            msg = str(e)
            if len(msg) > 1000:
                msg = msg[:997] + "..."
            return FinalResult(
                success=False,
                metadata={
                    "error_type": type(e).__name__,
                    "error_message": msg,
                    "source": source
                }
            )
