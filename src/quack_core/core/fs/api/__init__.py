"""
DEPRECATED: Use quack_core.fs.service.standalone for utility functions.
"""
import warnings
from quack_core.fs.service.standalone import *

warnings.warn("quack_core.fs.api is deprecated. Use quack_core.fs.service or quack_core.fs.service.standalone instead.", DeprecationWarning, stacklevel=2)