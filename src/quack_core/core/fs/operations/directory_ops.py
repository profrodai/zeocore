from pathlib import Path
from dataclasses import dataclass

@dataclass
class DirectoryInfo:
    path: Path
    files: list[Path]
    directories: list[Path]
    total_size: int
    is_empty: bool
    total_files: int
    total_directories: int

class DirectoryOperationsMixin:
    def _resolve_path(self, path: str | Path) -> Path:
        raise NotImplementedError

    def _list_directory(self, path: str | Path, pattern: str | None = None, include_hidden: bool = False) -> DirectoryInfo:
        resolved = self._resolve_path(path)
        if not resolved.exists(): raise FileNotFoundError(f"Directory not found: {resolved}")
        if not resolved.is_dir(): raise NotADirectoryError(f"Not a directory: {resolved}")

        files = []
        directories = []
        total_size = 0

        for item in resolved.iterdir():
            if not include_hidden and item.name.startswith('.'): continue
            if pattern and not item.match(pattern): continue

            if item.is_file():
                files.append(item)
                try: total_size += item.stat().st_size
                except OSError: pass
            elif item.is_dir():
                directories.append(item)

        return DirectoryInfo(
            path=resolved, files=files, directories=directories, total_size=total_size,
            is_empty=(len(files) == 0 and len(directories) == 0),
            total_files=len(files), total_directories=len(directories)
        )