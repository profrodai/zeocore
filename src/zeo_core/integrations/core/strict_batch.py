"""Required-item aggregation with one directory promotion after validation."""

import hashlib
import shutil
import tempfile
import unicodedata
from collections.abc import Callable, Sequence
from pathlib import Path

from zeo_core.integrations.core.artifacts import (
    ConversionBatchItem,
    ConversionBatchReceipt,
    ConversionReceipt,
    RequiredConversionTask,
)
from zeo_core.integrations.core.results import IntegrationResult

type ReceiptConverter = Callable[[str, str, str], IntegrationResult[ConversionReceipt]]


def _contained(path: Path, root: Path) -> None:
    path.resolve().relative_to(root)
    if ".." in path.parts:
        raise ValueError("PATH_TRAVERSAL")
    current = path.absolute()
    while current != root and current != current.parent:
        if current.is_symlink():
            raise ValueError("SYMLINK_PATH")
        current = current.parent


def _destinations(
    tasks: Sequence[RequiredConversionTask],
    destination: Path,
    root: Path,
) -> None:
    ids: set[str] = set()
    outputs: set[Path] = set()
    portable_outputs: set[str] = set()
    sources: set[Path] = set()
    for task in tasks:
        source = Path(task.source_path)
        source = source if source.is_absolute() else root / source
        _contained(source, root)
        sources.add(source.resolve())
        output = Path(task.output_path)
        if output.is_absolute() or ".." in output.parts or not output.parts:
            raise ValueError("INVALID_OUTPUT_PATH")
        final = (destination / output).resolve()
        final.relative_to(destination.resolve())
        if task.task_id in ids:
            raise ValueError("DUPLICATE_TASK_ID")
        portable = unicodedata.normalize("NFC", str(final)).casefold()
        if portable in portable_outputs:
            raise ValueError("DUPLICATE_OUTPUT")
        ids.add(task.task_id)
        outputs.add(final)
        portable_outputs.add(portable)
    if sources & outputs:
        raise ValueError("SOURCE_OUTPUT_ALIAS")
    if any(a != b and a in b.parents for a in outputs for b in outputs):
        raise ValueError("NESTED_OUTPUT_COLLISION")


def _preflight(
    tasks: Sequence[RequiredConversionTask],
    destination: Path,
    root: Path,
) -> None:
    if not tasks:
        raise ValueError("EMPTY_BATCH")
    _contained(destination, root)
    if destination.resolve() == root:
        raise ValueError("INVALID_DESTINATION")
    if not destination.parent.is_dir() or destination.exists():
        raise ValueError("DESTINATION_EXISTS_OR_PARENT_MISSING")
    _destinations(tasks, destination, root)


def _convert(
    task: RequiredConversionTask,
    staged: Path,
    converter: ReceiptConverter,
) -> ConversionBatchItem:
    item = ConversionBatchItem(
        task_id=task.task_id, required=task.required, status="FAILED"
    )
    try:
        result = converter(task.source_path, str(staged), task.target_format)
        item.receipt = result.content
        if (
            result.success
            and result.content is not None
            and result.content.status == "SUCCEEDED"
            and result.content.output is not None
            and staged.is_file()
            and not staged.is_symlink()
            and hashlib.sha256(staged.read_bytes()).hexdigest()
            == result.content.output.sha256
        ):
            item.status = "SUCCEEDED"
        else:
            item.error = "CONVERSION_FAILED"
    except Exception:
        item.error = "CONVERTER_EXCEPTION"
    if item.status == "FAILED" and (staged.exists() or staged.is_symlink()):
        if staged.is_dir() and not staged.is_symlink():
            shutil.rmtree(staged)
        else:
            staged.unlink()
    return item


def _stage_and_promote(
    tasks: Sequence[RequiredConversionTask],
    destination: Path,
    root: Path,
    converter: ReceiptConverter,
    receipt: ConversionBatchReceipt,
) -> None:
    with tempfile.TemporaryDirectory(prefix=".batch-", dir=destination.parent) as temp:
        staging = Path(temp) / "release"
        staging.mkdir()
        receipt.items = tuple(
            _convert(t, staging / t.output_path, converter) for t in tasks
        )
        if any(i.required and i.status != "SUCCEEDED" for i in receipt.items):
            raise ValueError("REQUIRED_ITEM_FAILED")
        if destination.exists() or destination.is_symlink():
            raise ValueError("DESTINATION_EXISTS")
        # Compute final facts before the only promotion, so success cannot become
        # false merely because bookkeeping after a successful rename failed.
        for task, item in zip(tasks, receipt.items, strict=True):
            if item.receipt is not None and item.receipt.output is not None:
                fact = item.receipt.output
                portable = str((destination / task.output_path).relative_to(root))
                item.receipt.output = fact.model_copy(update={"path": portable})
        staging.rename(destination)
        receipt.status = "SUCCEEDED"
        receipt.promoted = True


def convert_batch_strict(
    tasks: Sequence[RequiredConversionTask],
    output_dir: str,
    *,
    workspace_root: str,
    converter: ReceiptConverter,
) -> IntegrationResult[ConversionBatchReceipt]:
    """Require an absent destination. Clean failed staging and promote nothing."""
    root = Path(workspace_root).resolve()
    destination = Path(output_dir)
    destination = destination if destination.is_absolute() else root / destination
    receipt = ConversionBatchReceipt(
        items=tuple(
            ConversionBatchItem(
                task_id=t.task_id, required=t.required, status="NOT_RUN"
            )
            for t in tasks
        ),
        status="FAILED",
        output_directory=output_dir,
    )
    try:
        _preflight(tasks, destination, root)
    except (OSError, ValueError) as exc:
        code = (
            str(exc)
            if isinstance(exc, ValueError) and str(exc).isupper()
            else "INVALID_PATH"
        )
        return IntegrationResult(success=False, content=receipt, error=code)
    lock = destination.parent / ("." + destination.name + ".promotion-lock")
    try:
        lock.mkdir()
    except OSError:
        return IntegrationResult(
            success=False, content=receipt, error="DESTINATION_BUSY"
        )
    try:
        _stage_and_promote(tasks, destination, root, converter, receipt)
        return IntegrationResult.success_result(receipt)
    except (OSError, ValueError) as exc:
        code = (
            str(exc)
            if isinstance(exc, ValueError) and str(exc).isupper()
            else "PROMOTION_FAILED"
        )
        return IntegrationResult(success=False, content=receipt, error=code)
    finally:
        lock.rmdir()
