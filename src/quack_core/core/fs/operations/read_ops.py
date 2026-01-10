from pathlib import Path

class ReadOperationsMixin:
    def _resolve_path(self, path: str | Path) -> Path:
        raise NotImplementedError

    def _read_text(self, path: str | Path, encoding: str = "utf-8") -> str:
        resolved = self._resolve_path(path)
        with open(resolved, "r", encoding=encoding) as f:
            return f.read()

    def _read_binary(self, path: str | Path) -> bytes:
        resolved = self._resolve_path(path)
        with open(resolved, "rb") as f:
            return f.read()