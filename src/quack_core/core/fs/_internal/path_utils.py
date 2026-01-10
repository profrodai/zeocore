"""
Legacy internal path utils. 
Most logic has moved to quack_core.fs.normalize.
This file now just delegates or holds low-level helpers if needed.
"""
from quack_core.fs.normalize import coerce_path_str as extract_str_impl

def _extract_path_str(obj):
    return extract_str_impl(obj)

def _normalize_path_param(obj):
    from pathlib import Path
    return Path(extract_str_impl(obj))