# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_workflow/protocols/remote_handler.py
# role: protocols
# neighbors: __init__.py
# exports: Good, Bad, test_protocol_runtime_checkable
# git_branch: refactor/newHeaders
# git_commit: 72778e2
# === QV-LLM:END ===

from pathlib import Path

from quack_core.workflow.protocols.remote_handler import RemoteFileHandler
from quack_core.workflow.results import InputResult


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
