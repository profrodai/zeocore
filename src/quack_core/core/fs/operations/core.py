import mimetypes
from pathlib import Path

def _resolve_path(base_dir: Path, path: str | Path) -> Path:
    try:
        path_obj = Path(path)
        if path_obj.is_absolute():
            return path_obj
        return base_dir / path
    except TypeError:
        return base_dir / str(path)

def _initialize_mime_types() -> None:
    mimetypes.init()