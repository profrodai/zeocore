"""Process-local managed mode set by a trusted host before loading providers.

An irreversible latch prevents accidental fallback to member/device transport.
This is routing enforcement for cooperative SDK code, not a Python sandbox.
"""

_managed = False


def enter_managed_execution() -> None:
    global _managed
    _managed = True


def is_managed_execution() -> bool:
    return _managed
