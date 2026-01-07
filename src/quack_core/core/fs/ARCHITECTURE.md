# quack_core.core.fs — Architecture

## Why this module exists

`quack_core.core.fs` is the **filesystem kernel** of QuackCore.

It provides:
- **Safe, inspectable file operations** (read/write/copy/move/delete/list)
- **A stable boundary** between raw `pathlib.Path` operations and user-facing workflows
- **Typed results** that make CLI output and automation reliable (no exceptions-as-control-flow)

It does NOT:
- implement domain workflows (that belongs in QuackTools / workflows)
- bundle unrelated utilities (keep it small, composable, and teachable)

---

## Design invariants (non-negotiable)

### 1) Two-layer boundary: `_internal` vs `api/public`
- `_internal/` may use `Path`, raise exceptions, and be “Pythonic”
- `api/public/` must:
  - normalize inputs
  - catch exceptions
  - return `*Result` Pydantic models
  - never leak internal helpers directly

### 2) Consistent return types
- Public methods **never** return `Path` (unless wrapped in a `PathResult`)
- Public methods **never** return `bool` / `str` directly when a Result exists
- Internal helpers may return primitives for performance and simplicity

### 3) Service-first API
Everything user-facing routes through `FileSystemService`:

- `FileSystemService` is composed via mixins:
  - `PathOperationsMixin`
  - `FileOperationsMixin`
  - `UtilityOperationsMixin`
  - `ValidationOperationsMixin` (optional but recommended)

Standalone functions are thin convenience wrappers that call the service.

### 4) Input normalization is centralized
All public entry points accept common flexible inputs:
- `str | Path | os.PathLike`
- optional `encoding`, `errors`, `newline`, etc.

Normalization rules live in one place and are reused.

### 5) Errors are QuackErrors
- Internals may raise native exceptions
- Public layer catches and maps to:
  - `QuackFileNotFoundError`
  - `QuackPermissionError`
  - `QuackValidationError`
  - `QuackIOError`
…then returns failure Results with structured diagnostics.

---

## Public API surface

### Primary surface: `FileSystemService`
- Provides all public filesystem operations
- Methods return `*Result` objects

### Secondary surface: functional wrappers
For ergonomics in scripts:
- `read_text(...)`
- `write_text(...)`
- `copy_file(...)`
- etc.

They call `get_fs_service()` and delegate.

---

## Core result models

All public operations return a Pydantic model with a shared minimal contract:

### Required fields (recommended baseline)
- `ok: bool`
- `path: Optional[str]` or `PathResult` composition
- `error: Optional[ErrorInfo]` (structured)
- `meta: Optional[dict]` (sizes, counts, timestamps, etc.)

### "ErrorInfo" should include
- `type`
- `message`
- `hint` (optional)
- `exception` (optional stringified class)
- `trace_id` (optional, if you do tracing)

---

## File layout (canonical)

quack_core/lib/fs/
- __init__.py
- service.py
- api/
  - public/
    - __init__.py
    - results.py
    - normalize.py
    - wrappers.py
- _internal/
  - __init__.py
  - types.py
  - normalize.py
  - errors.py
  - path_ops.py
  - file_ops.py
  - util_ops.py
  - validate.py
- operations/
  - __init__.py
  - path_operations.py
  - file_operations.py
  - utility_operations.py
  - validation_operations.py
- mixins/
  - __init__.py
  - path_operations_mixin.py
  - file_operations_mixin.py
  - utility_operations_mixin.py
  - validation_operations_mixin.py
- tests/
  - test_public_api_contracts.py
  - test_path_ops.py
  - test_file_ops.py
  - test_wrappers.py

Notes:
- `operations/` contains reusable operation primitives (still "public-ish" but not user-facing)
- `mixins/` attach those operations to the service with consistent logging + error mapping
- `_internal/` is the only place allowed to directly touch low-level implementation details

---

## Responsibilities by layer

### `_internal/*`
Contains raw implementation helpers:
- work with `Path`
- raise standard exceptions
- keep functions short and pure where possible

Examples:
- `_internal/path_ops.py`: ensure_dir, resolve, expanduser, glob
- `_internal/file_ops.py`: atomic write, safe copy, read bytes
- `_internal/util_ops.py`: compute hash, guess mime, size formatting
- `_internal/validate.py`: validate extension, max size, forbidden paths

### `operations/*`
Defines operation objects or small helpers used by mixins:
- depends on `_internal`
- still not the public API
- should be stable and testable independently

### `api/public/*`
The "contract surface":
- `normalize.py`: input coercion and option defaults
- `results.py`: Pydantic Result models
- `wrappers.py`: functional wrappers

No business logic beyond:
- normalize
- call service
- return result

### `service.py`
The composition root:
- defines `FileSystemService(...)`
- integrates mixins
- owns shared dependencies (logger, config, path service if needed)

---

## Method catalogue (what must exist)

### Path operations (public)
- `resolve(path) -> PathResult`
- `exists(path) -> BoolResult`
- `is_file(path) -> BoolResult`
- `is_dir(path) -> BoolResult`
- `ensure_dir(path, parents=True) -> PathResult`
- `list_dir(path, pattern=None, recursive=False) -> PathsResult`

### File operations (public)
- `read_text(path, encoding='utf-8') -> TextResult`
- `write_text(path, text, encoding='utf-8', create_dirs=True) -> WriteResult`
- `read_bytes(path) -> BytesResult`
- `write_bytes(path, data, create_dirs=True) -> WriteResult`
- `copy(src, dst, overwrite=False, create_dirs=True) -> CopyResult`
- `move(src, dst, overwrite=False, create_dirs=True) -> MoveResult`
- `delete(path, missing_ok=True) -> DeleteResult`

### Utility operations (public)
- `stat(path) -> StatResult`
- `hash_file(path, algo='sha256') -> HashResult`
- `mime_type(path) -> MimeResult`
- `tree(path, max_depth=..., pattern=...) -> TreeResult` (optional but useful)

### Validation operations (public)
- `validate_path(path, rules=...) -> ValidationResult`
- `validate_file(path, max_bytes=..., allowed_ext=..., forbidden_globs=...) -> ValidationResult`

---

## Cross-check checklist (for reconstruction)

### Contract checks
- [ ] Every public method returns a `*Result` Pydantic model
- [ ] No public method leaks raw `Path` or raw exceptions
- [ ] Every failure case sets `ok=False` and fills `error`

### Boundary checks
- [ ] `_internal/*` is never imported by consumers directly (only by operations/service/mixins)
- [ ] `api/public/*` imports do not depend on `_internal/*`

### Consistency checks
- [ ] Normalization exists in one place (no duplicated coercion logic)
- [ ] Encoding defaults are consistent (`utf-8`)
- [ ] All operations support `create_dirs` where writing occurs

### Test checks
- [ ] One test ensures each public method never raises (contract test)
- [ ] Golden tests for error mapping (missing file, permission denied)
- [ ] Wrapper functions are tested to ensure they delegate to service

---
