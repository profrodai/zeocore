"""
Credential-location migration for zeo_core's Google integrations.

RULING-407/408 (zeocore org corpus, 2026-08-31): the pre-migration default
(`config/google_credentials.json`, `config/google_client_secret.json`) resolves
CWD-relative -- from a fresh directory with no repo, authorizing Google writes a
live OAuth token into whatever folder the caller happened to be standing in,
created silently by `makedirs(exist_ok=True)`. RULING-407 ruled the root defect
is the LOCATION and that the failure mode is SILENCE; RULING-408 (DESIGN-01
approach C) ruled the fix: a `platformdirs`-computed per-user destination, an
EXPLICIT one-shot migration (never silent), and refuse-and-instruct -- never
guess -- when a token exists at both the old and new locations with differing
contents.

This module owns exactly that: computing the new default paths and performing
the one-shot migration. It does NOT perform credential file I/O for normal
auth flows -- that stays GoogleAuthProvider's job (auth.py), using the
sandbox-fallback helpers below only because the new default is an absolute
path outside the FileSystemService singleton's CWD-anchored sandbox.
"""

from pathlib import Path
from typing import Any

import platformdirs

from zeo_core.core.fs.results import DataResult, FileInfoResult, OperationResult
from zeo_core.core.fs.service import create_service, standalone
from zeo_core.core.fs.service.full_class import FileSystemService
from zeo_core.core.logging import get_logger

logger = get_logger(__name__)

# The two filenames GoogleConfigProvider.get_default_config() has always used.
# Migration only ever touches these two -- never a user-supplied custom path.
CREDENTIALS_FILENAME = "google_credentials.json"
CLIENT_SECRET_FILENAME = "google_client_secret.json"  # noqa: S105 -- a filename, not a credential value

_PATH_OUTSIDE_BASE_DIR = "path_outside_base_dir"

# One scoped FileSystemService per resolved parent directory, reused across
# calls in a process rather than rebuilt every time -- construction is cheap
# but there is no reason to pay it twice for the same directory.
_scoped_service_cache: dict[str, FileSystemService] = {}


def _scoped_service(parent_dir: str) -> FileSystemService:
    """
    A FileSystemService anchored (sandboxed) to `parent_dir` itself, never to
    CWD and never with unsafe_allow_absolute_paths. This is NOT a sandbox
    bypass: it is a differently-anchored sandbox, exactly as narrow as the
    default CWD-anchored one, just rooted where the credential actually
    lives. RULING-237 s2.1 (quackverse, sibling fork) named this same class
    of gap for an out-of-sandbox credentials_file and left the exact shape to
    the implementer; this is that shape for zeocore.
    """
    svc = _scoped_service_cache.get(parent_dir)
    if svc is None:
        svc = create_service(base_dir=parent_dir)
        _scoped_service_cache[parent_dir] = svc
    return svc


def _is_sandbox_escape(result: OperationResult) -> bool:
    return bool(
        result.error_info is not None
        and result.error_info.type == _PATH_OUTSIDE_BASE_DIR
    )


def get_file_info_with_fallback(path: str) -> FileInfoResult:
    """standalone.get_file_info, falling back to a directory-scoped service
    when `path` is outside the CWD sandbox (the new platformdirs default
    always is, from most working directories)."""
    result = standalone.get_file_info(path)
    if _is_sandbox_escape(result):
        result = _scoped_service(str(Path(path).parent)).get_file_info(Path(path).name)
    return result


def read_json_with_fallback(path: str) -> DataResult[dict[str, Any]]:
    result = standalone.read_json(path)
    if _is_sandbox_escape(result):
        result = _scoped_service(str(Path(path).parent)).read_json(Path(path).name)
    return result


def write_json_with_fallback(
    path: str, data: dict[str, Any], mode: int | None = None
) -> OperationResult:
    result = standalone.write_json(path, data, mode=mode)
    if _is_sandbox_escape(result):
        result = _scoped_service(str(Path(path).parent)).write_json(
            Path(path).name, data, mode=mode
        )
    return result


def parent_directory_with_fallback(path: str) -> str | None:
    """
    The directory containing `path`, computed the same way the pre-migration
    code did (standalone.split_path, joining every component but the last)
    for any path the CWD sandbox accepts -- so an existing mock of
    standalone.split_path/join_path in a caller's test still governs
    unchanged. Only when split_path itself reports a genuine
    path_outside_base_dir escape does this fall back to a plain
    pathlib.Path(path).parent computation, which needs no sandboxed
    normalization at all. Returns None on any OTHER split_path failure
    (preserving the original "real failure" contract), or the computed
    directory string otherwise. A path with no directory component (a bare
    filename) returns "" as split_path's own contract already did.
    """
    split_result = standalone.split_path(path)
    if split_result.success and split_result.data is not None:
        components = split_result.data[:-1]
        return str(Path(*components)) if components else ""

    if _is_sandbox_escape(split_result):
        parent = Path(path).parent
        return str(parent) if str(parent) not in ("", ".") else ""

    return None


def create_directory_with_fallback(path: str, exist_ok: bool = True) -> OperationResult:
    result = standalone.create_directory(path, exist_ok=exist_ok)
    if _is_sandbox_escape(result):
        # The directory itself is the anchor here -- scope the service to
        # its parent so "create this directory" is a relative op inside it.
        result = _scoped_service(str(Path(path).parent)).create_directory(
            Path(path).name, exist_ok=exist_ok
        )
    return result


def platformdirs_config_dir() -> str:
    """The OS-appropriate per-user config directory for zeocore's Google
    credentials, per RULING-408's adoption of DESIGN-01 approach C."""
    return platformdirs.user_config_dir("zeocore", appauthor=False)


def default_credentials_path() -> str:
    return str(Path(platformdirs_config_dir()) / CREDENTIALS_FILENAME)


def default_client_secret_path() -> str:
    return str(Path(platformdirs_config_dir()) / CLIENT_SECRET_FILENAME)


# The two legacy, CWD-relative locations this migration reads from and never
# writes to again once migrated.
LEGACY_CREDENTIALS_PATH = f"config/{CREDENTIALS_FILENAME}"
LEGACY_CLIENT_SECRET_PATH = f"config/{CLIENT_SECRET_FILENAME}"


class CredentialMigrationAmbiguousError(Exception):
    """Raised when a credential exists at BOTH the legacy and the new
    location with DIFFERING contents. RULING-408 defined this case
    explicitly: refuse-and-instruct, never guess, never merge, never pick
    the newer file. Carries the two paths so the caller can print both."""

    def __init__(self, legacy_path: str, new_path: str) -> None:
        self.legacy_path = legacy_path
        self.new_path = new_path
        super().__init__(
            f"A credential exists at both {legacy_path!r} and {new_path!r} "
            "with differing contents. Refusing to guess which is current."
        )


def _read_json_if_present(path: str) -> dict[str, Any] | None:
    info = get_file_info_with_fallback(path)
    if not info.success or not info.exists:
        return None
    result = read_json_with_fallback(path)
    if not result.success or result.data is None:
        return None
    return result.data


def migrate_one_shot(
    legacy_path: str, new_path: str, *, label: str, notice: bool = True
) -> str:
    """
    The one-shot, EXPLICIT migration RULING-408 ruled for: if a credential
    exists ONLY at the legacy CWD-relative location, move it (by writing to
    the new location) and print a notice -- silence is the defect this
    migration exists to close, so it must never move a live credential
    without saying so. If a credential exists at BOTH locations with
    IDENTICAL contents, the new location wins with no action needed (already
    migrated). If contents DIFFER, refuse and instruct
    (CredentialMigrationAmbiguousError) rather than guess.

    Returns the path callers should use: always `new_path`, since this
    function's contract is "the new location is authoritative after this
    call returns" -- it either already was, or this call just made it so.

    RULING-408 left permanence undecided with a stated default of one-shot;
    this is that default. The legacy file is left in place (not deleted) --
    deleting a user's only copy of a live credential on a best-effort
    migration is a strictly worse failure mode than leaving a stale copy
    behind, and is not what "one-shot" was ruled to mean.
    """
    legacy_data = _read_json_if_present(legacy_path)
    new_data = _read_json_if_present(new_path)

    if legacy_data is None:
        # Nothing to migrate -- either already migrated, or never existed.
        return new_path

    if new_data is not None:
        if legacy_data != new_data:
            raise CredentialMigrationAmbiguousError(legacy_path, new_path)
        # Identical at both locations: already migrated, nothing to do.
        return new_path

    # Legacy exists, new does not: perform the move, explicitly.
    parent = str(Path(new_path).parent)
    mkdir_result = create_directory_with_fallback(parent, exist_ok=True)
    if not mkdir_result.success:
        logger.error(
            f"Could not create {label} destination directory {parent}: "
            f"{mkdir_result.error}"
        )
        return legacy_path

    write_result = write_json_with_fallback(new_path, legacy_data, mode=0o600)
    if not write_result.success:
        logger.error(f"Could not migrate {label} to {new_path}: {write_result.error}")
        return legacy_path

    if notice:
        print(
            f"[zeocore] Migrated {label} from {legacy_path!r} (old, "
            f"CWD-relative default) to {new_path!r} (new, per-user default). "
            f"The old file was left in place; the new location is now "
            "authoritative. See RULING-408 for why this moved."
        )
    return new_path


def resolve_credentials_path(explicit: str | None = None) -> str:
    """Entry point GoogleConfigProvider/GoogleAuthProvider callers use to get
    the credentials_file path that should actually be used: an explicitly
    passed path is honored unchanged (never migrated -- migration only
    applies to the DEFAULT), otherwise the one-shot migration runs against
    the two well-known locations and the (now authoritative) new path is
    returned."""
    if explicit is not None:
        return explicit
    return migrate_one_shot(
        LEGACY_CREDENTIALS_PATH,
        default_credentials_path(),
        label="Google OAuth credentials",
    )


def resolve_client_secret_path(explicit: str | None = None) -> str:
    if explicit is not None:
        return explicit
    return migrate_one_shot(
        LEGACY_CLIENT_SECRET_PATH,
        default_client_secret_path(),
        label="Google OAuth client secret",
    )


__all__ = [
    "CredentialMigrationAmbiguousError",
    "create_directory_with_fallback",
    "default_client_secret_path",
    "default_credentials_path",
    "get_file_info_with_fallback",
    "migrate_one_shot",
    "platformdirs_config_dir",
    "read_json_with_fallback",
    "resolve_client_secret_path",
    "resolve_credentials_path",
    "write_json_with_fallback",
]
