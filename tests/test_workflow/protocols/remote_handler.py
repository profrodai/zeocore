# quack-core/tests/test_workflow/protocols/remote_handler.py
from pathlib import Path

from quackcore.workflow.protocols.remote_handler import RemoteFileHandler
from quackcore.workflow.results import InputResult


class Good:
    def is_remote(self, src: str) -> bool:
        return False
    def download(self, src: str) -> InputResult:
        return InputResult(path=Path(src))


class Bad:
    def is_remote(self, src: str) -> bool:
        return False


def test_protocol_runtime_checkable():
    g = Good()
    assert isinstance(g, RemoteFileHandler)
    b = Bad()
    assert not isinstance(b, RemoteFileHandler)
