"""
Type aliases and typing utilities for contracts.

Provides semantic type hints without runtime overhead.
"""

from typing import Any, NewType

# Metadata dictionaries (free-form key-value pairs)
Metadata = dict[str, Any]

# Error code type (should follow ZEO_* convention; ZC_/legacy QC_ also
# accepted by CapabilityResult/CapabilityError's validators)
ErrorCode = NewType("ErrorCode", str)

# Role identifier for artifacts (stable semantic names)
ArtifactRole = NewType("ArtifactRole", str)
