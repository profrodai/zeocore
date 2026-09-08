"""A small public-API consumer, not a tutorial application or learning grader."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path

from zeo_core.integrations.core.artifacts import artifact_fact
from zeo_core.integrations.environments import IntegrationEnvironment
from zeo_core.integrations.jupytext import (
    JupytextConfig,
    NotebookConverter,
    RequiredConversionTask,
    compare_notebook_semantics,
)
from zeo_core.integrations.notebook import (
    NotebookExecutionRequest,
    execute_notebook,
    get_notebook_environment_identity,
)
from zeo_core.integrations.pandoc import DocumentConverter, PandocConfig

FIXTURE = Path(__file__).resolve().parent / "fixture"


class ReferenceGateError(ValueError):
    """Only fixed application gate codes, never external exception text."""


def require(condition: bool, code: str) -> None:
    """Keep gates active even under python -O."""
    if not condition:
        raise ReferenceGateError(code)


def inspect_fixture(root: Path, expected: dict) -> None:
    """Independent hand-authored expectations, not a round-trip self-comparison."""
    nb = json.loads((root / "clean/lesson.ipynb").read_text())
    cells = nb["cells"]
    require([c["cell_type"] for c in cells] == expected["cell_types"], "CELL_TYPES")
    for index, tags in expected["tags"].items():
        require(cells[int(index)]["metadata"]["tags"] == tags, "TAGS")
    require(cells[4]["metadata"] == expected["reflection"], "REFLECTION")
    require(".noeval" in "".join(cells[2]["source"]), "NOEVAL")
    prose = "".join(cells[0]["source"])
    require("Café, λ and 東京" in prose and "(asset.txt)" in prose, "PROSE_ASSET")
    require(all(not c.get("outputs") for c in cells), "STALE_OUTPUTS")


def convert(root: Path, docx: bool) -> dict:
    converter = NotebookConverter(JupytextConfig())
    task = RequiredConversionTask(
        task_id="notebook",
        source_path="source.md",
        output_path="lesson.ipynb",
        target_format="ipynb",
    )
    batch = converter.convert_batch_strict([task], "clean", workspace_root=str(root))
    require(batch.success and batch.content is not None, "REQUIRED_CONVERSION")
    back = converter.convert_file_with_receipt(
        "clean/lesson.ipynb", "roundtrip.md", "md", workspace_root=str(root)
    )
    require(back.success, "ROUNDTRIP")
    parity = compare_notebook_semantics("source.md", "roundtrip.md")
    require(parity.success, "PARITY")
    expected = json.loads((root / "expected.json").read_text())
    inspect_fixture(root, expected)
    execution = execute_notebook(
        NotebookExecutionRequest(
            source_path="clean/lesson.ipynb",
            output_path="executed.ipynb",
            workspace_root=str(root),
            working_directory=str(root),
            environment_lock_path="environment.lock",
            expected_environment_sha256=get_notebook_environment_identity()[
                "environment_sha256"
            ],
        )
    )
    require(execution.success and execution.content is not None, "EXECUTION")
    require(
        execution.content.code_cells_executed == expected["executed_cells"],
        "EXECUTED_COUNT",
    )
    require(execution.content.code_cells_skipped == 0, "UNDECLARED_SKIP")
    require(execution.content.code_cells_failed == 0, "UNEXPECTED_ERROR")
    require(
        execution.content.code_cells_completed == expected["executed_cells"],
        "COMPLETED_COUNT",
    )
    executed = json.loads((root / "executed.ipynb").read_text())
    output = "".join(executed["cells"][1]["outputs"][0]["text"])
    require(output == expected["output"], "INDEPENDENT_OUTPUT_CHECK")
    # Keep the relative asset valid beside BOTH notebook paths.
    shutil.copyfile(root / "asset.txt", root / "clean/asset.txt")
    optional: dict = {"status": "UNAVAILABLE", "reason": "NOT_REQUESTED"}
    if docx:
        # Pandoc documents this fixed epoch for reproducible archive timestamps.
        os.environ["SOURCE_DATE_EPOCH"] = "315532800"
        export = DocumentConverter(PandocConfig()).convert_file_with_receipt(
            "source.md", "review.docx", "docx", workspace_root=str(root)
        )
        optional = {
            "status": "SUCCEEDED" if export.success else "FAILED",
            "receipt": export.model_dump(mode="json"),
        }
    return {
        "batch": batch.model_dump(mode="json"),
        "roundtrip": back.model_dump(mode="json"),
        "parity": parity.model_dump(mode="json"),
        "execution": execution.model_dump(mode="json"),
        "independent_fixture_checks": "PASSED",
        "optional_docx": optional,
    }


def build(destination: Path, fixture: Path, docx: bool) -> None:
    require(not destination.exists() and not destination.is_symlink(), "OUTPUT_EXISTS")
    # Exclusive sibling lock prevents concurrent reference builds to one destination.
    lock = destination.with_name("." + destination.name + ".lock")
    lock.mkdir()
    previous = Path.cwd()
    try:
        with tempfile.TemporaryDirectory(
            prefix=".reference-", dir=destination.parent
        ) as tmp:
            root = Path(tmp).resolve()
            for name in ("source.md", "asset.txt", "expected.json"):
                shutil.copyfile(fixture / name, root / name)
            shutil.copyfile(
                Path(__file__).resolve().parents[2] / "uv.lock",
                root / "environment.lock",
            )
            subprocess.run(  # noqa: S603 -- explicit local repository setup
                ["/usr/bin/git", "init", "-q", str(root)], check=True
            )
            os.chdir(root)
            receipts = convert(root, docx)
            artifacts = [
                artifact_fact(p, p.suffix.lstrip("."), root).model_dump()
                for p in sorted(root.rglob("*"))
                if p.is_file() and ".git" not in p.relative_to(root).parts
            ]
            release = {
                "status": "SUCCEEDED",
                "scope": "AUTHORING_SUBSTRATE_REFERENCE",
                "publication_status": "NOT_PUBLISHED",
                "zeocore_version": version("zeocore"),
                "artifacts": artifacts,
                "receipts": receipts,
                "human_visual_approval": False,
                "student_learning_evidence": "UNAVAILABLE",
                "normalization": ["conversion receipts: details.conversion_time only"],
                "pandoc_source_date_epoch": "315532800" if docx else None,
            }
            (root / "release.json").write_text(
                json.dumps(release, indent=2, sort_keys=True) + "\n"
            )
            shutil.rmtree(root / ".git")
            os.chdir(previous)
            require(not destination.exists(), "OUTPUT_EXISTS")
            root.rename(destination)
    finally:
        os.chdir(previous)
        lock.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--mode", choices=("test", "production"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--docx", action="store_true")
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    require(
        args.run_id.isascii() and args.run_id.replace("-", "").isalnum(),
        "INVALID_RUN_ID",
    )
    fixture = args.fixture.resolve(strict=True)
    environment = IntegrationEnvironment(
        args.mode, args.state_root, ("jupytext", "pandoc")
    )
    if not args.child:
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--child",
            "--state-root",
            str(environment.root),
            "--mode",
            args.mode,
            "--run-id",
            args.run_id,
            "--fixture",
            str(fixture),
        ]
        if args.docx:
            command.append("--docx")
        return environment.run(command)
    require(
        os.environ.get("ZEO_INTEGRATION_STATE_DIR") == str(environment.state_dir),
        "ENVIRONMENT",
    )
    build(environment.work_dir / args.run_id, fixture, args.docx)
    print(json.dumps({"status": "SUCCEEDED", "run": args.run_id, "mode": args.mode}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReferenceGateError as exc:
        print(json.dumps({"status": "FAILED", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1) from None
    except ValueError, OSError, KeyError, TypeError:
        print('{"status":"FAILED","error":"REFERENCE_GATE_FAILED"}', file=sys.stderr)
        raise SystemExit(1) from None
