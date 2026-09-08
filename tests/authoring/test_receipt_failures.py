"""Positive controls for the receipt write gate and real Pandoc operations."""

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from zeo_core.integrations.core.artifacts import artifact_fact, validate_output
from zeo_core.integrations.core.conversion_receipts import convert_with_receipt
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.jupytext.models import ConversionDetails
from zeo_core.integrations.jupytext.service import JupytextIntegration
from zeo_core.integrations.pandoc.service import PandocIntegration


@pytest.mark.parametrize(
    "mode",
    [
        "false_success",
        "exception",
        "failed",
        "bad_details",
        "invalid",
        "empty_output",
        "source_changed",
        "validator",
        "racing_output",
    ],
)
def test_conversion_failure_never_publishes(tmp_path: Path, mode: str) -> None:
    source, output = tmp_path / "source.md", tmp_path / "output.md"
    source.write_text("# Canonical")

    def operation(staged: str) -> IntegrationResult:
        if mode == "exception":
            raise RuntimeError("SECRET_SENTINEL")
        if mode == "failed":
            return IntegrationResult.error_result("SECRET_SENTINEL")
        if mode != "false_success":
            Path(staged).write_text("" if mode == "empty_output" else "# Converted")
        if mode == "source_changed":
            source.write_text("# Concurrent change")
        if mode == "racing_output":
            output.write_text("owned by another writer")
        if mode == "bad_details":
            return IntegrationResult.success_result((staged, "not a model"))
        details = ConversionDetails(
            validation_errors=["SECRET_SENTINEL"] if mode == "invalid" else [],
        )
        return IntegrationResult.success_result((staged, details))

    result = convert_with_receipt(
        str(source),
        str(output),
        workspace_root=str(tmp_path),
        source_format="md",
        target_format="md",
        integration_id="test",
        converter_version="1",
        operation=operation,
        validator=(lambda _: False) if mode == "validator" else None,
    )
    assert not result.success
    assert "SECRET_SENTINEL" not in result.model_dump_json()
    assert result.content is not None
    assert result.content.output is None
    if mode == "racing_output":
        assert output.read_text() == "owned by another writer"
    else:
        assert not output.exists()
    assert not list(tmp_path.glob(".conversion-*"))


def test_deterministic_receipt_and_opt_in_paths(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("# Canonical")

    def operation(staged: str) -> IntegrationResult:
        Path(staged).write_text("# Converted")
        return IntegrationResult.success_result(
            (staged, ConversionDetails(conversion_time=5))
        )

    result = convert_with_receipt(
        str(source),
        str(tmp_path / "output.md"),
        workspace_root=str(tmp_path),
        source_format="md",
        target_format="md",
        integration_id="test",
        converter_version="1",
        operation=operation,
        absolute_paths=True,
    )
    assert result.success and result.content is not None
    assert result.content.source.path == str(source)
    digest = result.content.reproducibility_digest()
    result.content.details["conversion_time"] = 123
    assert result.content.reproducibility_digest() == digest
    result.content.converter_version = "2"
    assert result.content.reproducibility_digest() != digest


@pytest.mark.parametrize(
    "mode", ["alias", "collision", "symlink", "traversal", "outside"]
)
def test_path_refusal(tmp_path: Path, mode: str) -> None:
    source = tmp_path / "source.md"
    source.write_text("# Source")
    output = tmp_path / "out.md"
    if mode == "alias":
        output = source
    elif mode == "collision":
        output.write_text("old")
    elif mode == "symlink":
        output.symlink_to(source)
    elif mode == "traversal":
        output = tmp_path / "x" / ".." / "out.md"
    else:
        output = tmp_path.parent / "outside.md"
    with pytest.raises(ValueError):
        validate_output(source, output, tmp_path)


def test_service_refuses_uninitialized() -> None:
    j = JupytextIntegration()
    p = PandocIntegration()
    assert not j.script_to_notebook_with_receipt("a", "b", workspace_root=".").success
    assert not j.notebook_to_script_with_receipt("a", "b", workspace_root=".").success
    assert not j.convert_batch_strict([], "out", workspace_root=".").success
    assert not p.markdown_to_docx_with_receipt("a", "b", workspace_root=".").success
    assert not p.html_to_markdown_with_receipt("a", "b", workspace_root=".").success


def test_real_pandoc_receipts(tmp_path: Path) -> None:
    # Actual converter and actual files in a separate Git-rooted process.
    subprocess.run(  # noqa: S603 -- fixed fixture command
        ["/usr/bin/git", "init", "-q", str(tmp_path)],
        check=True,
    )
    (tmp_path / "source.md").write_text("# A lesson\n\nReceipt-bearing DOCX.")
    (tmp_path / "input.html").write_text(
        "<html><body><h1>A review draft</h1><p>This is a review draft. "
        "It cannot overwrite canonical Markdown.</p></body></html>"
    )
    program = """
import json
from pathlib import Path
from unittest.mock import patch
from zeo_core.integrations.pandoc import DocumentConverter, PandocConfig
c = DocumentConverter(PandocConfig())
root = str(Path.cwd())
results = {}
results["docx"] = c.convert_file_with_receipt(
    "source.md", "review.docx", "docx", workspace_root=root
).model_dump(mode="json")
results["draft"] = c.convert_file_with_receipt(
    "input.html", "draft.md", "markdown", workspace_root=root
).model_dump(mode="json")
results["overwrite"] = c.convert_file_with_receipt(
    "input.html", "source.md", "markdown", workspace_root=root
).model_dump(mode="json")
results["unsupported"] = c.convert_file_with_receipt(
    "source.md", "a.pdf", "pdf", workspace_root=root
).model_dump(mode="json")
with patch("zeo_core.integrations.pandoc.converter.verify_pandoc",
           side_effect=RuntimeError("unavailable")):
    results["missing"] = c.convert_file_with_receipt(
        "source.md", "unavailable.docx", "docx", workspace_root=root
    ).model_dump(mode="json")
Path("results.json").write_text(json.dumps(results))
"""
    child = subprocess.run(  # noqa: S603 -- fixed fixture program
        [sys.executable, "-c", program],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert child.returncode == 0, child.stderr
    results = json.loads((tmp_path / "results.json").read_text())
    assert results["docx"]["success"], results
    receipt = results["docx"]["content"]
    assert receipt["structural_validation"] == "PASSED"
    assert receipt["human_visual_approval"] is False
    assert receipt["converter_version"] != "unknown"
    assert (
        receipt["output"]
        == artifact_fact(tmp_path / "review.docx", "docx", tmp_path).model_dump()
    )
    with zipfile.ZipFile(tmp_path / "review.docx") as archive:
        assert b"A lesson" in archive.read("word/document.xml")
    assert results["draft"]["success"]
    assert results["draft"]["content"]["intended_use"] == "REVIEW_DRAFT"
    assert not results["overwrite"]["success"]
    assert not results["unsupported"]["success"]
    assert not results["missing"]["success"]
    assert not (tmp_path / "unavailable.docx").exists()
    assert (tmp_path / "source.md").read_text().startswith("# A lesson")
