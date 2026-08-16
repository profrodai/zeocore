# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_ops/core.py
# === QV-LLM:END ===

import mimetypes


def _initialize_mime_types() -> None:
    mimetypes.init()
