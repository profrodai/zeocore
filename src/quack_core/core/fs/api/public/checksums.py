from typing import Any
from quack_core.core.fs.service import get_service
from quack_core.core.fs.results import DataResult

def compute_checksum(path: Any, algorithm: str = "sha256") -> DataResult[str]:
    return get_service().compute_checksum(path, algorithm)