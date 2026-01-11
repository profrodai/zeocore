# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/common/typing.py
# module: quack_core.contracts.common.typing
# role: module
# neighbors: __init__.py, enums.py, ids.py, time.py, versions.py
# git_branch: feat/9-make-setup-work
# git_commit: 227c3fdd
# === QV-LLM:END ===

"""
Type aliases and typing utilities for contracts.

Provides semantic type hints without runtime overhead.
"""

from typing import Any, NewType

# Metadata dictionaries (free-form key-value pairs)
Metadata = dict[str, Any]

# Error code type (should follow QC_* convention)
ErrorCode = NewType("ErrorCode", str)

# Role identifier for artifacts (stable semantic names)
ArtifactRole = NewType("ArtifactRole", str)
