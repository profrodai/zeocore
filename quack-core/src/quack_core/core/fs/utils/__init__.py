# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/utils/__init__.py
# module: quack_core.core.fs.utils.__init__
# role: utils
# git_branch: main
# git_commit: f0715f0c
# === QV-LLM:END ===

"""
DEPRECATED: Use quack_core.core.fs.service.standalone for utility functions.
"""
import warnings

from quack_core.core.fs.service.standalone import *

warnings.warn("quack_core.core.fs.utils is deprecated. Use quack_core.core.fs.service.standalone instead.", DeprecationWarning, stacklevel=2)
