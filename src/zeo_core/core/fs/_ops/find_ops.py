from pathlib import Path


class FindOperationsMixin:
    def _find_files(
        self,
        path: Path,
        pattern: str,
        recursive: bool = True,
        include_hidden: bool = False,
    ) -> tuple[list[Path], list[Path]]:
        if not path.exists() or not path.is_dir():
            raise NotADirectoryError(f"Invalid search directory: {path}")

        files: list[Path] = []
        directories: list[Path] = []
        iterator = path.rglob(pattern) if recursive else path.glob(pattern)

        for item in iterator:
            if not include_hidden and item.name.startswith("."):
                continue
            try:
                if item.is_file():
                    files.append(item)
                elif item.is_dir():
                    directories.append(item)
            except OSError:
                continue
        return files, directories
