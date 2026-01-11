import mimetypes
from pathlib import Path

def _initialize_mime_types() -> None:
    mimetypes.init()