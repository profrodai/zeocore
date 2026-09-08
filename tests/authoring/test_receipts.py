"""Adversarial controls and real conversions, outside legacy integration FS stubs."""

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, NoReturn

import pytest

from zeo_core.integrations.core.artifacts import RequiredConversionTask
from zeo_core.integrations.core.results import IntegrationResult
from zeo_core.integrations.core.strict_batch import convert_batch_strict
from zeo_core.integrations.jupytext.parity import compare_notebook_semantics

NOTEBOOK: dict[str, Any] = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "name": "python3",
            "language": "python",
            "display_name": "Python 3",
        }
    },
    "cells": [
        {
            "id": "intro",
            "cell_type": "markdown",
            "source": "Café [asset](asset.txt)",
            "metadata": {"purpose": "reflection"},
        },
        {
            "id": "exercise",
            "cell_type": "code",
            "source": "assert 2 + 2 == 4",
            "metadata": {"tags": ["exercise"]},
            "execution_count": None,
            "outputs": [],
        },
    ],
}


def write_nb(path: Path, notebook: dict) -> None:
    path.write_text(json.dumps(notebook))


@pytest.mark.parametrize(
    "change,expected",
    [
        ("order", "cell_type"),
        ("type", "cell_type"),
        ("id", "cell_id"),
        ("tags", "tags"),
        ("source", "source_sha256"),
        ("cell_metadata", "metadata_sha256"),
        ("metadata", "NOTEBOOK_METADATA"),
        ("count", "CELL_COUNT"),
        ("attachment", "attachments_sha256"),
    ],
)
def test_parity_positive_controls(tmp_path: Path, change: str, expected: str) -> None:
    left, right = tmp_path / "a.ipynb", tmp_path / "b.ipynb"
    write_nb(left, NOTEBOOK)
    write_nb(right, NOTEBOOK)
    assert compare_notebook_semantics(str(left), str(right)).success
    changed = copy.deepcopy(NOTEBOOK)
    if change == "order":
        changed["cells"].reverse()
    elif change == "type":
        changed["cells"][0]["cell_type"] = "raw"
    elif change == "id":
        changed["cells"][0]["id"] = "different"
    elif change == "tags":
        changed["cells"][1]["metadata"]["tags"] = ["solution"]
    elif change == "source":
        changed["cells"][0]["source"] += " drift"
    elif change == "cell_metadata":
        changed["cells"][0]["metadata"]["unknown"] = "drift"
    elif change == "metadata":
        changed["metadata"]["unknown"] = "drift"
    elif change == "count":
        changed["cells"].pop()
    else:
        changed["cells"][0]["attachments"] = {"a": {"text/plain": "changed"}}
    write_nb(right, changed)
    result = compare_notebook_semantics(str(left), str(right))
    assert not result.success
    assert result.error is not None
    assert expected in result.error


def test_named_version_normalization_only(tmp_path: Path) -> None:
    a, b = tmp_path / "a.ipynb", tmp_path / "b.ipynb"
    nb = copy.deepcopy(NOTEBOOK)
    nb["metadata"]["jupytext"] = {"text_representation": {"extension": ".md"}}
    write_nb(a, nb)
    nb["metadata"]["jupytext"]["text_representation"]["jupytext_version"] = "9.9.9"
    write_nb(b, nb)
    assert compare_notebook_semantics(str(a), str(b)).success
    nb["metadata"]["jupytext"]["text_representation"]["unknown"] = "never ignore"
    write_nb(b, nb)
    assert not compare_notebook_semantics(str(a), str(b)).success


@pytest.mark.parametrize(
    "content,code",
    [
        ("", "EMPTY_INPUT"),
        ('{"cells":[]}', "ZERO_CELLS"),
        ('{"cells":[{"cell_type":"unexpected"}]}', "UNSUPPORTED_CELL_TYPE"),
    ],
)
def test_invalid_notebooks(tmp_path: Path, content: str, code: str) -> None:
    path = tmp_path / "a.ipynb"
    path.write_text(content)
    assert compare_notebook_semantics(str(path), str(path)).error == code


def task(
    identity: str, output: str, source: str = "source.md", required: bool = True
) -> RequiredConversionTask:
    return RequiredConversionTask(
        task_id=identity,
        source_path=source,
        output_path=output,
        target_format="ipynb",
        required=required,
    )


@pytest.mark.parametrize(
    "tasks,code",
    [
        ([], "EMPTY_BATCH"),
        ([task("a", "a.ipynb"), task("a", "b.ipynb")], "DUPLICATE_TASK_ID"),
        ([task("a", "a.ipynb"), task("b", "a.ipynb")], "DUPLICATE_OUTPUT"),
        ([task("a", "a.ipynb"), task("b", "A.ipynb")], "DUPLICATE_OUTPUT"),
        ([task("a", "../outside.ipynb")], "INVALID_OUTPUT_PATH"),
        ([task("a", "/outside.ipynb")], "INVALID_OUTPUT_PATH"),
        ([task("a", "a.ipynb", "release/a.ipynb")], "SOURCE_OUTPUT_ALIAS"),
        ([task("a", "a"), task("b", "a/b")], "NESTED_OUTPUT_COLLISION"),
    ],
)
def test_preflight_before_writes(tmp_path: Path, tasks: list, code: str) -> None:
    def forbidden(*args: object) -> NoReturn:
        raise AssertionError("converter must not run")

    before = list(tmp_path.iterdir())
    result = convert_batch_strict(
        tasks, "release", workspace_root=str(tmp_path), converter=forbidden
    )
    assert result.error == code
    assert result.content is not None
    assert len(result.content.items) == len(tasks)
    assert list(tmp_path.iterdir()) == before


def test_symlink_destination(tmp_path: Path) -> None:
    (tmp_path / "link").symlink_to(tmp_path.parent, target_is_directory=True)
    result = convert_batch_strict(
        [task("a", "a.ipynb")],
        "link/release",
        workspace_root=str(tmp_path),
        converter=lambda *_: IntegrationResult.error_result("UNEXPECTED_CALL"),
    )
    assert not result.success
    assert not (tmp_path.parent / "release").exists()


def test_real_public_pipeline(tmp_path: Path) -> None:
    # This child uses real fs services, not the parent suite's global FS mocks.
    subprocess.run(  # noqa: S603 -- fixed fixture command
        ["/usr/bin/git", "init", "-q", str(tmp_path)], check=True
    )  # noqa: S603 -- fixed test command
    source = tmp_path / "source.md"
    source.write_text("""---
jupyter:
  jupytext:
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
---

# A lesson

```python tags=["exercise"]
assert 2 + 2 == 4
```

```python .noeval
raise RuntimeError("not executed")
```

<!-- #region purpose="reflection" -->
Café [asset](asset.txt).
<!-- #endregion -->
""")
    program = """
import json
from pathlib import Path
from zeo_core.integrations.jupytext import JupytextConfig, NotebookConverter
from zeo_core.integrations.jupytext.parity import compare_notebook_semantics
from zeo_core.integrations.core.artifacts import RequiredConversionTask as Task

c = NotebookConverter(JupytextConfig())
root = str(Path.cwd())
results = {}


def run(tasks, name):
    return c.convert_batch_strict(tasks, name, workspace_root=root)


good = Task(
    task_id="good",
    source_path="source.md",
    output_path="lesson.ipynb",
    target_format="ipynb",
)
bad = Task(
    task_id="bad",
    source_path="missing.md",
    output_path="bad.ipynb",
    target_format="ipynb",
)
results["required"] = run([good, bad], "failed").model_dump(mode="json")
results["optional"] = run(
    [good, bad.model_copy(update={"required": False})], "optional"
).model_dump(mode="json")
results["repeat"] = run([good], "optional").model_dump(mode="json")
results["second"] = run([good], "second").model_dump(mode="json")
service = __import__(
    "zeo_core.integrations.jupytext", fromlist=["JupytextIntegration"]
).JupytextIntegration()
assert service.initialize().success
results["service"] = service.script_to_notebook_with_receipt(
    "source.md", "service.ipynb", workspace_root=root
).model_dump(mode="json")
results["service_back"] = service.notebook_to_script_with_receipt(
    "service.ipynb", "service.md", workspace_root=root
).model_dump(mode="json")
results["service_batch"] = service.convert_batch_strict(
    [good], "service-release", workspace_root=root
).model_dump(mode="json")
results["service_parity"] = service.compare_notebook_semantics(
    "source.md", "service.md"
).model_dump(mode="json")

results["back"] = c.convert_file_with_receipt(
    "optional/lesson.ipynb", "roundtrip.md", "md", workspace_root=root
).model_dump(mode="json")
results["parity"] = compare_notebook_semantics("source.md", "roundtrip.md").model_dump(
    mode="json"
)
results["collision"] = c.convert_file_with_receipt(
    "source.md", "source.md", "md", workspace_root=root
).model_dump(mode="json")
Path("results.json").write_text(json.dumps(results))
"""
    completed = subprocess.run(  # noqa: S603 -- fixed fixture program
        [sys.executable, "-c", program], cwd=tmp_path, capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stderr
    results = json.loads((tmp_path / "results.json").read_text())
    assert not results["required"]["success"]
    assert not (tmp_path / "failed").exists()
    assert results["optional"]["success"], results
    items = results["optional"]["content"]["items"]
    assert [item["status"] for item in items] == ["SUCCEEDED", "FAILED"]
    assert not (tmp_path / "optional" / "bad.ipynb").exists()
    assert not results["repeat"]["success"]
    assert results["second"]["success"]
    assert (tmp_path / "second" / "lesson.ipynb").read_bytes() == (
        tmp_path / "optional" / "lesson.ipynb"
    ).read_bytes()
    for key in ("service", "service_back", "service_batch", "service_parity"):
        assert results[key]["success"], results[key]

    assert results["back"]["success"], results["back"]
    assert results["parity"]["success"], results["parity"]
    assert not results["collision"]["success"]
    receipt = items[0]["receipt"]
    notebook = tmp_path / "optional" / "lesson.ipynb"
    assert (
        receipt["source"]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    )
    assert (
        receipt["output"]["sha256"] == hashlib.sha256(notebook.read_bytes()).hexdigest()
    )
    assert receipt["output"]["path"] == "optional/lesson.ipynb"
    assert receipt["details"]["cell_count"] == 4
    nb = json.loads(notebook.read_text())
    assert [c["cell_type"] for c in nb["cells"]] == [
        "markdown",
        "code",
        "markdown",
        "markdown",
    ]
    assert nb["cells"][1]["metadata"]["tags"] == ["exercise"]
    assert ".noeval" in "".join(nb["cells"][2]["source"])
    assert nb["cells"][3]["metadata"] == {"purpose": "reflection"}
    assert not receipt["human_visual_approval"]
    assert not list(tmp_path.glob(".batch-*"))
    assert not list(tmp_path.glob(".*promotion-lock"))
