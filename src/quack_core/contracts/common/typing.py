# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/common/typing.py
# module: quack_core.contracts.common.typing
# role: module
# neighbors: __init__.py, enums.py, ids.py, time.py, versions.py
# git_branch: refactor/toolkitWorkflow
# git_commit: 21a4e25
# === QV-LLM:END ===

"""
Type aliases and typing utilities for contracts.

Provides semantic type hints without runtime overhead.
"""

from typing import Dict, Any, NewType

# Metadata dictionaries (free-form key-value pairs)
Metadata = Dict[str, Any]

# Error code type (should follow QC_* convention)
ErrorCode = NewType("ErrorCode", str)

# Role identifier for artifacts (stable semantic names)
ArtifactRole = NewType("ArtifactRole", str)