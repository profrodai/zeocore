# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/__init__.py
# module: quack_core.core.fs.api.__init__
# role: api
# git_branch: feat/9-make-setup-work
# git_commit: 8234fdcd
# === QV-LLM:END ===

"""
DEPRECATED: Use quack_core.core.fs.service.standalone for utility functions.
"""
import warnings
from quack_core.core.fs.service.standalone import *

warnings.warn("quack_core.core.fs.api is deprecated. Use quack_core.core.fs.service or quack_core.core.fs.service.standalone instead.", DeprecationWarning, stacklevel=2)