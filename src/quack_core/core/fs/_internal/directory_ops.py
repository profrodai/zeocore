from dataclasses import dataclass
from pathlib import Path


@dataclass
class DirectoryScanStats:
    files: list[Path]
    directories: list[Path]
    total_size: int


def _ensure_directory(path: Path, exist_ok: bool = True) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=exist_ok)
        return path
    except FileExistsError as e:
        raise FileExistsError(f"Directory already exists: {path}") from e
    except PermissionError as e:
        raise PermissionError(f"Permission denied creating directory: {path}") from e
    except Exception as e:
        raise OSError(f"Failed to create directory: {e}") from e


def _scan_directory(
    path: Path,
    pattern: str | None = None,
    recursive: bool = False,
    include_hidden: bool = False,
) -> DirectoryScanStats:
    if not path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")

    files = []
    directories = []
    total_size = 0

    # Choose iterator based on recursion
    iterator = path.rglob("*") if recursive else path.iterdir()

    for item in iterator:
        # Handle hidden files
        if not include_hidden and item.name.startswith("."):
            continue

        # Handle pattern matching (fnmatch style)
        if pattern and not item.match(pattern):
            continue

        if item.is_file():
            files.append(item)
            try:
                total_size += item.stat().st_size
            except OSError:
                pass
        elif item.is_dir():
            directories.append(item)

    return DirectoryScanStats(
        files=files, directories=directories, total_size=total_size
    )
