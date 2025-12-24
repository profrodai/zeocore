"""
Configuration resolution engine.
Handles the merge logic: Request > Preset > Policy > Defaults.
"""
import os
import yaml
from typing import TypeVar, Type, Optional, Dict, Any
from pydantic import BaseModel

T_Policy = TypeVar("T_Policy", bound=BaseModel)
T_Request = TypeVar("T_Request", bound=BaseModel)

class BasePolicy(BaseModel):
    """Base class for organization-wide defaults (quack_policy.yaml)."""
    pass

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
            # We log this in a real app, but for now we return empty to fall back to defaults
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
        # 1. Load Global Policy File
        full_policy_dict = cls.load_policy_file(policy_path)
        
        # 2. Extract tool-specific policy
        tool_policy_dict = full_policy_dict.get(tool_name, {})

        # 3. Handle Presets (if request specifies one)
        preset_dict = {}
        if hasattr(request, 'preset') and request.preset:
            # Presets are stored under 'presets' key in policy file
            # Format: presets: { video: { shorts: { ... } } }
            all_presets = full_policy_dict.get('presets', {}).get(tool_name, {})
            preset_dict = all_presets.get(request.preset, {})

        # 4. Extract explicit values from Request (exclude Unset/None)
        # We assume request fields map 1:1 to policy fields where overrides are allowed
        request_dict = request.model_dump(exclude_unset=True, exclude_none=True)

        # 5. Merge! (Last one wins)
        # Start with model defaults (via empty constructor)
        # update with tool policy -> update with preset -> update with request
        
        # Create base instance to get defaults
        final_policy = policy_class(**tool_policy_dict)
        
        # Apply Preset
        if preset_dict:
            final_policy = final_policy.model_copy(update=preset_dict)
            
        # Apply Request overrides
        final_policy = final_policy.model_copy(update=request_dict)
        
        return final_policy