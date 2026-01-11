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

> **No tool, agent, or workflow ever touches `pathlib`, `os`, or raw IO directly.**

Filesystem access is a **capability**, not an implementation detail.

---

## 2. Position in the QuackVerse (Doctrine Alignment)

### Ring placement

```
Ring A — CORE (QuackCore)
│
├── core.fs   ← YOU ARE HERE
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

### 1️⃣ Layering doctrine: `_internal` → `_ops` → `service`

There are **three layers**, but **only one public surface**.

---

### `_internal/` — Implementation layer (private, lowest level)

* Pure IO helpers
* Work only with `pathlib.Path`
* Raise **native Python exceptions**
* No Result models
* No logging policy
* No input normalization
* No awareness of base directories or sandboxing rules

> `_internal` is **pure implementation**.
> It is **never imported outside Core FS internals**.

---

### `_ops/` — Operation façade layer (private, core plumbing)

`_ops` is a **first-class internal operation façade**, not a convenience helper.

It exists to:

* compose `_internal` primitives into coherent filesystem operations
* encapsulate *how* low-level actions are performed
* provide a stable internal interface for the service layer
* reduce duplication across service mixins
* keep `_internal` small, focused, and testable

**Characteristics:**

* Calls `_internal/*`
* Groups multiple low-level actions into reusable operations
* May contain light internal logic (e.g. sequencing, helpers)
* **Still raises native exceptions**
* Returns **raw values only** (`Path`, `bytes`, `list[Path]`, `dict`, etc.)
* Does **not**:

  * return `*Result`
  * normalize `FsPathLike`
  * decide logging policy
  * map or swallow errors
  * import `results.py` or `normalize.py`

> `_ops` is **core internal plumbing**.
> It is private, but **not optional** once introduced.

---

### `service/` — Contract layer (only public surface)

* Owns the **public filesystem contract**
* Normalizes all inputs
* Anchors paths to policy (`base_dir`, sandboxing, etc.)
* Catches **all exceptions**
* Maps failures to structured `ErrorInfo`
* Returns typed `*Result` objects
* Owns logging and user-visible behavior
* Safe for:

  * QuackTools
  * Agents
  * CLI
  * Temporal
  * Cloud execution

> **Nothing outside `service/` may import `_ops/` or `_internal/`.**

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
* Used everywhere (tools, tests, CLI, agents)

There is **no alternate IO path**.

---

### 3️⃣ Input normalization is centralized

All public methods accept flexible inputs:

```python
FsPathLike = str | Path | Result | Protocol
```

Normalization rules:

* Implemented **once** in `core.fs.normalize`
* Used **only by the service layer**
* Never duplicated
* Never implemented in `_ops` or `_internal`

> If path coercion logic appears anywhere else, it is a bug.

---

### 4️⃣ Structured errors (no raw exceptions)

* `_internal` raises native exceptions
* `_ops` raises native exceptions
* `service` catches everything
* Errors are mapped to structured `ErrorInfo`
* Public methods **never raise**

This is mandatory for:

* CLI UX
* Agent reasoning
* Teaching
* Cloud retries
* Temporal workflows

---

### 5️⃣ Public boundary is enforced by imports

**Allowed dependencies:**

* `service/*` → may import `_ops/*` and `_internal/*`
* `_ops/*` → may import `_internal/*`
* `_internal/*` → imports nothing from higher layers

**Forbidden:**

* Anything outside `service/*` importing `_ops/*` or `_internal/*`
* `_internal/*` importing `_ops/*` or `service/*`
* `_ops/*` importing:

  * `service/*`
  * `results.py`
  * `normalize.py`

> If you see `from quack_core.core.fs._internal import ...` outside `service/`, it’s a doctrine violation.

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
├── service/            # PUBLIC CONTRACT SURFACE (ONLY SURFACE)
│   ├── __init__.py     # get_service(), create_service()
│   ├── base.py         # FileSystemService base + error mapping
│   ├── standalone.py  # Functional wrappers (secondary surface)
│   │
│   ├── file_operations.py
│   ├── path_operations.py
│   ├── utility_operations.py
│   └── validation_operations.py
│
├── _ops/               # PRIVATE operation façade (core plumbing)
│   ├── file_ops.py
│   ├── path_ops.py
│   └── utility_ops.py
│
├── _internal/          # PRIVATE pure IO implementation
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

The **only canonical API**.

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
* No `_ops` / `_internal` imports
* May be removed in the future without breaking contracts

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

## 7. Responsibilities by layer (summary)

### `_internal/*`

* touches filesystem
* raises native exceptions
* no Results
* no normalization
* no logging
* no public guarantees

### `_ops/*`

* internal operation façade
* composes `_internal`
* raises native exceptions
* returns raw values
* no Results
* no normalization
* no public guarantees

### `service/*`

* normalizes inputs
* enforces sandboxing
* catches + maps errors
* emits Results
* owns logging + UX
* defines the public contract

---

## 8. Required public method catalogue

### Path operations

* `resolve`
* `exists`
* `is_file`
* `is_dir`
* `ensure_dir`
* `list_dir`

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

### `_ops` tests (recommended)

* verify `_ops` composes `_internal`
* ensure exceptions are not swallowed
* keep tests small — `_ops` is internal

---

## 10. Why this matters for DuckTyper & AI-First Media

This architecture enables:

* agent-safe filesystem reasoning
* reproducible content pipelines
* Temporal-safe retries
* n8n side-effect isolation
* teachable automation systems
* junior-safe contributions

> **If filesystem behavior is not predictable, automation does not compound.**

---

## 11. Final rule (non-negotiable)

> **If a QuackTool, Agent, or Workflow touches `pathlib` directly — it is a bug.**

All IO goes through `core.fs`.

This is how the system scales, teaches, and survives refactors.