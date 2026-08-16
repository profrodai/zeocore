# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_paths/conftest.py
# === QV-LLM:END ===

"""
Fixtures scoped to test_paths/.

quack_core.core.paths._internal (resolver.py, utils.py) drives its marker-file /
marker-dir detection entirely through quack_core.core.fs.service.standalone.join_path,
in addition to normalize_path (already mocked, out-of-sandbox, in the root conftest).
The root conftest's autouse mocks only cover normalize_path; join_path was left on its
real, sandboxed implementation, which rejects any path outside the FS service's
base_dir (CWD) - which every pytest `tmp_path` and `mock_project_structure` fixture is.
That silently broke every _find_project_root / _find_nearest_directory / marker-lookup
call in this suite (paths that DO exist on disk were reported not-found because
join_path never got past the sandbox check to look).

This fixture extends the same "avoid filesystem/sandbox friction in tests" intent the
root conftest's mock_fs_standalone/mock_normalize_path already state, scoped to this
directory only so it cannot change behavior for suites outside test_paths/.
"""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from quack_core.core.fs import DataResult, OperationResult


@pytest.fixture(autouse=True)
def mock_paths_join_path():
    """Bypass the fs-service sandbox for join_path within test_paths/.

    Mirrors the real join_path contract (DataResult with ok/path/data) but performs
    a plain os.path join instead of routing through the sandboxed base_dir check, so
    marker-file/marker-dir lookups against pytest's tmp_path (which lives outside the
    repo's CWD-derived base_dir) actually reach the filesystem instead of being
    rejected before they are ever checked.
    """
    with patch(
        "quack_core.core.fs.service.standalone.join_path"
    ) as mock_join:

        def _mock_join(*parts: Any) -> DataResult[str]:
            if not parts:
                p = Path(".")
                return DataResult(ok=True, path=p, data=".", format="path")
            str_parts = [str(p) for p in parts]
            base = str_parts[0]
            others = [p.lstrip("/\\") for p in str_parts[1:]]
            joined = str(Path(base).joinpath(*others))
            return DataResult(ok=True, path=Path(joined), data=joined, format="path")

        mock_join.side_effect = _mock_join
        yield


@pytest.fixture(autouse=True)
def mock_paths_create_directory():
    """Bypass the fs-service sandbox for create_directory within test_paths/.

    _find_output_directory(create=True) (resolver.py) creates the output dir via
    standalone.create_directory, which is sandboxed the same way join_path/
    normalize_path are - out-of-base_dir paths (every pytest tmp_path) are rejected
    before anything is written to disk. Same rationale as mock_paths_join_path.
    """
    with patch(
        "quack_core.core.fs.service.standalone.create_directory"
    ) as mock_create:

        def _mock_create(path: Any, exist_ok: bool = True) -> OperationResult:
            p = Path(str(path))
            p.mkdir(parents=True, exist_ok=exist_ok)
            return OperationResult(ok=True, path=p, message="Created directory")

        mock_create.side_effect = _mock_create
        yield
