# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/utils/__init__.py
# module: quack_core.core.fs.utils.__init__
# role: utils
# git_branch: feat/9-make-setup-work
# git_commit: 26dbe353
# === QV-LLM:END ===

"""
LEGACY MODULE - DEPRECATED
"""
import warnings

# Explicitly re-export only what was likely used to maintain minimal back-compat
# if absolutely necessary, but strictly warn.
from quack_core.core.fs.api.public import (
    atomic_write,
    compute_checksum,
    ensure_directory,
    expand_user_vars,
    extract_path_str,
    normalize_path,
)

warnings.warn(
    "quack_core.core.fs.utils is deprecated. Use quack_core.core.fs.api.public instead.",
    DeprecationWarning,
    stacklevel=2
)