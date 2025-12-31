# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/integrations/google/drive/utils/query.py
# module: quack_core.integrations.google.drive.utils.query
# role: utils
# neighbors: __init__.py, api.py
# exports: build_query, build_file_fields
# git_branch: refactor/toolkitWorkflow
# git_commit: 223dfb0
# === QV-LLM:END ===

"""
Query utilities for Google Drive integration.

This module provides functions for building query strings for
Google Drive API requests.
"""


def build_query(folder_id: str | None = None, pattern: str | None = None) -> str:
    """
    Build a query string for listing files in Google Drive.

    Args:
        folder_id: Optional folder ID to list files from.
        pattern: Optional filename pattern to filter results.

    Returns:
        str: The query string.
    """
    query_parts: list[str] = []

    # Filter by parent folder
    if folder_id:
        query_parts.append(f"'{folder_id}' in parents")

    # Exclude trashed files
    query_parts.append("trashed = false")

    # Filter by name pattern
    if pattern:
        if "*" in pattern:
            # Handle wildcards in the pattern
            name_pattern = pattern.replace("*", "")
            if name_pattern:
                if "*" in pattern and pattern != "*":
                    # Extract the part before the asterisk if it exists
                    if pattern.startswith("*") and pattern.endswith("*"):
                        # *text* pattern
                        clean_pattern = pattern.strip("*")
                        query_parts.append(f"name contains '{clean_pattern}'")
                    elif pattern.startswith("*"):
                        # *text pattern (ends with)
                        clean_pattern = pattern[1:]
                        query_parts.append(f"name contains '{clean_pattern}'")
                    elif pattern.endswith("*"):
                        # text* pattern (starts with)
                        clean_pattern = pattern[:-1]
                        query_parts.append(f"name contains '{clean_pattern}'")
                    else:
                        # Handle pattern with * in the middle
                        parts = pattern.split("*")
                        # Use the first part as the filter
                        query_parts.append(f"name contains '{parts[0]}'")
                else:
                    # Empty wildcard (*)
                    query_parts.append("name contains ''")
            else:
                # Empty wildcard (*)
                query_parts.append("name contains ''")
        else:
            # Exact match
            query_parts.append(f"name = '{pattern}'")

    return " and ".join(query_parts)


def build_file_fields(include_permissions: bool = False) -> str:
    """
    Build a fields parameter string for file requests.

    Args:
        include_permissions: Whether to include permission details.

    Returns:
        str: The fields parameter string.
    """
    fields = [
        "id",
        "name",
        "mimeType",
        "webViewLink",
        "webContentLink",
        "size",
        "createdTime",
        "modifiedTime",
        "parents",
        "shared",
        "trashed",
    ]

    if include_permissions:
        fields.append("permissions(id,type,role,emailAddress,domain)")

    return f"files({', '.join(fields)})"
