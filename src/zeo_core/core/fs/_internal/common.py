from pathlib import Path


def _get_extension(path: Path) -> str:
    # Doctrine: _internal receives strict Paths, no strings.
    filename = path.name
    if filename.startswith(".") and "." not in filename[1:]:
        return filename[1:]
    return path.suffix.lstrip(".")
