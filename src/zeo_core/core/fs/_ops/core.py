import mimetypes


def _initialize_mime_types() -> None:
    mimetypes.init()
