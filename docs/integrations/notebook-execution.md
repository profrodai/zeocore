# Fresh-kernel notebook execution

**Updated:** 2026-09-09. Development API, pending release.

Install the optional `zeocore[notebook]` extra. It includes nbclient, the Python
kernel and psutil for descendant tracking. Ordinary ZeoCore consumers do not
need it. The learner runtime must not depend on this authoring tool.

```python
from zeo_core.integrations.notebook import NotebookExecutionRequest, execute_notebook

result = execute_notebook(NotebookExecutionRequest(
    source_path="clean.ipynb",
    output_path="executed.ipynb",
    workspace_root="/path/to/workspace",
    working_directory="/path/to/workspace",
    kernel_name="python3",
    timeout_seconds=120,
    cell_timeout_seconds=30,
))
assert result.status == "SUCCEEDED"
print(result.model_dump_json(indent=2))
```

Each call creates a new worker, a new Python kernel, an isolated HOME and a
private Python kernelspec using this environment's interpreter. Only the
explicitly provisioned `python3` kernel is available; another name produces
`KERNEL_UNAVAILABLE`. The kernel uses local IPC transport. Notebook code runs
in the declared working directory. Source and output must remain within the
workspace and must differ; existing output is refused.

The parent enforces the whole-run deadline independently of nbclient's cell
timeout. Syntax errors, assertions, exceptions, missing/crashed kernels, cell
timeouts and whole-run timeouts cannot return success. Stale execution counters
and outputs are cleared before running. Empty executable cells cannot turn
unevaluated output into execution evidence. A notebook with no code cannot
provide execution evidence even when `require_code_cells=False`. Code tagged
`no-execute` is skipped and counted separately; an entirely skipped notebook
cannot pass.

The parent retains observed process identities and kernel sessions, freezes
ordinary descendant spawning during final cleanup, kills descendants and reaps
the worker after success, failure or timeout. A cleanup failure prevents output
promotion. Executed output is written separately and exclusively promoted only
after successful execution and cleanup. Source changes during execution fail.

The environment starts from explicit PATH and temporary HOME/Jupyter/IPython/XDG
directories. Parent credentials, proxies and unrelated variables are omitted.
An allowlist may carry LANG, LC_ALL, TZ or non-secret COURSE_* variables; names
containing secret/token/password/key/credential/proxy markers are refused.
Do not put secrets in COURSE_* values. Kernel discovery uses only the freshly
created kernelspec directory, not ambient user kernel configuration.

This executes **trusted course code**. It is not an operating-system sandbox:
code can still read accessible files, start processes and use the network.
Receipts explicitly record process/network isolation as UNAVAILABLE. Ordinary
kernel/child cleanup is tested; deliberate hostile daemonization, privilege
changes and unrelated processes are outside this containment claim. Use an
external container with enforced network policy for releases that require it.

Receipts contain source/executed hashes, kernel and executor versions, actual
executed/skipped code-cell counts, fixed failure categories and cleanup status.
They do not contain source, output text or raw tracebacks. No successful
execution establishes student learning or human visual approval.

Run `make verify`. The real-kernel tests include stale-output, fresh-state,
synthetic-secret and child-process controls after every important exit path.
