# 🛠️ **QuackTools**

**Atomic Limbs of the Sovereign Agent Architecture**

> **Tools do the work.**
> They do not decide *what* to do.
> They do not decide *when* to do it.
> They do not talk to each other.
> QuackTools are **Atomic Limbs** designed to be manipulated by Sovereign Agents (e.g., OpenClaw). They turn structured instructions into verifiable proof of work.

---

## 🧠 What QuackTools Are

**QuackTools are granular, domain-focused workers** in Ring B of the QuackVerse.

Each QuackTool:

* performs **one atomic limb operation**
* consumes **structured inputs**
* issues **Async Tickets** for long-running jobs
* emits **verifiable manifests + LLM-optimized summaries**
* is **deterministic** and **stateless**
* imports **QuackCore only**

QuackTools answer one question:

> **“Given this atomic instruction, mutate the project state and provide proof.”**

---

## ❌ What QuackTools Are Not

QuackTools are **not**:

* agents or managers
* planners or sequencers
* long-running autonomous services
* UIs

They **never**:

* decide which tool to run (The Agent decides)
* sequence steps (Temporal/Agent decides)
* lie about completion (The Ticket/Manifest prevents this)
* store canonical organizational state (The Ledger/Store does)

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
│    Ticket System · QuackStore (.quack/) · QuackLedger    │
└──────────────────────────────────────────────────────────┘

```

**QuackTools live entirely in Ring B.** They are the "Limbs" triggered by the "Manager" in Ring C.

---

## 🧠 Core Responsibilities (The Handshake)

### Tools Do

* **Issue Tickets:** Return a `RunID` immediately for async tasks.
* **Mutate State:** Perform the bounded transformation.
* **Provide Proof:** Emit a `manifest.json` with a verified checksum.
* **Update Context:** Write a `summary.md` (LLM-snippet) so agents understand the result.
* **Self-Describe:** Implement `--discovery` for machine-readable capability mapping.

---

## 🧠 Tools vs Agents (The Manager/Limb Distinction)

| Aspect | Tool (Limb) | Agent (Manager) |
| --- | --- | --- |
| Purpose | Execute Mutation | Decide & Sequence |
| State | Stateless | Stateful Monologue |
| Logic | Atomic/Deterministic | Heuristics & Policy |
| Interface | CLI Grammar | Reasoning & Intent |
| Output | Manifest + Summary | Decisions + Signals |

> **The Agent (Manager) plans. The Tool (Limb) produces.**

---

## 🧠 Execution Model (Sovereign Edition)

QuackTools are anchored to the local project's **Artifact Store**.

**The Async Handshake:**

1. **Trigger:** Agent calls `quack <tool> <limb>`.
2. **Ticket:** Tool returns `RunID` and background-executes.
3. **Poll:** Agent monitors `quack status <RunID>`.
4. **Verify:** Tool writes `manifest.json`. Agent admits success only upon verification.

---

## 🧠 The Sovereign Artifact Store (`.quack/`)

Every tool operates within the local project boundary:

* **Manifests:** Machine-readable proof of work.
* **Summaries:** LLM-optimized context snippets (`summary.md`).
* **Lineage:** Every run is recorded in the local `ledger.db`.

---

## 🧰 Tool Interface Doctrine

### One Canonical CLI

There is exactly **one** canonical CLI entry point:

```bash
quack <tool> <limb> [options]

```

### Mandatory Agentic Verbs

Every QuackTool must implement:

* `status <RunID>` — Report progress of an async ticket.
* `explain <RunID>` — Output the `summary.md` for LLM context.
* `--discovery` — Output JSON-formatted capability and schema map.
* `validate` — Check inputs before issuing a ticket.
* `doctor` — Auto-fix local environment and dependencies.

---

## 📦 Monorepo Layout

```text
quackverse/
├── quackcore/              # Ring A: Ticket system & Ledger
├── quacktools/             # Ring B: Atomic Limbs
│   ├── quack-video/
│   ├── quack-ingest/
│   └── ...
├── quackrunner/            # Ring C: Local execution gateway
└── README.md

```

---

## 🧭 Governance Rules (Non-Negotiable)

1. **Everything Emits Proof:** No manifest = it didn't happen.
2. **Atomic Over Monolithic:** Prefer many small verbs over one complex command.
3. **Async by Default:** Issue tickets for any task exceeding 2 seconds.
4. **LLM-First context:** Always produce a `summary.md` for the agent.
5. **Local Portability:** Store all artifacts and logs in the local `.quack/` store.
6. **No Silent Failures:** Tools must return `QC_ERROR_CODES` for agents to handle.
7. **Discovery is Sacred:** Agents must be able to self-teach via `--discovery`.

---

## 🧠 Closing Statement

**QuackTools are the limbs of the Sovereign Organization.**

They are built to be directed by always-on agents, tracked by durable workflows, and audited by humans. By separating the **judgment (Agent)** from the **mutation (Tool)**, we create a system that is scalable, auditable, and genuinely sovereign.