# quack-core/tests/test_workflow/output/test_writers.py
from pathlib import Path
from types import SimpleNamespace

import pytest

import quack_core.workflow.output.writers as writers_mod
from quack_core.workflow.output.writers import DefaultOutputWriter, YAMLOutputWriter


class StubFS:
    def write_json(self, path, data, indent=None):
        return SimpleNamespace(success=True, path=str(path))

    def write_text(self, path, data):
        return SimpleNamespace(success=True, path=str(path))


@pytest.fixture(autouse=True)
def patch_fs_service(monkeypatch):
    """
    Patch the filesystem service functions using the standalone module.

    This approach uses monkeypatch to replace individual functions in the
    standalone module with our stub implementations.
    """
    stub = StubFS()

    # Import the standalone module
    from quack_core.lib.fs.service import standalone

    # Replace individual functions in the standalone module
    monkeypatch.setattr(standalone, "write_json", stub.write_json)
    monkeypatch.setattr(standalone, "write_text", stub.write_text)

    return stub


def test_default_writer_basics(tmp_path: Path):
    w = DefaultOutputWriter(indent=3)
    assert w.get_extension() == ".json"
    assert w._indent == 3
    # valid data
    assert w.validate_data({"a": 1})
    assert w.validate_data([1, 2, 3])
    # invalid types
    with pytest.raises(ValueError):
        w.validate_data("nope")
    with pytest.raises(ValueError):
        w.validate_data({"x": {1, 2}})

    # write_output adds extension
    p = tmp_path / "o"
    ret = w.write_output({"k": 2}, p)
    assert ret.endswith(".json")
    # if extension present, unchanged
    q = tmp_path / "q.json"
    assert w.write_output([], q) == str(q)


def test_default_writer_write_wrapper(tmp_path: Path):
    w = DefaultOutputWriter()
    opts = {"output_dir": str(tmp_path)}
    out = w.write([{"a": 1}], str(tmp_path / "in.txt"), opts)
    assert out["success"] is True
    assert out["output_path"].endswith("in.json")


def test_yaml_writer(monkeypatch, tmp_path: Path):
    w = YAMLOutputWriter(default_flow_style=True)
    assert w.get_extension() == ".yaml"
    assert w.validate_data({"b": 3})
    out = w.write_output({"b": 3}, tmp_path / "y")
    assert out.endswith(".yaml")
    # wrapper
    opts = {"output_dir": str(tmp_path)}
    res = w.write([{"c": 4}], str(tmp_path / "f.txt"), opts)
    assert res["success"] is True
    assert res["output_path"].endswith("f.yaml")

    # missing yaml dependency
    monkeypatch.setattr(writers_mod, "yaml", None)
    w2 = YAMLOutputWriter()
    with pytest.raises(ImportError):
        w2.validate_data({"x": 1})
