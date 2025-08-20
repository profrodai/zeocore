# quack-core/tests/test_workflow/output/test_base.py
import pytest

from quackcore.workflow.output.base import OutputWriter


def test_base_is_abstract():
    with pytest.raises(TypeError):
        OutputWriter()  # cannot instantiate abstract base

    # even subclass without implementation is still abstract
    class Incomplete(OutputWriter):
        pass

    with pytest.raises(TypeError):
        Incomplete()
