# === QV-LLM:BEGIN ===
# path: tests/conftest.py
# role: module
# neighbors: __init__.py
# git_branch: feat/9-make-setup-work
# git_commit: 1a3eba04
# === QV-LLM:END ===

"""
Root level test configuration for QuackVerse monorepo.
This sets up the Python path for tests across the entire monorepo.
"""

import sys
from pathlib import Path

# Add all src directories to Python path
REPO_ROOT = Path(__file__).parent
for package_dir in ["quack-core", "quack-chat", "quackster"]:
    src_dir = REPO_ROOT / package_dir / "src"
    if src_dir.exists() and src_dir not in sys.path:
        sys.path.insert(0, str(src_dir.parent))

# Print current path setup for debugging
print(f"Python path: {sys.path}")