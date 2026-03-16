# 🏃 **QuackRunner**

**The Execution Gateway & Ticket Manager of the QuackVerse**

> **QuackRunner executes.**
> It does not decide *what* to run.
> It does not decide *when* to run.
> It does not plan workflows.
> QuackRunner is the **hardened muscle** of the QuackVerse, responsible for managing the lifecycle of **Atomic Limbs** and their background processes.

---

## 🧠 What QuackRunner Is

**QuackRunner is a stateful execution service** in Ring C. In the Sovereign Agent Architecture, it acts as the bridge between the **Manager (Agent)** and the **Limbs (Tools)**.

It provides a **hardened, auditable execution surface** that handles the heavy lifting of background process management, ensuring that long-running jobs are isolated, tracked, and verified.

QuackRunner answers one question only:

> **“Execute this atomic limb, issue a Ticket, and monitor the process until the Manifest is signed.”**

---

## ❌ What QuackRunner Is Not

QuackRunner is **not**:

* **The Manager:** It does not select tools (Agents do).
* **The Watchdog:** It does not own the high-level business retry logic (Temporal does).
* **The Brain:** It does not store organizational memory (The Local Ledger does).
* **The Integration Fabric:** It does not talk to SaaS APIs (n8n does).

---

## 🧭 Position in the QuackVerse

```
┌──────────────────────────────────────────────────────────┐
│             RING C — AGENTIC CONTROL                     │
│    OpenClaw (Manager) · Temporal · QuackRunner (Muscle)  │
├──────────────────────────────────────────────────────────┤
│             RING B — ATOMIC LIMBS (WORKERS)              │
│    QuackIngest · QuackDistro · QuackVideo · QuackDeck    │
├──────────────────────────────────────────────────────────┤
│             RING A — THE SOVEREIGN BRAIN                 │
│    Ticket System · QuackStore (.quack/) · QuackLedger    │
└──────────────────────────────────────────────────────────┘

```

**QuackRunner lives in Ring C.** It sits between the Agent's reasoning and the Tool's mutation.

---

## 🧠 Core Responsibilities

### 1️⃣ Ticket & PID Management

QuackRunner implements the **Async Handshake**. When a long-running limb is triggered:

* It spawns the background process.
* It captures the **PID** (Process ID).
* It registers the **RunID Ticket** in the local `.quack/` store.

### 2️⃣ Isolated Execution

It ensures that limbs run in a clean environment (venv, container, or sandbox) with:

* Injected least-privilege credentials.
* Enforced timeouts and resource limits.
* Captured `stdout/stderr` streamed to the log store.

### 3️⃣ Verification & Handover

Once a limb exits, QuackRunner:

* Verifies the presence of the `manifest.json`.
* Validates the checksum of the artifacts.
* Triggers the creation of the `summary.md` (Agent Context).
* Updates the **RunResult** status in the Ledger.

---

## 🏃 The Execution Model (Agentic)

1. **Request:** Agent/Temporal sends a `RunRequest` to QuackRunner.
2. **Launch:** QuackRunner issues a **RunID**, starts the tool, and returns the Ticket immediately.
3. **Monitor:** QuackRunner tracks the PID. If the process dies without a manifest, it marks the run as `QC_SYS_PID_LOST`.
4. **Finalize:** Upon success, QuackRunner signals the Agent/Temporal that the **Proof of Work** is ready for inspection.

---

## 🧠 API Surface

### Canonical Agentic Endpoints

* `POST /runs`: Trigger a limb (returns a Ticket).
* `GET /runs/{run_id}/status`: Query the current state (Pending/Running/Success/Error).
* `GET /runs/{run_id}/explain`: Retrieve the `summary.md` for LLM context.
* `GET /runs/{run_id}/logs`: Stream the execution logs.

---

## 🧭 Governance Rules (Non-Negotiable)

1. **No Manifest, No Success:** QuackRunner never reports success unless the manifest checksum is verified.
2. **Isolation is Mandatory:** Tools must run in isolated environments to prevent local state pollution.
3. **Logs are First-Class:** Every run must produce an auditable log stream.
4. **PID Authority:** QuackRunner is the authoritative source for whether a background limb is "Alive."
5. **Machine-First:** All outputs must be optimized for Agent consumption (`QC_*` codes and JSON).
6. **Local Sovereignty:** All execution data must be written to the project's local `.quack/` store.

---

## 🧠 Closing Statement

**QuackRunner is the muscle that moves the Sovereign Organization.** It takes the abstract plans of the Agent and turns them into real, auditable mutations of data. It ensures that execution is not just a "demo," but a robust, industrial-grade process that provides the proof the organization needs to scale.

---

**Next Step:** QuackRunner is now aligned with the Agentic OS pivot. Would you like to proceed with the update for **QuackLedger** to formalize how it tracks these results in the "Sovereign Brain"?