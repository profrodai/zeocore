# 🧠 **QuackCore**

**The Kernel of the QuackVerse**

> **QuackCore defines what is possible — not what happens.**
> It is the constitutional layer that makes the QuackVerse inspectable, auditable, and composable at scale.

---

## 🧠 What QuackCore Is

**QuackCore is the kernel of the QuackVerse.**

It defines the **contracts, primitives, and invariants** that every other component relies on.

QuackCore answers one question only:

> **“What shapes, rules, and interfaces are valid in this system?”**

It does **not** decide:

* what to run
* when to run it
* how to sequence work
* which tools to choose
* how users interact

Those concerns live above the kernel.

---

## 🧾 “Pure” Means No Business Side Effects — Not “No I/O”

When we say QuackCore is *pure*, we mean:

> **QuackCore performs no *domain side effects* and owns no *control-plane responsibilities*.**

QuackCore **may** include **infrastructure primitives** that perform low-level I/O, such as:

* filesystem abstractions
* config loading and validation
* path resolution
* serialization
* checksums and hashing
* artifact conventions
* logging semantics

These are **kernel capabilities**, not business actions.

What QuackCore must never do is encode **what an organization does** or **how work flows**.

---

## ❌ What QuackCore Is Not

QuackCore is **not**:

* a workflow engine
* a scheduler
* an execution service
* an agent runtime
* a UI or CLI application
* an integration hub for business systems
* a teaching platform
* a product surface
* a place for proprietary logic

If a module needs to:

* start a server
* execute tools
* manage long-running processes
* mutate external business systems
* embed prompts or policies
* require production secrets to import safely

…it does **not** belong in QuackCore.

---

## 🧭 Position in the QuackVerse

```
┌────────────────────────────────────────────┐
│        RING C — EXPERIENCES                │
│  Temporal · Agents · QuackRunner           │
│  Quackchat · n8n                           │
├────────────────────────────────────────────┤
│        RING B — TOOLS (WORKERS)            │
│  QuackVideo · QuackImage · QuackMachinima │
│  QuackQuote · QuackTutorial · …            │
├────────────────────────────────────────────┤
│        RING A — CORE (KERNEL)              │
│        ▶ QuackCore ◀                      │
│  Contracts · Capabilities · Registries     │
│  Config · IO · Results                    │
└────────────────────────────────────────────┘
```

QuackCore lives entirely in **Ring A**.

Everything depends on it.
It depends on nothing above it.

---

## 🧠 Core Responsibilities

QuackCore is responsible for **definition, validation, and transparency** — not execution.

---

### 1️⃣ Contracts & Canonical Schemas

QuackCore defines the **canonical shapes** used across the QuackVerse:

* tool input schemas
* tool output manifests
* run requests and run results
* error and status envelopes
* artifact metadata
* provenance and checksums

These contracts enable:

* interoperability
* auditability
* long-term stability
* machine and human inspection

---

### 2️⃣ Capability Interfaces

QuackCore defines **what kinds of things may exist**, without implementing them:

* tool capability protocols
* execution request interfaces
* storage abstraction interfaces
* configuration contracts

QuackCore answers:

> *“If something claims to be a tool, runner, or capability, what must it look like?”*

---

### 3️⃣ Registries & Discovery

QuackCore provides typed registries and discovery mechanisms:

* plugin discovery
* capability registration
* schema validation
* deterministic error reporting

This enables composition without tight coupling.

---

### 4️⃣ Infrastructure Primitives (Kernel Services)

QuackCore includes **domain-agnostic primitives** required everywhere:

* **Filesystem (`quack_core.lib.fs`)**
  Standardized read/write, atomic operations, structured data IO, checksums.
* **Paths (`quack_core.lib.paths`)**
  Resolution, normalization, validation, safety semantics.
* **Config (`quack_core.config`)**
  Typed, validated configuration conventions.
* **Logging & CLI semantics**
  Consistent diagnostics and structured output.
* **Artifact conventions**
  Naming, manifests, deterministic layouts.

These primitives may perform I/O **as a capability**, but they do not encode workflows or decisions.

---

### 5️⃣ Adapter Libraries (Not Hosted Services)

QuackCore may include **adapter libraries** such as:

* HTTP adapters
* MCP adapters

These define:

* request/response envelopes
* validation rules
* error translation
* auth propagation conventions

They **do not**:

* host servers
* expose public endpoints
* execute tools
* manage lifecycle

Hosted services live in **QuackRunner** or other Ring C components.

---

### 6️⃣ Self-Describing & White-Box Conventions

QuackCore is **explicitly white-box**.

It defines conventions that allow the system to describe itself:

* schema introspection
* artifact manifests
* provenance metadata
* deterministic result envelopes
* validation and diagnostics semantics

This enables:

* auditing
* debugging
* compliance
* reproducibility
* operational clarity

This is **not teaching**.
This is **transparency**.

---

## ✅ What Belongs in QuackCore vs ❌ What Does Not

### ✅ Allowed in QuackCore

* filesystem abstraction
* config parsing and validation
* logging and result envelopes
* schema definitions
* hashing and checksums
* artifact conventions
* adapter *libraries* (no hosting)

### ❌ Not Allowed in QuackCore

* workflow logic
* execution logic
* business integrations (Twenty, Docusaurus, etc.)
* domain actions (“publish”, “update CRM”, “render video”)
* UI logic
* agent reasoning
* prompts or policies

---

## 🧪 The Litmus Test

A module belongs in QuackCore **only if**:

* it is domain-agnostic
* it introduces no side effects beyond primitive I/O
* it encodes no business workflow
* it is safe to import without secrets
* it defines rules, not behavior

If it *does something*, it does not belong here.

---

## 🧠 QuackCore vs QuackRunner

| Concern             | QuackCore | QuackRunner    |
| ------------------- | --------- | -------------- |
| Defines contracts   | ✅         | ❌              |
| Provides primitives | ✅         | ❌              |
| Hosts APIs          | ❌         | ✅              |
| Executes tools      | ❌         | ✅              |
| Side effects        | ❌         | ✅              |
| Stability           | Very high | Evolves faster |

QuackCore is the **constitution**.
QuackRunner is an **institution** governed by it.

---

## 📦 Indicative Repository Structure

```text
quack-core/
├── contracts/          # Canonical schemas
├── capabilities/       # Capability interfaces
├── registries/         # Discovery & validation
├── adapters/           # Adapter libraries (HTTP, MCP)
├── config/             # Configuration models
├── lib/
│   └── fs/             # Filesystem primitives
├── paths/              # Path semantics
├── results/            # Result & error envelopes
├── utils/              # Pure helpers only
│
├── tests/
└── README.md
```

---

## 🧭 Governance Rules (Non-Negotiable)

1. QuackCore defines rules, not pipelines
2. No orchestration
3. No execution
4. No business side effects
5. No prompts or policies
6. Infrastructure primitives are allowed
7. Adapter libraries allowed — hosting is not
8. White-box by default
9. Engine public, content private

---

## 🧠 Closing Statement

**QuackCore is the constitutional layer of the QuackVerse.**

It does not act.
It does not decide.
It does not execute.

It defines the invariants that make AI-first organizations:

* auditable
* composable
* portable
* and sovereign.

If QuackCore is solid, everything built on top can evolve safely.
