# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/api/public/__init__.py
# module: quack_core.core.fs.api.public.__init__
# role: api
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

"""
DEPRECATED: Use quack_core.core.fs.service.standalone for utility functions.
This module is kept for backward compatibility but now delegates to the service.
"""
from quack_core.core.fs.service.standalone import *