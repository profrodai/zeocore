"""Optional fresh-kernel execution for trusted course notebooks."""

from zeo_core.integrations.notebook.identity import (
    environment_identity as get_notebook_environment_identity,
)
from zeo_core.integrations.notebook.models import (
    NotebookExecutionReceipt,
    NotebookExecutionRequest,
)
from zeo_core.integrations.notebook.service import execute_notebook

__all__ = [
    "NotebookExecutionReceipt",
    "NotebookExecutionRequest",
    "execute_notebook",
    "get_notebook_environment_identity",
]
