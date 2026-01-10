# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_internal/path_utils.py
# module: quack_core.core.fs._internal.path_utils
# role: module
# neighbors: __init__.py, checksums.py, common.py, comparison.py, disk.py, file_info.py (+4 more)
# git_branch: feat/9-make-setup-work
# git_commit: ccfbaeea
# === QV-LLM:END ===

"""
Legacy internal path utils. 
Most logic has moved to quack_core.core.fs.normalize.
This file now just delegates or holds low-level helpers if needed.
"""
from quack_core.core.fs.normalize import coerce_path_str as extract_str_impl

def _extract_path_str(obj):
    return extract_str_impl(obj)

def _normalize_path_param(obj):
    from pathlib import Path
    return Path(extract_str_impl(obj))