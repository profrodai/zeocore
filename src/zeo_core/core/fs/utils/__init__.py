"""
DEPRECATED: Use zeo_core.core.fs.service.standalone for utility functions.
"""

import warnings

# Deliberate wildcard: this is a deprecated backward-compat shim that must re-export
# the replacement module's full public surface. Enumerating symbols by hand risks
# silently dropping one on the next upstream change to `service.standalone`.
# Judged not a defect in quackverse-lint-mypy-backlog round 1, reconfirmed round 2.
from zeo_core.core.fs.service.standalone import *  # noqa: F403

warnings.warn(
    "zeo_core.core.fs.utils is deprecated. Use "
    "zeo_core.core.fs.service.standalone instead.",
    DeprecationWarning,
    stacklevel=2,
)
