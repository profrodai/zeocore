from typing import Any
from pathlib import Path
from quack_core.core.fs._internal.path_utils import _extract_path_str, _safe_path_str
from quack_core.core.fs.results import DataResult

def extract_path_str(obj: Any) -> str:
    return _extract_path_str(obj)

def safe_path_str(obj: Any, default: str | None = None) -> str | None:
    return _safe_path_str(obj, default)

def extract_path_from_result(path_or_result: Any) -> DataResult[str]:
    try:
        path_str = _extract_path_str(path_or_result)
        return DataResult(success=True, path=Path(path_str), data=path_str, format="path", message="Successfully extracted path")
    except Exception as e:
        return DataResult(success=False, path=None, data=str(path_or_result), format="path", error=str(e), message="Failed to extract path")