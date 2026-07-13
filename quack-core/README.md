# 🧠 **QuackCore**

**The Sovereign Kernel of the QuackVerse**

> **QuackCore defines what is possible — not what happens.**
> It is the constitutional layer and the "Sovereign Brain" that makes AI-first organizations auditable, portable, and resistant to hallucination.

---

## 🧠 What QuackCore Is

**QuackCore is the Ring A kernel of the QuackVerse.**

It defines the **contracts, primitives, and authoritative state patterns** that every other component relies on. In the Sovereign Agent Architecture, QuackCore is the "Truth Provider" that allows agents like OpenClaw to verify their own actions against a local system of record.

It does **not** decide:

* what the Agent should "think"
* when to trigger a limb
* how to publish content

---

## 🧾 The Sovereign "Truth" Primitives

QuackCore is "pure" in logic but **authoritative in I/O**. It owns the standards for the **Local Project Brain**:

* **The Ticket System (`quack_core.async`)**: Standardizes the `RunID` ticket and the status-polling handshake for asynchronous limbs.
* **The Artifact Store (`quack_core.store`)**: Defines the `.quack/` directory structure, ensuring local portability.
* **The Ledger (`quack_core.ledger`)**: Provides the schema and logic for the local `ledger.db`—the immutable production lineage.
* **Discovery (`quack_core.discovery`)**: Generates machine-readable capability maps so agents can self-teach the CLI surface.

---

## ❌ What QuackCore Is Not

QuackCore is **not**:

* **The Manager:** It does not plan (Agents do).
* **The Muscle:** It does not execute CLI commands or start sub-processes (QuackRunner does).
* **The Watchdog:** It does not manage durability or retries (Temporal does).
* **The Repository:** It does not store stories or courses (Everduck does).

---

## 🧭 Position in the QuackVerse

```
┌──────────────────────────────────────────────────────────┐
│             RING C — AGENTIC CONTROL                     │
│    OpenClaw (Manager) · Temporal · Quackchat (Cockpit)   │
├──────────────────────────────────────────────────────────┤
│             RING B — ATOMIC LIMBS (WORKERS)              │
│    QuackIngest · QuackDistro · QuackVideo · QuackDeck    │
├──────────────────────────────────────────────────────────┤
│             RING A — THE SOVEREIGN BRAIN                 │
│        ▶ QuackCore ◀                                     │
│    Ticket System · QuackStore (.quack/) · QuackLedger    │
└──────────────────────────────────────────────────────────┘

```

Everything depends on QuackCore. It is the only package allowed to be imported by Ring B workers.

---

## 🧠 Core Responsibilities

### 1️⃣ Authoritative Contracts (Anti-Hallucination)

QuackCore defines the **Proof of Work** requirement.

* **Manifests:** Mandatory JSON schema for success.
* **Summaries:** The `summary.md` standard—LLM-optimized snippets that update an agent's context without "context shredding."
* **Checksums:** Logic for `QC_MANIFEST_VERIFIED` signatures.

### 2️⃣ The Async Handshake (Tickets)

Standardizes the `RunID` lifecycle:

* **Ticket Issuance:** Creating the `pending` state record.
* **Polling Logic:** How `quack status` retrieves machine-readable progress.
* **Verification:** The transition from `pending` to `success` based on file-system proofs.

### 3️⃣ Local Portability (The `.quack/` folder)

Owns the filesystem primitives that ensure the **Sovereign Brain** stays with the project:

* Standardizing the `runs/`, `assets/`, and `metadata/` hierarchies.
* Ensuring the `ledger.db` is the single source of truth for project lineage.

### 4️⃣ Error Taxonomy (`QC_*` Codes)

Defines the blessed machine-readable error codes. This allows agents to pivot or escalate based on **Area** (IO, VAL, SYS) rather than parsing raw stack traces.

---

## ✅ What Belongs in QuackCore vs ❌ What Does Not

### ✅ Allowed in QuackCore

* Artifact store definitions (`.quack/`)
* Ledger schemas and lineage logic
* Async ticket state models
* `summary.md` generation primitives
* Machine-readable `--discovery` schemas
* Result/Error envelopes (`QC_` codes)

### ❌ Not Allowed in QuackCore

* Agent prompts or "monologue" logic
* CLI entry points for specific tools (e.g., `quack video`)
* Temporal worker implementations
* Third-party SaaS API clients (n8n handles these)
* Rendering logic

---

## 🧠 QuackCore vs QuackRunner

| Concern | QuackCore (Kernel) | QuackRunner (Muscle) |
| --- | --- | --- |
| **Defines Proof** | ✅ Yes | ❌ No |
| **Owns Ledger** | ✅ Yes | ❌ No |
| **Starts Process** | ❌ No | ✅ Yes |
| **Manages PIDs** | ❌ No | ✅ Yes |
| **Stability** | Constant (Constitution) | Evolutionary |

---

## 🧭 Governance Rules (Non-Negotiable)

1. **Sovereignty First:** All organizational memory must be portable in the local project store.
2. **Atomic Contracts:** Define small, verifiable interfaces.
3. **No Manifest, No Success:** QuackCore logic must never validate a task without a manifest checksum.
4. **Machine-First:** Discovery and Summaries are as important as raw data.
5. **Engine Public, Content Private.**

---

## 🧠 Closing Statement

**QuackCore is the Sovereign Brain.** It does not act, but it ensures that every action taken by an agent or tool is recorded, verified, and auditable. It is the bedrock that allows the "Optimistic Professor" to trust the machine.

---