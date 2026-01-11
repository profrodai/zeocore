from pathlib import Path

class ReadOperationsMixin:
    def _read_text(self, path: Path, encoding: str = "utf-8") -> str:
        with open(path, "r", encoding=encoding) as f:
            return f.read()

    def _read_binary(self, path: Path) -> bytes:
        with open(path, "rb") as f:
            return f.read()