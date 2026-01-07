# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/common/ids.py
# module: quack_core.contracts.common.ids
# role: module
# neighbors: __init__.py, enums.py, time.py, typing.py, versions.py
# exports: generate_run_id, generate_artifact_id, is_valid_uuid
# git_branch: feat/9-make-setup-work
# git_commit: c28ab838
# === QV-LLM:END ===

"""
ID generation utilities for contracts.

Provides standardized UUID generation for run IDs and artifact IDs.
No external dependencies beyond stdlib.
"""

import uuid
from typing import NewType

# Type aliases for clarity
RunID = NewType("RunID", str)
ArtifactID = NewType("ArtifactID", str)


def generate_run_id() -> str:
    """
    Generate a unique run identifier.

    Returns:
        UUID4 string suitable for tracking a single tool execution

    Example:
        >>> run_id = generate_run_id()
        >>> len(run_id)
        36
    """
    return str(uuid.uuid4())


def generate_artifact_id() -> str:
    """
    Generate a unique artifact identifier.

    Returns:
        UUID4 string suitable for tracking a single artifact across storage systems

    Example:
        >>> artifact_id = generate_artifact_id()
        >>> len(artifact_id)
        36
    """
    return str(uuid.uuid4())


def is_valid_uuid(value: str) -> bool:
    """
    Validate that a string is a properly formatted UUID.

    Args:
        value: String to validate

    Returns:
        True if value is a valid UUID format

    Example:
        >>> is_valid_uuid("550e8400-e29b-41d4-a716-446655440000")
        True
        >>> is_valid_uuid("not-a-uuid")
        False
    """
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False
