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
