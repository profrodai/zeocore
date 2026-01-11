# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/core/fs/_ops/serialization_ops.py
# module: quack_core.core.fs._ops.serialization_ops
# role: _ops
# neighbors: __init__.py, base.py, core.py, directory_ops.py, file_info.py, find_ops.py (+4 more)
# exports: SerializationOperationsMixin
# git_branch: feat/9-make-setup-work
# git_commit: d448237f
# === QV-LLM:END ===

import json
from pathlib import Path
from typing import Any

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

class SerializationOperationsMixin:
    def _read_text(self, path: Path, encoding: str = "utf-8") -> str:
        raise NotImplementedError
    def _write_text(self, path: Path, content: str, encoding: str = "utf-8", **kwargs) -> Path:
        raise NotImplementedError

    def _read_yaml(self, path: Path) -> dict[str, Any]:
        if not YAML_AVAILABLE: raise ImportError("PyYAML is not available")
        data = yaml.safe_load(self._read_text(path))
        if data is None: return {}
        if not isinstance(data, dict):
            raise ValueError(f"YAML content is not a dict: {type(data)}")
        return data

    def _write_yaml(self, path: Path, data: dict[str, Any], atomic: bool = True) -> Path:
        if not YAML_AVAILABLE: raise ImportError("PyYAML is not available")
        content = yaml.safe_dump(data, default_flow_style=False, sort_keys=False)
        return self._write_text(path, content, atomic=atomic)

    def _read_json(self, path: Path) -> dict[str, Any]:
        data = json.loads(self._read_text(path))
        if not isinstance(data, dict):
            raise ValueError(f"JSON content is not a dict: {type(data)}")
        return data

    def _write_json(self, path: Path, data: dict[str, Any], atomic: bool = True, indent: int = 2) -> Path:
        content = json.dumps(data, indent=indent, ensure_ascii=False)
        return self._write_text(path, content, atomic=atomic)