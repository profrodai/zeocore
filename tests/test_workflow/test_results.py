# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_workflow/test_results.py
# role: tests
# neighbors: __init__.py, example_test.py
# exports: test_input_result_defaults, test_output_result_fields, test_final_result_fields
# git_branch: refactor/toolkitWorkflow
# git_commit: 66ff061
# === QV-LLM:END ===

from pathlib import Path

from quack_core.workflow.results import FinalResult, InputResult, OutputResult


def test_input_result_defaults(tmp_path: Path):
    p = tmp_path / "file.txt"
    p.write_text("hello")
    ir = InputResult(path=p)
    assert isinstance(ir.path, Path)
    assert ir.path == p
    assert ir.metadata == {}
    # model_dump should include path as a Path object - we don't need to convert
    # Just fix the test to expect a Path object instead of a string
    d = ir.model_dump()
    assert d["path"] == p


def test_output_result_fields():
    ok = OutputResult(success=True, content={"foo": "bar"})
    assert ok.success is True
    assert ok.content == {"foo": "bar"}
    assert ok.raw_text is None

    err = OutputResult(success=False, content=None, raw_text="oops")
    assert err.success is False
    assert err.content is None
    assert err.raw_text == "oops"


def test_final_result_fields(tmp_path: Path):
    out = tmp_path / "out.json"
    fr = FinalResult(success=False, result_path=out, metadata={"x": 1})
    assert fr.success is False
    assert fr.result_path == out
    assert fr.metadata["x"] == 1
