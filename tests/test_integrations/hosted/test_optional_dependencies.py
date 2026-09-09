"""Remote/fake profiles must not require local provider SDKs."""

import os
import subprocess
import sys
from pathlib import Path


def test_fake_example_without_local_provider_sdks(tmp_path: Path) -> None:
    example = Path(__file__).resolve().parents[3] / "examples/zeoconnect_usage.py"
    script = """
import importlib.abc
import runpy
import sys

class NoGoogleSDK(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        blocked = {'google', 'googleapiclient', 'google_auth_oauthlib', 'requests'}
        if fullname.split('.')[0] in blocked:
            raise ModuleNotFoundError('optional Google SDK disabled')

sys.meta_path.insert(0, NoGoogleSDK())
for name in ('google.auth', 'requests'):
    try:
        __import__(name)
    except ModuleNotFoundError:
        pass
    else:
        raise AssertionError('SDK blocker positive control failed')
runpy.run_path(sys.argv[1], run_name='__main__')
"""
    result = subprocess.run(  # noqa: S603 - repository-owned example and fixed fixture
        [sys.executable, "-c", script, str(example)],
        cwd=tmp_path,
        env={"HOME": str(tmp_path), "PATH": os.environ.get("PATH", "")},
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert (
        result.stdout
        == "FAKE: selected Drive bytes verified; no credential or network\n"
    )
