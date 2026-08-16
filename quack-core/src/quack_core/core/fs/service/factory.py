# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/service/factory.py
# === QV-LLM:END ===


from pathlib import Path

from quack_core.core.fs.service.full_class import FileSystemService
from quack_core.core.logging import LOG_LEVELS, LogLevel


def create_service(
    base_dir: str | Path | None = None,
    log_level: int = LOG_LEVELS[LogLevel.INFO],
    unsafe_allow_absolute_paths: bool = False,  # ← MUST MATCH base.py __init__
) -> FileSystemService:
    """
    Factory to create a FileSystemService instance.

    Args:
        base_dir: Root directory for the service. Defaults to CWD.
        log_level: Logging verbosity.
        unsafe_allow_absolute_paths: If True, allows absolute paths outside base_dir (still blocks ../ escape).
                                ⚠️  WARNING: This is a TRUST BOUNDARY setting.
                                Permits absolute paths outside base_dir; the '..'
                                traversal escape check remains active. Only use in
                                trusted environments.
    """
    return FileSystemService(
        base_dir=base_dir,
        log_level=log_level,
        unsafe_allow_absolute_paths=unsafe_allow_absolute_paths,  # ← MUST MATCH
    )
