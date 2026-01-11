import mimetypes
from pathlib import Path

def _resolve_path(base_dir: Path, path: str | Path) -> Path:
    """
    Resolve a path relative to base_dir.
    WARNING: Does NOT check for sandboxing. Service layer must normalize first.
    This simply handles the mechanical join/resolve.
    """
    try:
        path_obj = Path(path)
        if path_obj.is_absolute():
            return path_obj.resolve()
        return (base_dir / path).resolve()
    except TypeError:
        return (base_dir / str(path)).resolve()

def _initialize_mime_types() -> None:
    mimetypes.init()