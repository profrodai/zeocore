# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/common/versions.py
# module: quack_core.contracts.common.versions
# role: module
# neighbors: __init__.py, enums.py, ids.py, time.py, typing.py
# git_branch: feat/9-make-setup-work
# git_commit: 8234fdcd
# === QV-LLM:END ===

"""
Version constants for contracts module.

These versions follow semantic versioning and are embedded in manifests
and API responses to enable version-aware parsing.
"""

# Overall contracts module version
CONTRACTS_VERSION = "1.0.0"

# Specific schema versions
MANIFEST_VERSION = "1.0"
ARTIFACT_SCHEMA_VERSION = "1.0"
ENVELOPE_VERSION = "1.0"
