
from pathlib import Path
from quack_core.core.fs.service.full_class import FileSystemService
from quack_core.core.logging import LOG_LEVELS, LogLevel


def create_service(
        base_dir: str | Path | None = None,
        log_level: int = LOG_LEVELS[LogLevel.INFO],
        unsafe_disable_sandbox: bool = False,  # ← MUST MATCH base.py __init__
) -> FileSystemService:
    """
    Factory to create a FileSystemService instance.

    Args:
        base_dir: Root directory for the service. Defaults to CWD.
        log_level: Logging verbosity.
        unsafe_disable_sandbox: If True, disables ALL filesystem sandboxing.
                                ⚠️  WARNING: This is a TRUST BOUNDARY setting.
                                Allows operations outside base_dir and disables
                                path safety checks. Only use in trusted environments.
    """
    return FileSystemService(
        base_dir=base_dir,
        log_level=log_level,
        unsafe_disable_sandbox=unsafe_disable_sandbox  # ← MUST MATCH
    )