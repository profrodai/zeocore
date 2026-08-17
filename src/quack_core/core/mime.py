
"""
MIME type and binary detection utilities.

Fix #4: Centralized binary extension list for consistency and testability.
Single source of truth for "is this file binary?" logic.
"""

# Binary extensions (non-UTF8-safe files) - Fix #4: Centralized constant
# This is the canonical list used throughout QuackCore
BINARY_EXTENSIONS: set[str] = {
    # Archives
    "bin",
    "zip",
    "tar",
    "gz",
    "bz2",
    "xz",
    "7z",
    "rar",
    # Documents
    "pdf",
    "docx",
    "xlsx",
    "pptx",
    # Images (raster/binary - SVG is text/XML, not here)
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp",
    "bmp",
    "tiff",
    "tif",
    "ico",
    # Audio/Video
    "mp3",
    "wav",
    "ogg",
    "flac",
    "aac",
    "m4a",
    "mp4",
    "avi",
    "mkv",
    "webm",
    "mov",
    "flv",
    "wmv",
    # Data formats
    "parquet",
    "feather",
    "arrow",
    "avro",
    "pickle",
    "pkl",
    # Compiled/Executable
    "exe",
    "dll",
    "so",
    "dylib",
    "wasm",
    "pyc",
    # Other
    "ttf",
    "otf",
    "woff",
    "woff2",  # Fonts
}

# Text extensions (UTF8-safe files) - for explicit checking
TEXT_EXTENSIONS: set[str] = {
    # Plain text
    "txt",
    "text",
    "log",
    # Markup
    "html",
    "htm",
    "xml",
    "svg",
    # Data formats
    "json",
    "yaml",
    "yml",
    "toml",
    "ini",
    "cfg",
    "conf",
    "csv",
    "tsv",
    # Code
    "py",
    "js",
    "ts",
    "jsx",
    "tsx",
    "java",
    "c",
    "cpp",
    "h",
    "hpp",
    "rs",
    "go",
    "rb",
    "php",
    "swift",
    "kt",
    "scala",
    # Markdown/Docs
    "md",
    "markdown",
    "rst",
    "adoc",
    "tex",
    # Shell/Config
    "sh",
    "bash",
    "zsh",
    "fish",
    "ps1",
    "bat",
    "cmd",
    # Other
    "css",
    "scss",
    "sass",
    "less",
    "sql",
    "graphql",
    "proto",
}


def is_binary_extension(extension: str) -> bool:
    """
    Check if file extension indicates binary content.

    Fix #4: Centralized binary detection logic.

    Args:
        extension: File extension (with or without leading dot)

    Returns:
        True if extension indicates binary file

    Examples:
        >>> is_binary_extension(".pdf")
        True

        >>> is_binary_extension("png")
        True

        >>> is_binary_extension(".txt")
        False

        >>> is_binary_extension("svg")
        False  # SVG is text/XML
    """
    # Normalize: lowercase, remove leading dot
    normalized = extension.lower().lstrip(".")
    return normalized in BINARY_EXTENSIONS


def get_content_type(extension: str) -> str:
    """
    Get MIME type from file extension.

    Args:
        extension: File extension (with or without leading dot)

    Returns:
        MIME type string

    Examples:
        >>> get_content_type(".json")
        'application/json'

        >>> get_content_type("png")
        'image/png'

        >>> get_content_type(".unknown")
        'application/octet-stream'
    """
    # Normalize extension
    ext = extension.lower().lstrip(".")

    # Common MIME types
    type_map = {
        # Text
        "txt": "text/plain",
        "html": "text/html",
        "htm": "text/html",
        "css": "text/css",
        "csv": "text/csv",
        "md": "text/markdown",
        "xml": "application/xml",
        "svg": "image/svg+xml",
        # Data
        "json": "application/json",
        "yaml": "application/x-yaml",
        "yml": "application/x-yaml",
        "toml": "application/toml",
        # Documents
        "pdf": "application/pdf",
        "docx": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pptx": (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ),
        # Images
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "tif": "image/tiff",
        "ico": "image/x-icon",
        # Audio/Video
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "mp4": "video/mp4",
        "webm": "video/webm",
        "avi": "video/x-msvideo",
        # Archives
        "zip": "application/zip",
        "tar": "application/x-tar",
        "gz": "application/gzip",
        "7z": "application/x-7z-compressed",
        "rar": "application/vnd.rar",
        # Binary
        "bin": "application/octet-stream",
        "exe": "application/x-msdownload",
        "dll": "application/x-msdownload",
        "so": "application/x-sharedlib",
        "wasm": "application/wasm",
    }

    return type_map.get(ext, "application/octet-stream")


def is_text_extension(extension: str) -> bool:
    """
    Check if file extension indicates text content.

    Args:
        extension: File extension (with or without leading dot)

    Returns:
        True if extension indicates text file

    Note:
        This is NOT just "not binary" - some extensions may be unknown.
        For explicit text checking, use this. For binary detection, use
        is_binary_extension().
    """
    normalized = extension.lower().lstrip(".")
    return normalized in TEXT_EXTENSIONS
