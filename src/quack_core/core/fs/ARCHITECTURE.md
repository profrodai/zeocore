# 🧠 `quack_core.core.fs` — Filesystem Architecture

**Status:** Canonical · Doctrine-Aligned
**Ring:** Core (QuackCore)
**Audience:** Core maintainers, QuackTool authors, junior contributors

---

## 1. Why this module exists

`quack_core.core.fs` is the **filesystem kernel** of QuackCore.

It defines **how all file IO happens across the QuackVerse**, in a way that is:

* safe (no exceptions as control flow)
* inspectable (typed results, structured errors)
* teachable (clear contracts, layered responsibilities)
* automation-ready (CLI, agents, Temporal, n8n)

This module exists so that:

> **No tool, agent, or workflow ever needs to touch `pathlib`, `os`, or raw IO directly.**

---

## 2. Position in the QuackVerse (Doctrine Alignment)

### Ring placement

```
Ring A — CORE (QuackCore)
│
├── core.fs  ← YOU ARE HERE
│
├── core.config
├── core.logging
├── core.errors
└── core.protocols
```

### Responsibilities (non-negotiable)

`core.fs`:

* ✅ defines IO **capabilities and contracts**
* ✅ emits **artifacts + structured results**
* ✅ is safe for **CLI, agents, and cloud execution**
* ❌ does NOT orchestrate workflows
* ❌ does NOT embed narratives or IP
* ❌ does NOT render or schedule

> `core.fs` answers:
> **“What filesystem actions are possible, and in what shape?”**

---

## 3. Design invariants (non-negotiable)

### 1️⃣ Two-layer boundary: `_internal` vs `service`

There are **exactly two meaningful layers**.

#### `_internal/` — Implementation layer

* Pure IO helpers
* Work only with `pathlib.Path`
* Raise **native exceptions**
* No Result models
* No logging policy
* No normalization logic

> `_internal` is **not a public API**.

#### `service/` — Contract layer (public)

* Owns the public filesystem contract
* Normalizes all inputs
* Catches all exceptions
* Maps errors to `ErrorInfo`
* Returns typed `*Result` objects
* Safe for tools, agents, CLI, Temporal

> **Nothing outside `service/` should touch `_internal/`.**

---

### 2️⃣ Service-first API (single source of truth)

All filesystem access routes through:

```python
FileSystemService
```

Accessed via:

```python
from quack_core.core.fs.service import get_service
```

* One shared service instance
* Configured once (base_dir, logging, policy)
* Used everywhere (CLI, tools, tests, agents)

There is **no alternate IO path**.

---

### 3️⃣ Input normalization is centralized

All public methods accept **flexible inputs**:

```python
FsPathLike = str | Path | Result | Protocol
```

Normalization rules:

* Implemented **once** in `core.fs.normalize`
* Used **only by the service layer**
* Never duplicated
* Never implemented in `_internal`

> If path coercion logic appears in more than one place, it is a bug.

---

### 4️⃣ Structured errors (no raw exceptions)

* `_internal` raises native exceptions
* `service` catches everything
* Errors are mapped to structured `ErrorInfo`
* Results **never raise**

This is mandatory for:

* CLI UX
* Agent reasoning
* Teaching
* Cloud retries
* Temporal workflows

---

## 4. Canonical file layout

```
quack_core/core/fs/
│
├── __init__.py
│
├── protocols.py        # FsPathLike, HasPath, HasData, etc.
├── results.py          # Pydantic Result + ErrorInfo models
├── normalize.py        # Input coercion (SSOT)
│
├── service/            # PUBLIC CONTRACT SURFACE
│   ├── __init__.py     # get_service(), create_service()
│   ├── base.py         # FileSystemService base + error mapping
│   ├── standalone.py  # Functional wrappers (secondary surface)
│   │
│   ├── file_operations.py
│   ├── path_operations.py
│   ├── utility_operations.py
│   └── validation_operations.py
│
├── operations/         # Bridge layer (optional, reusable)
│   ├── file_ops.py
│   ├── path_ops.py
│   └── utility_ops.py
│
├── _internal/          # PURE IMPLEMENTATION
│   ├── file_ops.py
│   ├── path_ops.py
│   ├── util_ops.py
│   └── validate.py
│
└── tests/
    ├── test_contract_never_raises.py
    ├── test_error_mapping.py
    ├── test_service_file_ops.py
    └── test_standalone_wrappers.py
```

---

## 5. Public API surfaces

### Primary surface — `FileSystemService`

This is the **only canonical API**.

* All methods return `*Result`
* All failures are structured
* All inputs normalized
* No side-effects beyond IO

Used by:

* QuackTools
* Agents
* CLI commands
* Cloud execution

---

### Secondary surface — functional wrappers

For ergonomics only:

```python
from quack_core.core.fs.service.standalone import read_text
```

Rules:

* Wrappers **delegate only**
* No logic
* No normalization
* No `_internal` imports
* Safe to delete later if needed

---

## 6. Result model doctrine

### Baseline contract (all Results)

Every public method returns a Pydantic model with:

```python
ok: bool
path: Optional[Path]
error_info: Optional[ErrorInfo]
meta: Optional[dict]
```

> `success` may exist for backward compatibility,
> but `ok` is the canonical semantic.

---

### `ErrorInfo` (required structure)

```python
class ErrorInfo(BaseModel):
    type: str              # e.g. "file_not_found"
    message: str
    hint: str | None
    exception: str | None
    trace_id: str | None
```

Mapped centrally in `service.base`.

---

## 7. Responsibilities by layer

### `_internal/*`

* touch the filesystem
* raise native exceptions
* no logging policy
* no Results
* no normalization

### `operations/*` (optional)

* reusable groupings
* depend on `_internal`
* no public guarantees

### `service/*`

* normalize inputs
* catch + map errors
* emit Results
* own logging + policy
* enforce doctrine

---

## 8. Required public method catalogue

### Path operations

* `resolve(path)`
* `exists(path)`
* `is_file(path)`
* `is_dir(path)`
* `ensure_dir(path, parents=True)`
* `list_dir(path, pattern=None, recursive=False)`

### File operations

* `read_text`
* `write_text`
* `read_bytes`
* `write_bytes`
* `copy`
* `move`
* `delete`

### Utility operations

* `stat`
* `hash_file`
* `mime_type`
* `tree` (optional)

### Validation operations

* `validate_path`
* `validate_file`

---

## 9. Test doctrine (mandatory)

### Contract tests

* No public method may raise
* All failures return `ok=False`

### Error mapping tests

* missing file
* permission denied
* invalid path

### Wrapper tests

* wrappers delegate to service
* no independent behavior

---

## 10. Why this matters for DuckTyper & AI-First Media

This design enables:

* agents reasoning over filesystem actions
* reproducible content pipelines
* Temporal-safe retries
* n8n side-effect isolation
* teachable automation flows
* junior-safe contribution

> **If filesystem behavior is not predictable,
> automation does not compound.**

---

## 11. Final rule (non-negotiable)

> **If a QuackTool, Agent, or Workflow touches `pathlib` directly — it is a bug.**

All IO goes through `core.fs`.

This is how the system scales, teaches, and survives refactors.

