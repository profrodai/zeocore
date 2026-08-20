from pathlib import Path
from types import SimpleNamespace

from _pytest.monkeypatch import MonkeyPatch

from zeo_core.integrations.jupytext.config import JupytextConfig
from zeo_core.integrations.jupytext.converter import NotebookConverter
from zeo_core.integrations.jupytext.models import ConversionTask, NotebookInfo


def test_converter_init_detects_real_jupytext_version(fs_stub: SimpleNamespace) -> None:
    converter = NotebookConverter(JupytextConfig())
    assert converter.jupytext_version != "unknown"


def test_converter_init_swallows_verify_failure(
    fs_stub: SimpleNamespace, monkeypatch: MonkeyPatch
) -> None:
    import zeo_core.integrations.jupytext.converter as converter_mod

    def broken_verify() -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(converter_mod, "verify_jupytext", broken_verify)
    converter = NotebookConverter(JupytextConfig())
    assert converter.jupytext_version == "unknown"


def test_convert_file_to_ipynb_dispatches_to_notebook(fs_stub: SimpleNamespace) -> None:
    converter = NotebookConverter(JupytextConfig())
    result = converter.convert_file("ex01.py", "ex01.ipynb", "ipynb")
    assert result.success is True
    assert result.content == "ex01.ipynb"


def test_convert_file_guesses_ipynb_from_output_extension(
    fs_stub: SimpleNamespace,
) -> None:
    converter = NotebookConverter(JupytextConfig())
    result = converter.convert_file("ex01.py", "ex01.ipynb")
    assert result.success is True


def test_convert_file_to_script_dispatches_to_script(fs_stub: SimpleNamespace) -> None:
    converter = NotebookConverter(JupytextConfig())
    result = converter.convert_file("notebook.ipynb", "notebook.py", "py:percent")
    assert result.success is True
    assert result.content == "notebook.py"


def test_convert_file_propagates_error(fs_stub: SimpleNamespace) -> None:
    fs_stub.get_file_info = lambda path: SimpleNamespace(success=False, exists=False)
    converter = NotebookConverter(JupytextConfig())
    result = converter.convert_file("missing.py", "out.ipynb", "ipynb")
    assert result.success is False
    assert result.error is not None


def test_convert_batch_all_succeed(fs_stub: SimpleNamespace) -> None:
    converter = NotebookConverter(JupytextConfig())
    tasks = [
        ConversionTask(
            source=NotebookInfo(path="ex01.py", format="py:percent"),
            target_format="ipynb",
        ),
        ConversionTask(
            source=NotebookInfo(path="ex02.py", format="py:percent"),
            target_format="ipynb",
        ),
    ]
    result = converter.convert_batch(tasks)
    assert result.success is True
    assert result.content is not None
    assert len(result.content) == 2


def test_convert_batch_empty_tasks(fs_stub: SimpleNamespace) -> None:
    converter = NotebookConverter(JupytextConfig())
    result = converter.convert_batch([])
    assert result.success is True
    assert result.content == []


def test_convert_batch_partial_failure(fs_stub: SimpleNamespace) -> None:
    converter = NotebookConverter(JupytextConfig())

    real_get_file_info = fs_stub.get_file_info

    def selective_get_file_info(path: str) -> SimpleNamespace:
        if "bad" in path:
            return SimpleNamespace(success=False, exists=False)
        result: SimpleNamespace = real_get_file_info(path)
        return result

    fs_stub.get_file_info = selective_get_file_info

    tasks = [
        ConversionTask(
            source=NotebookInfo(path="ex01.py", format="py:percent"),
            target_format="ipynb",
        ),
        ConversionTask(
            source=NotebookInfo(path="bad.py", format="py:percent"),
            target_format="ipynb",
        ),
    ]
    result = converter.convert_batch(tasks)
    assert result.success is True
    assert result.content is not None
    assert len(result.content) == 1
    assert "Partially successful" in (result.message or "")
    assert result.error is not None


def test_convert_batch_all_fail(fs_stub: SimpleNamespace) -> None:
    fs_stub.get_file_info = lambda path: SimpleNamespace(success=False, exists=False)
    converter = NotebookConverter(JupytextConfig())
    tasks = [
        ConversionTask(
            source=NotebookInfo(path="bad.py", format="py:percent"),
            target_format="ipynb",
        ),
    ]
    result = converter.convert_batch(tasks)
    assert result.success is False


def test_convert_batch_respects_output_dir_override(fs_stub: SimpleNamespace) -> None:
    converter = NotebookConverter(JupytextConfig())
    tasks = [
        ConversionTask(
            source=NotebookInfo(path="sub/ex01.py", format="py:percent"),
            target_format="ipynb",
        ),
    ]
    result = converter.convert_batch(tasks, output_dir="other_dir")
    assert result.success is True
    assert result.content == ["other_dir/ex01.ipynb"]


def test_validate_conversion_true_for_real_file(
    fs_stub: SimpleNamespace, tmp_path: Path
) -> None:
    real_path = tmp_path / "out.ipynb"
    real_path.write_text("x" * 100)
    converter = NotebookConverter(JupytextConfig())
    assert converter.validate_conversion(str(real_path), "in.py") is True


def test_validate_conversion_false_for_missing_file(fs_stub: SimpleNamespace) -> None:
    converter = NotebookConverter(JupytextConfig())
    assert converter.validate_conversion("/no/such/file.ipynb", "in.py") is False


def test_guess_target_format_uses_config_default(fs_stub: SimpleNamespace) -> None:
    from zeo_core.integrations.jupytext.config import JupytextConfig as _Cfg

    converter = NotebookConverter(_Cfg(default_script_format="md"))
    assert converter._guess_target_format("out.unknownext") == "md"


def test_resolve_batch_output_path_explicit_no_override(
    fs_stub: SimpleNamespace,
) -> None:
    converter = NotebookConverter(JupytextConfig())
    task = ConversionTask(
        source=NotebookInfo(path="ex01.py", format="py:percent"),
        target_format="ipynb",
        output_path="explicit/out.ipynb",
    )
    assert converter._resolve_batch_output_path(task, None) == "explicit/out.ipynb"


def test_resolve_batch_output_path_explicit_with_override_dir(
    fs_stub: SimpleNamespace,
) -> None:
    converter = NotebookConverter(JupytextConfig())
    task = ConversionTask(
        source=NotebookInfo(path="ex01.py", format="py:percent"),
        target_format="ipynb",
        output_path="explicit/out.ipynb",
    )
    result = converter._resolve_batch_output_path(task, "override_dir")
    assert result == "override_dir/out.ipynb"
