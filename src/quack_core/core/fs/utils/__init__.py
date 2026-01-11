# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/utils/__init__.py
# module: quack_core.core.fs.utils.__init__
# role: utils
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

"""
DEPRECATED: Use quack_core.core.fs.api.public
"""
import warnings
from quack_core.core.fs.api.public import *

warnings.warn("quack_core.core.fs.utils is deprecated. Use quack_core.core.fs.api.public instead.", DeprecationWarning, stacklevel=2)