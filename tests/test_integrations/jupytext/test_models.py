from zeo_core.integrations.jupytext.models import (
    ConversionDetails,
    ConversionTask,
    NotebookInfo,
)


def test_notebook_info_defaults() -> None:
    info = NotebookInfo(path="ex01.py", format="py:percent")
    assert info.path == "ex01.py"
    assert info.format == "py:percent"
    assert info.size == 0
    assert info.cell_count is None


def test_notebook_info_full() -> None:
    info = NotebookInfo(path="ex01.py", format="py:percent", size=200, cell_count=3)
    assert info.size == 200
    assert info.cell_count == 3


def test_conversion_details_defaults() -> None:
    details = ConversionDetails()
    assert details.source_format is None
    assert details.target_format is None
    assert details.validation_errors == []


def test_conversion_details_full() -> None:
    details = ConversionDetails(
        source_format="py:percent",
        target_format="ipynb",
        conversion_time=0.05,
        output_size=512,
        input_size=128,
        cell_count=2,
    )
    assert details.source_format == "py:percent"
    assert details.target_format == "ipynb"
    assert details.cell_count == 2


def test_conversion_task() -> None:
    source = NotebookInfo(path="ex01.py", format="py:percent")
    task = ConversionTask(source=source, target_format="ipynb")
    assert task.source is source
    assert task.target_format == "ipynb"
    assert task.output_path is None


def test_conversion_task_with_output_path() -> None:
    source = NotebookInfo(path="ex01.py", format="py:percent")
    task = ConversionTask(source=source, target_format="ipynb", output_path="out.ipynb")
    assert task.output_path == "out.ipynb"
