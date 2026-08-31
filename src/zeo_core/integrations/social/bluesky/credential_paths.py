"""Credential-location helpers for zeo_core's Bluesky integration.

This integration is greenfield (RULING-409 s6c: "integrations/ has no social
package -- GREENFIELD"), so unlike Google's `credential_paths.py` there is no
legacy CWD-relative default to migrate away from -- there was never a prior
release that could have written one. The defect RULING-407/408 fixed for
Google (a fresh directory's CWD silently becomes the credential's home) is
avoided here by construction: the *default* credentials path has always been
the platformdirs per-user location, same computation Google's fix landed on
(`platformdirs.user_config_dir("zeocore", appauthor=False)`), just under a
`bluesky/` subdirectory rather than reusing Google's two filenames.

The sandbox-escape fallback below (`write_json_with_fallback` and friends)
reuses the same pattern `google/credential_paths.py` established: the
platformdirs default is an absolute path outside the FileSystemService
singleton's CWD-anchored sandbox, so a direct `standalone.write_json` call
against it is rejected by the sandbox from most working directories, and a
directory-scoped `FileSystemService` (anchored at the credential's own
parent, not CWD) is required to actually write it. This is the same
established in-repo idiom, not a new invention -- RULING-237 s2.1 named this
exact class of gap for any out-of-sandbox credentials_file.
"""

from pathlib import Path
from typing import Any

import platformdirs

from zeo_core.core.fs.results import FileInfoResult, OperationResult
from zeo_core.core.fs.service import create_service, standalone
from zeo_core.core.fs.service.full_class import FileSystemService
from zeo_core.core.logging import get_logger

logger = get_logger(__name__)

CREDENTIALS_FILENAME = "bluesky_credentials.json"  # noqa: S105 -- a filename, not a credential value

_PATH_OUTSIDE_BASE_DIR = "path_outside_base_dir"

# One scoped FileSystemService per resolved parent directory, reused across
# calls in a process rather than rebuilt every time.
_scoped_service_cache: dict[str, FileSystemService] = {}


def _scoped_service(parent_dir: str) -> FileSystemService:
    """A FileSystemService anchored (sandboxed) to `parent_dir` itself, never
    to CWD. Not a sandbox bypass: a differently-anchored sandbox, exactly as
    narrow as the default CWD-anchored one, just rooted where the credential
    actually lives."""
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
    when `path` is outside the CWD sandbox (the platformdirs default
    normally is, from most working directories)."""
    result = standalone.get_file_info(path)
    if _is_sandbox_escape(result):
        result = _scoped_service(str(Path(path).parent)).get_file_info(Path(path).name)
    return result


def read_json_with_fallback(path: str) -> Any:  # noqa: ANN401 -- passthrough of standalone.read_json's DataResult[dict], typed loosely to avoid importing the generic result type just for this one signature
    result = standalone.read_json(path)
    if _is_sandbox_escape(result):
        result = _scoped_service(str(Path(path).parent)).read_json(Path(path).name)
    return result


def write_json_with_fallback(
    path: str, data: dict[str, Any], mode: int | None = None
) -> OperationResult:
    """Write `data` as JSON to `path`, atomically, falling back to a
    directory-scoped service when `path` is outside the CWD sandbox."""
    result = standalone.write_json(path, data, atomic=True, mode=mode)
    if _is_sandbox_escape(result):
        result = _scoped_service(str(Path(path).parent)).write_json(
            Path(path).name, data, atomic=True, mode=mode
        )
    return result


def create_directory_with_fallback(path: str, exist_ok: bool = True) -> OperationResult:
    result = standalone.create_directory(path, exist_ok=exist_ok)
    if _is_sandbox_escape(result):
        result = _scoped_service(str(Path(path).parent)).create_directory(
            Path(path).name, exist_ok=exist_ok
        )
    return result


def platformdirs_config_dir() -> str:
    """The OS-appropriate per-user config directory for zeocore's Bluesky
    credentials -- same root Google's fix uses
    (`platformdirs.user_config_dir("zeocore", appauthor=False)`), so every
    zeocore integration's credentials converge on one per-user home rather
    than each picking its own."""
    return platformdirs.user_config_dir("zeocore", appauthor=False)


def default_credentials_path() -> str:
    return str(Path(platformdirs_config_dir()) / "bluesky" / CREDENTIALS_FILENAME)


__all__ = [
    "CREDENTIALS_FILENAME",
    "create_directory_with_fallback",
    "default_credentials_path",
    "get_file_info_with_fallback",
    "platformdirs_config_dir",
    "read_json_with_fallback",
    "write_json_with_fallback",
]
