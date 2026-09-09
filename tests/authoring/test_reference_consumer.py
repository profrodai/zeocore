"""Exercise the reference consumer as a real independent installed application."""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "examples/authoring_reference/run.py"
FIXTURE = SCRIPT.parent / "fixture"


def run(root: Path, mode: str, run_id: str, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 -- fixed reference application
        [
            sys.executable,
            str(SCRIPT),
            "--state-root",
            str(root),
            "--mode",
            mode,
            "--run-id",
            run_id,
            *extra,
        ],
        capture_output=True,
        text=True,
        timeout=90,
    )


def normalized(release: dict) -> dict:
    """The ONLY excluded receipt field is the documented conversion timer."""
    receipts = release["receipts"]
    for item in receipts["batch"]["content"]["items"]:
        item["receipt"]["details"].pop("conversion_time", None)
    receipts["roundtrip"]["content"]["details"].pop("conversion_time", None)
    optional = receipts["optional_docx"]
    if optional["status"] == "SUCCEEDED":
        optional["receipt"]["content"]["details"].pop("conversion_time", None)
    return release


def test_reference_repeated_and_separate_environments(tmp_path: Path) -> None:
    payloads = []
    for mode, name in [("test", "one"), ("test", "two"), ("production", "one")]:
        result = run(tmp_path, mode, name, "--docx")
        assert result.returncode == 0, result.stderr
        directory = tmp_path / mode / "work" / name
        release = json.loads((directory / "release.json").read_text())
        for fact in release["artifacts"]:
            data = (directory / fact["path"]).read_bytes()
            assert fact["size_bytes"] == len(data)
            assert fact["sha256"] == hashlib.sha256(data).hexdigest()
        assert release["receipts"]["optional_docx"]["status"] == "SUCCEEDED"
        assert release["receipts"]["execution"]["content"]["cleanup"] == "SUCCEEDED"
        assert release["publication_status"] == "NOT_PUBLISHED"
        assert release["receipts"]["batch"]["content"]["scope"] == "CONVERSION_STAGE"
        assert (
            release["receipts"]["parity"]["content"]["semantic_schema"]
            == "zeocore.notebook-semantics.v1"
        )
        assert release["student_learning_evidence"] == "UNAVAILABLE"
        assert release["human_visual_approval"] is False
        assert "solution-only" in (directory / "clean/lesson.ipynb").read_text()
        assert (directory / "clean/asset.txt").is_file()
        payloads.append(normalized(release))
    assert payloads[0] == payloads[1] == payloads[2]
    previous = (tmp_path / "test/work/one/release.json").read_bytes()
    assert run(tmp_path, "test", "one").returncode != 0
    assert (tmp_path / "test/work/one/release.json").read_bytes() == previous
    for mode in ("test", "production"):
        assert (tmp_path / mode / "config/integrations.yaml").is_file()
        assert not list((tmp_path / mode / "work").glob(".*"))


@pytest.mark.parametrize("change", ["assertion", "oracle", "asset"])
def test_reference_gate_positive_controls(tmp_path: Path, change: str) -> None:
    fixture = tmp_path / "fixture"
    shutil.copytree(FIXTURE, fixture)
    if change == "assertion":
        source = fixture / "source.md"
        source.write_text(
            source.read_text().replace("sum(values) == 10", "sum(values) == 999")
        )
    elif change == "oracle":
        oracle = fixture / "expected.json"
        expected = json.loads(oracle.read_text())
        expected["output"] = "a plausible but wrong output"
        oracle.write_text(json.dumps(expected))
    else:
        (fixture / "asset.txt").write_text("wrong input")
    result = run(tmp_path, "test", "failed", "--fixture", str(fixture))
    assert result.returncode != 0
    expected = "INDEPENDENT_OUTPUT_CHECK" if change == "oracle" else "EXECUTION"
    assert json.loads(result.stderr.splitlines()[-1])["error"] == expected
    assert not (tmp_path / "test/work/failed").exists()
    assert not list((tmp_path / "test/work").iterdir())


def test_reference_optional_export_is_explicit(tmp_path: Path) -> None:
    result = run(tmp_path, "test", "withoutdocx")
    assert result.returncode == 0, result.stderr
    release = json.loads((tmp_path / "test/work/withoutdocx/release.json").read_text())
    assert release["receipts"]["optional_docx"] == {
        "status": "UNAVAILABLE",
        "reason": "NOT_REQUESTED",
    }
    assert not (tmp_path / "test/work/withoutdocx/review.docx").exists()


def test_semantic_digest_retains_exact_observation_differences(tmp_path: Path) -> None:
    from tests.authoring.test_receipts import NOTEBOOK
    from zeo_core.integrations.jupytext import compare_notebook_semantics

    left, right = tmp_path / "left.ipynb", tmp_path / "right.ipynb"
    original = json.dumps(NOTEBOOK)
    left.write_text(original)
    observed = json.loads(original)
    observed["cells"][1]["execution_count"] = 1
    observed["cells"][1]["outputs"] = [
        {"output_type": "stream", "name": "stdout", "text": "run-specific observation"}
    ]
    right.write_text(json.dumps(observed))
    assert (
        hashlib.sha256(left.read_bytes()).digest()
        != hashlib.sha256(right.read_bytes()).digest()
    )
    result = compare_notebook_semantics(str(left), str(right))
    assert result.success and result.content is not None
    assert result.content.semantic_schema == "zeocore.notebook-semantics.v1"
    assert result.content.source_digest == result.content.derived_digest
    observed["cells"][1]["metadata"]["undeclared"] = "drift"
    right.write_text(json.dumps(observed))
    assert not compare_notebook_semantics(str(left), str(right)).success
