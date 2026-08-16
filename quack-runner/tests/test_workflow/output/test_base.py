# === QV-LLM:BEGIN ===
# path: quack-runner/tests/test_workflow/output/test_base.py
# === QV-LLM:END ===

import pytest

from quack_core.workflow.output.base import OutputWriter


def test_base_is_abstract():
    with pytest.raises(TypeError):
        OutputWriter()  # cannot instantiate abstract base

    # even subclass without implementation is still abstract
    class Incomplete(OutputWriter):
        pass

    with pytest.raises(TypeError):
        Incomplete()
