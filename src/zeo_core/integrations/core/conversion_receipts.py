"""Receipt construction around existing low-level conversion operations."""

import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, JsonValue

from zeo_core.integrations.core.artifacts import (
    ConversionReceipt,
    artifact_fact,
    validate_output,
)
from zeo_core.integrations.core.results import IntegrationResult

type ConversionOperation = Callable[[str], IntegrationResult]
type CellReader = Callable[[Path], tuple]


def _details(result: IntegrationResult) -> dict[str, JsonValue]:
    if not result.success or result.content is None:
        raise ValueError("CONVERSION_FAILED")
    details = result.content[1]
    if not isinstance(details, BaseModel):
        raise ValueError("MISSING_CONVERSION_DETAILS")
    values = details.model_dump(mode="json")
    if values.get("validation_errors"):
        raise ValueError("VALIDATION_FAILED")
    return values


def convert_with_receipt(
    input_path: str,
    output_path: str,
    *,
    workspace_root: str,
    source_format: str,
    target_format: str,
    integration_id: str,
    converter_version: str,
    operation: ConversionOperation,
    cells: CellReader | None = None,
    absolute_paths: bool = False,
    review_draft: bool = False,
    validator: Callable[[str], bool] | None = None,
) -> IntegrationResult[ConversionReceipt]:
    """Preserve details and validate bytes before exclusively publishing output."""
    source, output, root = Path(input_path), Path(output_path), Path(workspace_root)
    source = source if source.is_absolute() else root / source
    output = output if output.is_absolute() else root / output
    try:
        validate_output(source, output, root)
        source_fact = artifact_fact(
            source, source_format, root, absolute_paths=absolute_paths
        )
        if not source_fact.size_bytes or not source.read_bytes().strip():
            return IntegrationResult.error_result("EMPTY_INPUT")
    except OSError, ValueError:
        return IntegrationResult.error_result("INVALID_PATH_OR_COLLISION")
    receipt = ConversionReceipt(
        integration_id=integration_id,
        converter_version=converter_version,
        source=source_fact,
        status="FAILED",
        structural_validation="UNAVAILABLE",
        intended_use="REVIEW_DRAFT" if review_draft else "DERIVED_ARTIFACT",
    )
    try:
        # The workspace is caller-owned. Nothing is written to a canonical input.
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=".conversion-", dir=output.parent
        ) as staging:
            staged = Path(staging) / output.name
            result = operation(str(staged))
            receipt.details = _details(result)
            if not staged.is_file() or staged.is_symlink() or not staged.stat().st_size:
                raise ValueError("MISSING_OUTPUT")
            if validator is not None and not validator(str(staged)):
                raise ValueError("STRUCTURAL_VALIDATION_FAILED")
            if cells:
                receipt.cells = cells(staged)
            if artifact_fact(source, source_format, root).sha256 != source_fact.sha256:
                raise ValueError("SOURCE_CHANGED")
            # link is exclusive: a racing writer cannot be silently overwritten.
            fact = artifact_fact(staged, target_format, root)
            final_path = (
                str(output.resolve())
                if absolute_paths
                else str(output.resolve().relative_to(root.resolve()))
            )
            receipt.output = fact.model_copy(update={"path": final_path})
            os.link(staged, output)
            receipt.status = "SUCCEEDED"
            receipt.structural_validation = "PASSED"
            return IntegrationResult.success_result(receipt)
    except Exception:
        receipt.output = None
        receipt.validation_errors = ("CONVERSION_OR_VALIDATION_FAILED",)
        receipt.structural_validation = "FAILED"
        return IntegrationResult(
            success=False, content=receipt, error="CONVERSION_OR_VALIDATION_FAILED"
        )
