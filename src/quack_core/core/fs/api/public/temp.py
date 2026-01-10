from typing import Any
from quack_core.core.fs.service import get_service
from quack_core.core.fs.results import DataResult

def create_temp_directory(prefix: str = "quackcore_", suffix: str = "") -> DataResult[str]:
    return get_service().create_temp_directory(prefix, suffix)

def create_temp_file(suffix: str = ".txt", prefix: str = "quackcore_", directory: Any = None) -> DataResult[str]:
    return get_service().create_temp_file(suffix, prefix, directory)