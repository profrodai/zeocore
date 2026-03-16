# 🦆 QuackLedger

**The Sovereign Brain's Memory & Lineage Repository**

> **QuackLedger records reality.**
> It does not plan.
> It does not decide.
> It does not hallucinate.

---

## 🧠 What QuackLedger Is

QuackLedger is a **Ring A Kernel Primitive** implemented as a **Ring B Atomic Limb**. It is the authoritative memory of the QuackVerse.

It manages the project-local `ledger.db` within the `.quack/` store, tracking the **immutable production lineage** of every action taken by the organization. It connects **Root Assets** to their **Derived Artifacts** through the trail of **Verified Manifests**.

QuackLedger answers one question only:

> **“What is the verified history of this project, and where is the proof?”**

---

## ❌ What QuackLedger Is Not

QuackLedger is **not**:

* **A Manager:** It does not decide what to do next (Agents do).
* **A Database of Record:** It is a ledger of *events* and *artifacts*; business state lives in a CRM.
* **A Workflow Engine:** It does not manage retries or timers (Temporal does).
* **A Dashboard:** It is a machine-readable truth source, not a UI.

---

## 🧭 Position in the QuackVerse Doctrine

```
┌──────────────────────────────────────────────────────────┐
│             RING C — AGENTIC CONTROL                     │
│    OpenClaw (Manager) · Temporal · Quackchat (Cockpit)   │
├──────────────────────────────────────────────────────────┤
│             RING B — ATOMIC LIMBS (WORKERS)              │
│        ▶ QuackLedger ◀                                   │
├──────────────────────────────────────────────────────────┤
│             RING A — THE SOVEREIGN BRAIN                 │
│    Ticket System · QuackStore (.quack/) · QuackLedger    │
└──────────────────────────────────────────────────────────┘

```

QuackLedger is the bridge between the **Kernel's state** (Ring A) and the **Agent's reasoning** (Ring C).

---

## 🧠 Core Responsibilities (The Memory Handshake)

### 1️⃣ Lineage Tracking

QuackLedger maps the "Parent-Child" relationship of artifacts. It ensures that a LinkedIn post (child) can be traced back to a specific timestamp in a Riverside recording (root).

### 2️⃣ Manifest Indexing

Every time a limb (e.g., `QuackVideo`) completes a job, QuackLedger indexes the resulting `manifest.json`. It verifies the checksum before committing the event to the `ledger.db`.

### 3️⃣ Usage Audit

It records where and how artifacts were consumed. If an agent asks, "Have we used this clip for Prof Rod yet?", QuackLedger provides the definitive "Yes" or "No."

---

## 🧰 Canonical CLI Surface

QuackLedger is invoked by the **Sovereign Agent** to verify history before taking new actions.

```bash
quack ledger <limb> [options]

```

### Mandatory Agentic Verbs

* `status` — Report on the integrity of the local `ledger.db`.
* `query` — Search for artifacts based on tags, lineage, or parent IDs.
* `explain` — Output the `summary.md` for a specific run or lineage chain.
* `register` — Formally commit a verified manifest to the project history.
* `doctor` — Repair orphaned artifacts or broken lineage links.
* `--discovery` — Output machine-readable schemas for ledger queries.

---

## 🚀 Common Atomic Limbs

### Query Lineage (Agent Context)

```bash
quack ledger query --parent <RootAssetID> --type clip

```

### Register Manifest (The Proof)

```bash
quack ledger register --manifest .quack/runs/run_abc_123/manifest.json

```

---

## 📦 Output Artifacts

Each run produces a **ledger snapshot** or **lineage report**.

```text
.quack/
└── runs/
    └── run_ledger_xyz/
        ├── lineage.json    <-- The Parent-Child tree
        ├── usage.json      <-- Publishing & consumption history
        ├── summary.md      <-- LLM-optimized history snippet
        └── manifest.json   <-- Verification of the query itself

```

---

## 🔗 How QuackLedger Kills Hallucinations

1. **The Checksum Gate:** QuackLedger refuses to register any run that lacks a verified manifest checksum.
2. **Context Injection:** When an agent (OpenClaw) starts a session, it runs `quack ledger explain --recent`. The resulting `summary.md` gives the agent the "Truth" of what happened while it was offline.
3. **Lineage Enforcement:** If an agent tries to process a file that isn't in the ledger, the command fails with `QC_VAL_INVALID_ID`.

---

## 🧪 The Monday Morning Briefing Test

QuackLedger exists to answer:

> **“What exactly did we produce last week, and which root assets are still untapped?”**

If QuackLedger cannot provide the proof without a human checking a folder, the system is broken.

---

## 🧭 Governance Rules

1. **Proof Over Memory:** If it isn't in the Ledger, it didn't happen.
2. **Atomic Registration:** Every limb must register its result with the ledger upon completion.
3. **Local Sovereignty:** The `ledger.db` must live inside the project's `.quack/` folder.
4. **Machine-First:** Ledger queries must be optimized for Agent consumption (`JSON` + `summary.md`).
5. **Immutable History:** Once a manifest is registered, its lineage entry is locked.

---

## 🧠 Closing Statement

**QuackLedger is the organizational memory.** It eliminates amnesia by turning scattered files into a verifiable, auditable chain of truth. It allows the Sovereign Agent to reason about the past so it can safely execute the future.