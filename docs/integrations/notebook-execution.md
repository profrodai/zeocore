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
assert result.success
assert result.content is not None
assert result.content.status == "SUCCEEDED"
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

## Execution contract after elder review

`max_output_bytes` bounds retained stream, stderr and rich-output message content
before nbclient accumulates it (default 10 MiB). `max_code_cells` bounds code-cell
inventory (default 1000). Exceeding either limit fails. A polled worker-RSS fuse
(default 512 MiB) protects against oversized incoming messages while the receiver
is decoding them; it is not an OS-enforced peak-memory bound. Trusted kernel code
can still allocate memory, and strict memory isolation requires an external OS
boundary. The receipt's captured byte count never exceeds the retention limit.

`timeout_seconds` covers worker/kernel startup and cell execution.
`startup_timeout_seconds` additionally bounds Jupyter's readiness wait. Cleanup
has its own declared `cleanup_timeout_seconds` allowance (default 5, maximum 30).
The total advertised process lifetime is startup/execution deadline plus cleanup
allowance, with ordinary scheduler/syscall overhead. Receipts name the cleanup
scope as observed process identities and sessions; complete descendant cleanup
is explicitly UNAVAILABLE. A detached child observed before kernel exit is
covered. Hostile daemonization between observations is outside that guarantee.

Kernel identity records the actual generated kernelspec SHA-256, interpreter
binary SHA-256, and a versioned environment SHA-256 covering that executable,
Python version and the installed-distribution inventory. The
kernelspec location is a managed logical path. Absolute local provenance paths
require `absolute_provenance_paths=True`. Only the generated private Python spec
is used; ambient same-name specs and their environment values are excluded.
`expected_environment_sha256` refuses unexpected installed environments before
executing cells. `environment_lock_path` records the full hash and relative path
of the consumer's declared lockfile; when omitted its evidence is unavailable.
A lock reference alone does not certify that every installed dependency matches
that lock: compare the recorded actual inventory identity with an approved one.
Course-release policy should require both the lock and expected identity.

Receipts count attempted, completed, failed and intentionally skipped cells.
A timeout or crash marks unfinished attempted cells failed. `no-execute` cells
are intentional skips; the generic executor reports them, while the consumer
must reject undeclared skips. All-skipped and no-code inputs fail. `allow_errors`
accepts only False; continuing for diagnostics is not a release-acceptance mode.
Expected-failure exercises should catch and assert their precise expected
exception and evidence, then complete normally.

Execution receipts describe individual observations. Exact output hashes may
legitimately differ across runs; they identify the bytes observed, not semantic
equivalence or learning. Stable-content semantic comparison is a separate gate.
Network isolation remains UNAVAILABLE because this executor does not enforce or
measure egress policy. An external runner must supply separate measured network
policy evidence; callers cannot turn an unverified assertion into ENFORCED here.
