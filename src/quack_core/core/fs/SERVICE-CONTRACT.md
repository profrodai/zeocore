# `core/fs` — FileSystemService Public Contract

> **Scope.** This document is the *behavioral contract* of the public `FileSystemService`
> — what a caller may rely on. It complements `ARCHITECTURE.md` (which describes the
> internal layering: `_internal` → `_ops` → `service`); this document describes the
> guarantees the outermost layer makes to its consumers. Where this document and the
> code disagree, the code wins — report the drift.

## 1. The public surface

`FileSystemService` (in `service/full_class.py`) is the **only** public service class.
It is composed of operation mixins (directory, file, file-info, structured-data, path,
path-validation, utility) plus base functionality. Callers construct one service and
call its methods; they do not import the mixins, `_ops`, or `_internal` (those raise
`AttributeError` on import by design — doctrine enforcement).

Input paths are typed `FsPathLike` (str, `Path`, `PathLike[str]`, or a result-like object
carrying a path). Every public method returns a **typed result object**, never a bare
value.

## 2. The result contract

Every operation returns an `OperationResult` subclass (`BoolResult`, `PathResult`,
`FileInfoResult`, `DataResult[T]`, `DirectoryInfoResult`, `WriteResult`, …). The contract
on that result:

- **`ok: bool` is the canonical success indicator.** Check `result.ok`.
- **`error_info: ErrorInfo | None` is the canonical error channel** when `ok is False`.
  `ErrorInfo` carries: `type` (a stable identifier, e.g. `file_not_found`), `message`
  (the original exception message), `hint` (optional user-facing resolution), `exception`
  (the exception class name), `trace_id` (optional), and `details` (optional structured
  context — path, errno, etc.).
- **`message: str | None`** is a human-readable summary (success *or* failure).
- **`error: str | None` is LEGACY and deprecated** — use `error_info`. Retained only for
  backward compatibility; new callers must not read it.
- **`.success` is a deprecated transitional alias for `.ok`** (R-1). It exists only until a
  whole-tree audit shows zero `core/fs`-internal readers of `.success`; new code reads
  `.ok`. Do not introduce new `.success` readers.

## 3. "Never raises" — the operation guarantee, and its one boundary

**Operation methods never raise.** Every public operation wraps its body in a catch-all
that converts any exception into a failed result: `except Exception as e: return
<Result>(ok=False, error_info=self._map_error(e), …)`. A caller invoking an operation
(read, write, stat, hash, list, ensure-dir, mime-type, …) can rely on getting a result
back with `ok is False` and a populated `error_info` — it will **not** get an exception
propagated out of the operation.

**The one boundary that does raise: path normalization / sandbox validation.**
`_normalize_input_path` (the single source of truth for input coercion) deliberately
raises, because an un-normalizable or sandbox-violating path is a *contract violation by
the caller*, not an operational failure:

- **`QuackValidationError`** — the input cannot be coerced to a path (wrong type, malformed
  shape, or an otherwise-invalid value). The original error is chained as `original_error`.
- **`QuackPathSecurityError`** and its subtypes **`QuackPathEscapeError`** /
  **`QuackPathOutsideBaseDirError`** — the path violates sandboxing (see §4). These are
  re-raised unmapped so the caller can distinguish a security breach from an ordinary
  failure.

So the precise guarantee is: **operations return results and never raise; the
normalization boundary raises `QuackValidationError` on invalid input and
`QuackPathSecurityError` on a sandbox violation.** A contract that claimed unconditional
"never raises" would be false — the security boundary raising is intentional and
load-bearing.

(Separately, `__getattr__` on the `service` and `fs` packages raises `AttributeError` for
non-public names — an import-time doctrine guard, not an operational path.)

## 4. Sandbox / allowed-roots MUST-NOT (R-2, Master-ratified)

Path coercion is **sandboxed by default**. `coerce_path(path, base_dir, allow_absolute)`
anchors relative paths to the service's `base_dir` and, when `base_dir` is set:

- A **relative** path is resolved under `base_dir`.
- An **absolute** path is permitted **only if** it resolves to a location **inside**
  `base_dir`. An absolute path that escapes `base_dir` raises `QuackPathOutsideBaseDirError`.
- A traversal escape (`..` above `base_dir`, symlink escape, etc.) raises
  `QuackPathEscapeError`.

The escape hatch is explicit and named: the service's **`unsafe_allow_absolute_paths`**
flag (passed through as `allow_absolute`). It is `False` by default; only when explicitly
set `True` may absolute paths outside `base_dir` resolve. The MUST-NOT: **a path must not
escape `base_dir` unless the caller has explicitly opted out of the sandbox via
`unsafe_allow_absolute_paths=True`.** This was verified behaviorally (a `..` traversal is
blocked with the flag `False`, permitted with the flag `True`) and ratified.

## 5. What a caller may rely on (summary)

- Call `FileSystemService`; never import mixins/`_ops`/`_internal`.
- Read `result.ok`; on failure read `result.error_info` (not the deprecated `error`/`success`).
- Operations return failed results, never raised exceptions.
- Passing a malformed or sandbox-escaping path is a caller error and *will* raise
  (`QuackValidationError` / `QuackPathSecurityError`) — validate or sandbox-scope inputs,
  or set `unsafe_allow_absolute_paths` deliberately.
