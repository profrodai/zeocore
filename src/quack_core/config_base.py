# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/config_base.py
# module: quack_core.config_base
# role: module
# neighbors: __init__.py
# exports: BasePolicy, ConfigError, ConfigResolver, deep_merge
# git_branch: refactor/toolkitWorkflow
# git_commit: de0fa70
# === QV-LLM:END ===

"""
Configuration resolution engine with Deep Merge.
Handles the merge logic: Request > Preset > Policy > Defaults.
"""
import os
import yaml
from typing import TypeVar, Type, Dict, Any
from pydantic import BaseModel

T_Policy = TypeVar("T_Policy", bound=BaseModel)
T_Request = TypeVar("T_Request", bound=BaseModel)

class BasePolicy(BaseModel):
    """Base class for organization-wide defaults."""
    pass

class ConfigError(Exception):
    """Raised when config resolution fails (e.g. missing preset)."""
    pass

def deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries."""
    out = dict(base)
    for k, v in overlay.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out

class ConfigResolver:
    """
    Stateless utility to merge configuration layers.
    """

    @staticmethod
    def load_policy_file(path: str) -> Dict[str, Any]:
        """Safe loader for YAML policy file."""
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    @classmethod
    def resolve(
        cls,
        request: T_Request,
        policy_class: Type[T_Policy],
        tool_name: str,
        policy_path: str = "quack_policy.yaml"
    ) -> T_Policy:
        """
        Merges configuration in strict precedence order:
        1. Request (Runtime args) - Highest Priority
        2. Preset (If 'preset' is in request)
        3. Policy File (quack_policy.yaml)
        4. Class Defaults (Pydantic) - Lowest Priority
        """
        # 1. Start with Pydantic Defaults
        merged = policy_class().model_dump()

        # 2. Load Global Policy File
        full_policy_dict = cls.load_policy_file(policy_path)
        tool_policy = full_policy_dict.get(tool_name, {})
        merged = deep_merge(merged, tool_policy)

        # 3. Handle Presets (if request specifies one)
        if hasattr(request, 'preset') and request.preset:
            preset_name = request.preset
            # Presets are stored under 'presets' key in policy file
            # Format: presets: { video: { shorts: { ... } } }
            all_presets = full_policy_dict.get('presets', {}).get(tool_name, {})

            if preset_name not in all_presets:
                # We raise here to let the Interface layer handle the error mapping
                raise ConfigError(f"Preset '{preset_name}' not found for tool '{tool_name}'")
            
            preset_dict = all_presets[preset_name]
            merged = deep_merge(merged, preset_dict)

        # 4. Apply Request Overrides (exclude unset/none)
        request_dict = request.model_dump(exclude_unset=True, exclude_none=True)
        merged = deep_merge(merged, request_dict)

        # 5. Validate Final Result
        return policy_class.model_validate(merged)