from typing import Any
from quack_core.core.fs.service import get_service
from quack_core.core.fs.results import DataResult

def get_disk_usage(path: Any) -> DataResult[dict[str, int]]:
    return get_service().get_disk_usage(path)

def is_path_writeable(path: Any) -> DataResult[bool]:
    return get_service().is_path_writeable(path)