from pathlib import Path
from quack_core.fs.service.full_class import FileSystemService
from quack_core.lib.logging import LOG_LEVELS, LogLevel

def create_service(
    base_dir: str | Path | None = None,
    log_level: int = LOG_LEVELS[LogLevel.INFO],
) -> FileSystemService:
    return FileSystemService(base_dir=base_dir, log_level=log_level)