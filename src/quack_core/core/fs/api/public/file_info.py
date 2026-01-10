from typing import Any
from quack_core.core.fs.service import get_service
from quack_core.core.fs.results import DataResult

def get_file_type(path: Any) -> DataResult[str]:
    return get_service().get_file_type(path)

def get_file_size_str(size_bytes: int) -> DataResult[str]:
    return get_service().get_file_size_str(size_bytes)

def get_file_timestamp(path: Any) -> DataResult[float]:
    return get_service().get_file_timestamp(path)

def get_mime_type(path: Any) -> DataResult[str | None]:
    return get_service().get_mime_type(path)

def is_file_locked(path: Any) -> DataResult[bool]:
    return get_service().is_file_locked(path)