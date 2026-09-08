"""Fail-closed semantic comparison for constrained notebook authoring."""

import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from zeo_core.integrations.core.artifacts import NotebookCellFact
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.jupytext.operations.utils import detect_format


class NotebookParityReceipt(BaseModel):
    """Semantic equality excluding execution outputs and named tool version metadata."""

    equivalent: bool
    source_digest: str
    derived_digest: str
    mismatch: str | None = None
    normalizations: tuple[str, ...] = (
        "jupytext.text_representation.jupytext_version",
        "line endings CRLF to LF",
        "parser-generated IDs in text representations are not declared IDs",
    )


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    ).hexdigest()


def notebook_semantics(
    path: Path,
) -> tuple[dict[str, Any], tuple[NotebookCellFact, ...]]:
    """Parse declared IDs and retain every unknown metadata field."""
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError("EMPTY_INPUT")
    if path.suffix == ".ipynb":
        notebook = json.loads(text)
    else:
        jupytext = importlib.import_module("jupytext")
        notebook = jupytext.reads(text, fmt=detect_format(text, str(path)))
    cells = notebook.get("cells")
    if not isinstance(cells, list):
        raise ValueError("INVALID_NOTEBOOK")
    if not cells:
        raise ValueError("ZERO_CELLS")
    metadata = json.loads(json.dumps(notebook.get("metadata", {})))
    representation = metadata.get("jupytext", {}).get("text_representation", {})
    representation.pop("jupytext_version", None)
    facts: list[NotebookCellFact] = []
    for index, cell in enumerate(cells):
        if cell.get("cell_type") not in ("markdown", "code", "raw"):
            raise ValueError("UNSUPPORTED_CELL_TYPE")
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        cell_metadata = cell.get("metadata", {})
        # Jupytext assigns a fresh random id when parsing text. Only IDs stored
        # in notebook JSON are declared nbformat IDs; text metadata remains exact.
        cell_id = cell.get("id") if path.suffix == ".ipynb" else None
        facts.append(
            NotebookCellFact(
                ordinal=index,
                cell_type=cell["cell_type"],
                cell_id=cell_id,
                tags=tuple(cell_metadata.get("tags", [])),
                source_sha256=hashlib.sha256(
                    source.replace("\r\n", "\n").encode("utf-8")
                ).hexdigest(),
                metadata_sha256=_digest(cell_metadata),
                attachments_sha256=_digest(cell.get("attachments", {})),
            )
        )
    return {
        "metadata": metadata,
        "cells": [f.model_dump(mode="json") for f in facts],
    }, tuple(facts)


def compare_notebook_semantics(
    source_path: str, derived_path: str
) -> IntegrationResult[NotebookParityReceipt]:
    """Compare semantic pairs, naming the first mismatch; never ignore unknown drift."""
    try:
        left, _ = notebook_semantics(Path(source_path))
        right, _ = notebook_semantics(Path(derived_path))
        mismatch = None
        if left["metadata"] != right["metadata"]:
            mismatch = "NOTEBOOK_METADATA"
        elif len(left["cells"]) != len(right["cells"]):
            mismatch = "CELL_COUNT"
        else:
            for index, (a, b) in enumerate(
                zip(left["cells"], right["cells"], strict=True)
            ):
                for key in a:
                    if a[key] != b[key]:
                        mismatch = f"CELL_{index}:{key}"
                        break
                if mismatch:
                    break
        receipt = NotebookParityReceipt(
            equivalent=mismatch is None,
            source_digest=_digest(left),
            derived_digest=_digest(right),
            mismatch=mismatch,
        )
        return IntegrationResult(
            success=receipt.equivalent, content=receipt, error=mismatch
        )
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        ImportError,
    ) as exc:
        # Never echo source contents or parser exceptions into a portable receipt.
        code = (
            str(exc)
            if str(exc)
            in {
                "EMPTY_INPUT",
                "ZERO_CELLS",
                "UNSUPPORTED_CELL_TYPE",
                "INVALID_NOTEBOOK",
            }
            else "PARITY_READ_FAILED"
        )
        return IntegrationResult.error_result(code)
