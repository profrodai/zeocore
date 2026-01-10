# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/plugin.py
# module: quack_core.core.fs.plugin
# role: plugin
# neighbors: __init__.py, protocols.py, results.py
# exports: FSPlugin, QuackFSPlugin, create_plugin
# git_branch: feat/9-make-setup-work
# git_commit: 3a380e47
# === QV-LLM:END ===

from pathlib import Path
from typing import Protocol, TypeVar

from quack_core.core.fs.results import DataResult, OperationResult, ReadResult, WriteResult
from quack_core.core.fs.service import FileSystemService, get_service

T = TypeVar("T")

class FSPlugin(Protocol):
    @property
    def name(self) -> str: ...
    def read_text(self, path: str | Path, encoding: str = "utf-8") -> ReadResult[str]: ...
    def write_text(self, path: str | Path, content: str, encoding: str = "utf-8", atomic: bool = True) -> WriteResult: ...
    def read_yaml(self, path: str | Path) -> DataResult[dict]: ...
    def write_yaml(self, path: str | Path, data: dict, atomic: bool = True) -> WriteResult: ...
    def create_directory(self, path: str | Path, exist_ok: bool = True) -> OperationResult: ...

class QuackFSPlugin:
    def __init__(self, service: FileSystemService | None = None) -> None:
        self._service = service if service else get_service()

    @property
    def name(self) -> str:
        return "fs"

    def read_text(self, path: str | Path, encoding: str = "utf-8") -> ReadResult[str]:
        return self._service.read_text(path, encoding)

    def write_text(self, path: str | Path, content: str, encoding: str = "utf-8", atomic: bool = True) -> WriteResult:
        return self._service.write_text(path, content, encoding, atomic)

    def read_yaml(self, path: str | Path) -> DataResult[dict]:
        return self._service.read_yaml(path)

    def write_yaml(self, path: str | Path, data: dict, atomic: bool = True) -> WriteResult:
        return self._service.write_yaml(path, data, atomic)

    def create_directory(self, path: str | Path, exist_ok: bool = True) -> OperationResult:
        return self._service.create_directory(path, exist_ok)

def create_plugin() -> FSPlugin:
    return QuackFSPlugin()