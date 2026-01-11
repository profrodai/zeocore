from pathlib import Path
from quack_core.core.fs._internal.file_ops import _read_file_text, _read_file_bytes

class ReadOperationsMixin:
    def _read_text(self, path: Path, encoding: str = "utf-8") -> str:
        return _read_file_text(path, encoding)

    def _read_binary(self, path: Path) -> bytes:
        return _read_file_bytes(path)