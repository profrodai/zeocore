# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/common/enums.py
# module: quack_core.contracts.common.enums
# role: module
# neighbors: __init__.py, ids.py, time.py, typing.py, versions.py
# exports: CapabilityStatus, LogLevel, ArtifactKind, StorageScheme, ChecksumAlgorithm
# git_branch: refactor/toolkitWorkflow
# git_commit: de0fa70
# === QV-LLM:END ===

"""
Shared enumerations used across contracts.

These enums define controlled vocabularies for status codes,
artifact types, and other categorical values.
"""

from enum import Enum


class CapabilityStatus(str, Enum):
    """
    Status of a capability execution.

    Used in CapabilityResult to enable machine branching in orchestrators.
    """
    success = "success"  # Capability completed successfully
    skipped = "skipped"  # Capability was intentionally skipped (policy decision)
    error = "error"  # Capability failed with an error


class LogLevel(str, Enum):
    """
    Severity level for log events.

    Used in structured logging for audit trails.
    """
    DEBUG = "DEBUG"  # Detailed debug information
    INFO = "INFO"  # General informational messages
    WARN = "WARN"  # Warning messages (non-critical issues)
    ERROR = "ERROR"  # Error messages (critical failures)


class ArtifactKind(str, Enum):
    """
    Classification of artifact purpose in the workflow.

    Used by orchestrators to decide retention, routing, and visibility:
    - intermediate: Temporary artifacts, may be cleaned up
    - final: End-user deliverables, must be preserved
    - debug: Diagnostic artifacts, optional retention
    - report: Summary/analysis artifacts
    """
    intermediate = "intermediate"
    final = "final"
    debug = "debug"
    report = "report"


class StorageScheme(str, Enum):
    """
    Storage backend type for artifacts.

    Core schemes are well-known and blessed.
    For custom backends, use 'custom' and specify the scheme in StorageRef.scheme_custom.
    """
    # Core schemes (always supported)
    local = "local"  # Local filesystem
    http = "http"  # HTTP URL (commonly used for read-only access)
    https = "https"  # HTTPS URL (commonly used for read-only access)
    s3 = "s3"  # AWS S3
    gcs = "gcs"  # Google Cloud Storage
    azure = "azure"  # Azure Blob Storage

    # Nice-to-have schemes (reference only, implementation optional)
    drive = "drive"  # Google Drive
    ftp = "ftp"  # FTP server

    # Extensibility
    custom = "custom"  # For custom storage backends (specify in scheme_custom)


class ChecksumAlgorithm(str, Enum):
    """
    Checksum algorithm for artifact integrity.

    SHA256 is the only blessed algorithm. For custom algorithms,
    use the 'custom' value and specify the algorithm name in metadata.
    """
    sha256 = "sha256"
    custom = "custom"  # For future extensibility