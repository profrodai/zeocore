# === QV-LLM:BEGIN ===
# path: quack-runner/src/quack_runner/workflow/tool_runner.py
# module: quack_runner.workflow.tool_runner
# role: module
# neighbors: __init__.py, results.py, legacy.py
# exports: ToolRunner
# git_branch: feat/9-make-setup-work
# git_commit: ffd13f1b
# === QV-LLM:END ===


"""
Tool runner for executing QuackTools with file I/O.

IMPORTANT (Must-fix C): Tools must be fully initialized before use.
ToolRunner requires tool.name to be set (non-None).
"""

from pathlib import Path
from typing import Any, TYPE_CHECKING, Callable
from datetime import datetime
import tempfile
import shutil

from quack_core.contracts import (
    CapabilityResult,
    CapabilityStatus,
    RunManifest,
    ToolInfo,
    ManifestInput,
    ArtifactRef,
    ArtifactKind,
    StorageRef,
    StorageScheme,
    generate_run_id,
    utcnow,
    CapabilityError,
)
from quack_core.tools import ToolContext
from quack_core.core.logging import get_logger
from quack_core.core.fs.service import standalone as fs
from quack_core.core.serialization import normalize_for_json
from quack_core.core.mime import is_binary_extension, get_content_type

if TYPE_CHECKING:
    from quack_core.tools import BaseQuackTool


class ToolRunner:
    """
    Runner for executing tools with file I/O and manifest generation.

    REQUIREMENTS (Must-fix C):
    - Tool MUST be fully initialized (tool.name and tool.version set)
    - Tool MUST have non-None name attribute
    - Tool SHOULD inherit from BaseQuackTool (but duck-typed tools work if compliant)

    The runner will raise TypeError if tool.name is None.
    """

    def __init__(
            self,
            tool: "BaseQuackTool",
            logger: Any | None = None,
            cleanup_work_dir: bool = True
    ):
        """
        Initialize the tool runner.

        Args:
            tool: Fully initialized tool instance (name must be non-None)
            logger: Optional logger
            cleanup_work_dir: Whether to cleanup temporary work directories

        Raises:
            TypeError: If tool.name is None or not set
        """
        # Must-fix #1: Validate tool.name early
        tool_name = getattr(tool, "name", None)
        if not tool_name:
            raise TypeError(
                f"ToolRunner requires tool.name to be set (non-None). "
                f"Got tool of type {type(tool).__name__} with name={tool_name!r}. "
                f"Ensure tool is fully initialized before passing to ToolRunner."
            )

        self.tool = tool
        self.logger = logger or get_logger(f"runner.{tool.name}")  # Now safe
        self.cleanup_work_dir = cleanup_work_dir

        self._has_validate = hasattr(tool, 'validate') and callable(
            getattr(tool, 'validate'))
        self._has_pre_run = hasattr(tool, 'pre_run') and callable(
            getattr(tool, 'pre_run'))
        self._has_post_run = hasattr(tool, 'post_run') and callable(
            getattr(tool, 'post_run'))
        self._has_cleanup = hasattr(tool, 'cleanup') and callable(
            getattr(tool, 'cleanup'))

    def build_context(
            self,
            run_id: str,
            work_dir: str,
            output_dir: str,
            services: dict[str, Any] | None = None,
            metadata: dict[str, Any] | None = None
    ) -> ToolContext:
        """Build a ToolContext for tool execution."""
        return ToolContext(
            run_id=run_id,
            tool_name=self.tool.name,  # Safe - validated in __init__
            tool_version=self.tool.version,
            logger=self.logger,
            fs=fs,
            work_dir=work_dir,
            output_dir=output_dir,
            services=services or {},
            metadata=metadata or {}
        )

    def run_on_file(
            self,
            input_path: str | Path,
            request_builder: Callable[[str | bytes], Any],
            output_dir: str | Path | None = None,
            work_dir: str | Path | None = None,
            services: dict[str, Any] | None = None,
            metadata: dict[str, Any] | None = None
    ) -> RunManifest:
        """Run tool on a file input."""
        input_path = Path(input_path)

        created_temp_dir = False
        temp_dir_path: Path | None = None

        if output_dir is None:
            output_dir = Path("./output")
        else:
            output_dir = Path(output_dir)

        mkdir_result = fs.create_directory(str(output_dir), exist_ok=True)
        if not mkdir_result.success:
            started_at = utcnow()
            return self._build_error_manifest(
                ctx=None,
                input_path=input_path,
                started_at=started_at,
                error_msg=f"Failed to create output directory: {mkdir_result.error}",
                error_code="QC_IO_MKDIR_ERROR"
            )

        # Safe - tool.name validated in __init__
        safe_tool_name = self.tool.name.replace('.', '_').replace('/', '_')
        if work_dir is None:
            temp_dir_path = Path(tempfile.mkdtemp(prefix=f"quack_{safe_tool_name}_"))
            work_dir = temp_dir_path
            created_temp_dir = True
        else:
            work_dir = Path(work_dir)
            mkdir_result = fs.create_directory(str(work_dir), exist_ok=True)
            if not mkdir_result.success:
                started_at = utcnow()
                return self._build_error_manifest(
                    ctx=None,
                    input_path=input_path,
                    started_at=started_at,
                    error_msg=f"Failed to create work directory: {mkdir_result.error}",
                    error_code="QC_IO_MKDIR_ERROR"
                )

        run_id = generate_run_id()
        ctx = self.build_context(
            run_id=run_id,
            work_dir=str(work_dir),
            output_dir=str(output_dir),
            services=services,
            metadata=metadata
        )

        started_at = utcnow()

        try:
            init_result = self.tool.initialize(ctx)
            if init_result.status != CapabilityStatus.success:
                return self._build_error_manifest(
                    ctx=ctx,
                    input_path=input_path,
                    started_at=started_at,
                    error_msg=init_result.human_message,
                    error_code=init_result.machine_message or "QC_TOOL_INIT_ERROR"
                )

            file_info_result = fs.get_file_info(str(input_path))
            if not file_info_result.success:
                return self._build_error_manifest(
                    ctx=ctx,
                    input_path=input_path,
                    started_at=started_at,
                    error_msg=f"Failed to check file: {file_info_result.error}",
                    error_code="QC_IO_CHECK_ERROR"
                )

            file_info = file_info_result.data
            if not file_info or not file_info.exists:
                return self._build_error_manifest(
                    ctx=ctx,
                    input_path=input_path,
                    started_at=started_at,
                    error_msg=f"Input file not found: {input_path}",
                    error_code="QC_IO_NOT_FOUND"
                )

            ext_result = fs.get_extension(str(input_path))
            extension = (ext_result.data or "").lower().lstrip(".")

            is_binary = is_binary_extension(extension)

            content: str | bytes
            content_type: str

            if is_binary:
                read_result = fs.read_binary(str(input_path))
                if not read_result.success:
                    return self._build_error_manifest(
                        ctx=ctx,
                        input_path=input_path,
                        started_at=started_at,
                        error_msg=f"Failed to read binary file: {read_result.error}",
                        error_code="QC_IO_READ_ERROR"
                    )
                content = read_result.content
                content_type = get_content_type(extension)
            else:
                read_result = fs.read_text(str(input_path))
                if not read_result.success:
                    return self._build_error_manifest(
                        ctx=ctx,
                        input_path=input_path,
                        started_at=started_at,
                        error_msg=f"Failed to read text file: {read_result.error}",
                        error_code="QC_IO_READ_ERROR"
                    )
                content = read_result.content
                content_type = get_content_type(
                    extension) if extension else "text/plain"

            try:
                request = request_builder(content)
            except Exception as e:
                return self._build_error_manifest(
                    ctx=ctx,
                    input_path=input_path,
                    started_at=started_at,
                    error_msg=f"Failed to build request: {e}",
                    error_code="QC_VAL_INVALID"
                )

            input_artifact = ArtifactRef(
                role=f"{self.tool.name}.input",
                kind=ArtifactKind.intermediate,
                content_type=content_type,
                storage=StorageRef(
                    scheme=StorageScheme.local,
                    uri=f"file://{input_path.absolute()}"
                )
            )

            if self._has_validate:
                validate_result = self.tool.validate(request, ctx)  # type: ignore
                if validate_result.status != CapabilityStatus.success:
                    return self._build_error_manifest(
                        ctx=ctx,
                        input_path=input_path,
                        started_at=started_at,
                        error_msg=validate_result.human_message or "Validation failed",
                        error_code=validate_result.machine_message or "QC_VAL_FAILED",
                        input_artifact=input_artifact
                    )

            if self._has_pre_run:
                pre_result = self.tool.pre_run(request, ctx)  # type: ignore
                if pre_result.status != CapabilityStatus.success:
                    return self._build_error_manifest(
                        ctx=ctx,
                        input_path=input_path,
                        started_at=started_at,
                        error_msg=pre_result.human_message or "Pre-run failed",
                        error_code=pre_result.machine_message or "QC_PRE_RUN_FAILED",
                        input_artifact=input_artifact
                    )

            result = self.tool.run(request, ctx)

            if self._has_post_run:
                result = self.tool.post_run(request, result, ctx)  # type: ignore

            finished_at = utcnow()
            duration_sec = (finished_at - started_at).total_seconds()

            return self._build_manifest_from_result(
                result=result,
                ctx=ctx,
                input_path=input_path,
                input_artifact=input_artifact,
                started_at=started_at,
                finished_at=finished_at,
                duration_sec=duration_sec,
                output_dir=output_dir
            )

        except Exception as e:
            self.logger.exception(f"Tool execution failed: {e}")
            return self._build_error_manifest(
                ctx=ctx,
                input_path=input_path,
                started_at=started_at,
                error_msg=f"Unexpected error: {e}",
                error_code="QC_EXEC_ERROR"
            )

        finally:
            if self._has_cleanup:
                try:
                    self.tool.cleanup(ctx)  # type: ignore
                except Exception as e:
                    self.logger.warning(f"Cleanup failed: {e}")

            if created_temp_dir and self.cleanup_work_dir and temp_dir_path:
                try:
                    shutil.rmtree(temp_dir_path, ignore_errors=True)
                    self.logger.debug(f"Cleaned up temp directory: {temp_dir_path}")
                except Exception as e:
                    self.logger.warning(
                        f"Failed to cleanup temp directory {temp_dir_path}: {e}")

    def _build_manifest_from_result(
            self,
            result: CapabilityResult,
            ctx: ToolContext,
            input_path: Path,
            input_artifact: ArtifactRef,
            started_at: datetime,
            finished_at: datetime,
            duration_sec: float,
            output_dir: Path
    ) -> RunManifest:
        """Build RunManifest from CapabilityResult."""

        # Normalize result.metadata for JSON-safe manifests
        try:
            safe_result_metadata = normalize_for_json(
                result.metadata,
                path="result.metadata",
                allow_pydantic=True,
                allow_string_fallback=False,
                logger=self.logger
            )
        except TypeError as e:
            self.logger.warning(
                f"Tool {self.tool.name} returned non-JSON-safe metadata: {e}. "
                f"Using empty metadata."
            )
            safe_result_metadata = {}

        tool_info = ToolInfo(
            name=self.tool.name,
            version=self.tool.version,
            metadata=safe_result_metadata
        )

        manifest_input = ManifestInput(
            name="source",
            artifact=input_artifact,
            required=True,
            description="Input file"
        )

        outputs: list[ArtifactRef] = []
        manifest_metadata = dict(ctx.metadata, **safe_result_metadata)

        if result.status == CapabilityStatus.success and result.data is None:
            manifest_metadata["no_output"] = True
            self.logger.info(
                f"Tool {self.tool.name} returned success with no output data")

        if result.status == CapabilityStatus.success and result.data is not None:
            output_path = output_dir / f"{input_path.stem}.{ctx.run_id}.json"

            try:
                serialized = normalize_for_json(
                    result.data,
                    path="output",
                    allow_pydantic=True,
                    allow_string_fallback=False,
                    logger=self.logger
                )
            except TypeError as e:
                return RunManifest(
                    run_id=ctx.run_id,
                    tool=tool_info,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_sec=duration_sec,
                    status=CapabilityStatus.error,
                    inputs=[manifest_input],
                    outputs=[],
                    intermediates=[],
                    logs=result.logs,
                    error=CapabilityError(
                        code="QC_OUT_SERIALIZE_ERROR",
                        message=str(e)
                    ),
                    metadata=manifest_metadata
                )

            write_result = fs.write_json(str(output_path), serialized, indent=2)

            if not write_result.success:
                return RunManifest(
                    run_id=ctx.run_id,
                    tool=tool_info,
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_sec=duration_sec,
                    status=CapabilityStatus.error,
                    inputs=[manifest_input],
                    outputs=[],
                    intermediates=[],
                    logs=result.logs,
                    error=CapabilityError(
                        code="QC_IO_WRITE_ERROR",
                        message=f"Failed to write output: {write_result.error}"
                    ),
                    metadata=manifest_metadata
                )

            output_artifact = ArtifactRef(
                role=f"{self.tool.name}.output",
                kind=ArtifactKind.final,
                content_type="application/json",
                storage=StorageRef(
                    scheme=StorageScheme.local,
                    uri=f"file://{output_path.absolute()}"
                )
            )
            outputs.append(output_artifact)

        return RunManifest(
            run_id=ctx.run_id,
            tool=tool_info,
            started_at=started_at,
            finished_at=finished_at,
            duration_sec=duration_sec,
            status=result.status,
            inputs=[manifest_input],
            outputs=outputs,
            intermediates=[],
            logs=result.logs,
            error=result.error,
            metadata=manifest_metadata
        )

    def _build_error_manifest(
            self,
            ctx: ToolContext | None,
            input_path: Path | None,
            started_at: datetime,
            error_msg: str,
            error_code: str,
            input_artifact: ArtifactRef | None = None
    ) -> RunManifest:
        """Build error manifest with context preserved."""
        finished_at = utcnow()
        duration_sec = (finished_at - started_at).total_seconds()

        inputs: list[ManifestInput] = []
        if input_artifact:
            inputs.append(ManifestInput(
                name="source",
                artifact=input_artifact,
                required=True,
                description="Input file"
            ))
        elif input_path:
            file_info_result = fs.get_file_info(str(input_path))
            if file_info_result.success and file_info_result.data:
                file_info = file_info_result.data
                if file_info.exists:
                    ext_result = fs.get_extension(str(input_path))
                    extension = (ext_result.data or "").lower().lstrip(".")
                    content_type = get_content_type(
                        extension) if extension else "application/octet-stream"

                    input_artifact = ArtifactRef(
                        role=f"{self.tool.name}.input",
                        kind=ArtifactKind.intermediate,
                        content_type=content_type,
                        storage=StorageRef(
                            scheme=StorageScheme.local,
                            uri=f"file://{input_path.absolute()}"
                        )
                    )
                    inputs.append(ManifestInput(
                        name="source",
                        artifact=input_artifact,
                        required=True,
                        description="Input file"
                    ))

        metadata = dict(ctx.metadata) if ctx else {}
        metadata["error_code"] = error_code
        metadata["error_message"] = error_msg

        return RunManifest(
            run_id=ctx.run_id if ctx else generate_run_id(),
            tool=ToolInfo(
                name=self.tool.name,
                version=self.tool.version
            ),
            started_at=started_at,
            finished_at=finished_at,
            duration_sec=duration_sec,
            status=CapabilityStatus.error,
            inputs=inputs,
            outputs=[],
            intermediates=[],
            logs=[],
            error=CapabilityError(
                code=error_code,
                message=error_msg
            ),
            metadata=metadata
        )