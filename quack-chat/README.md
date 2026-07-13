# 🦆 Quackchat

**The Human Cockpit & Oversight Interface of the QuackVerse**

> **Quackchat is where intent enters the system and where judgment is final.**
> It does not execute limbs.
> It does not manage tickets.
> It does not contain agent logic.
> It allows the Human Commander to *observe, steer, and approve* the actions of Always-On Agents.

---

## 🧠 What Quackchat Is

**Quackchat is the interaction layer** for AI-first organizations. In the Sovereign Agent Architecture, it serves as the **Cockpit** where the Human Operator supervises the "Manager" (e.g., OpenClaw).

It is a **TypeScript application** (Web + CLI) that allows humans to:

* **Trigger Intent:** Signal Temporal to begin a specific production workflow.
* **Observe the Monologue:** Read the agent’s reasoning and `summary.md` context snippets.
* **Final Approval:** Intercept high-risk async tickets (payments, publishing, data deletion).
* **Lineage Inspection:** Browse the local `.quack/` store and the `QuackLedger`.
* **Escalation Point:** Act as the "Human Oracle" when an agent hits a `QC_ERROR_CODE`.

---

## ❌ What Quackchat Is Not

Quackchat is **not**:

* a chatbot framework or "wrapper."
* a tool runner (QuackRunner/Limbs do this).
* the system of record (The Artifact Store does this).
* the watchdog (Temporal does this).

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

**Quackchat lives in Ring C.** It is an interface into the "Brain" and the "Manager."

---

## 🧠 Core Responsibilities

---

### 1️⃣ Intent & Steering

Quackchat is the entry point for "Commander's Intent." It structures human requests and forwards them to **Temporal** to initiate or steer workflows. It is the primary way a human says, "Mator, let's start Pillar A for this week."

### 2️⃣ Operational Visibility

Quackchat provides a window into the **Sovereign Brain**. It queries the local `ledger.db` and Temporal state to show:

* What agents are currently "thinking."
* The status of active **Async Tickets** (RunIDs).
* Visualizations of artifact lineage.

### 3️⃣ The Approval Gate

For actions flagged by **Sovereign Safety Standards** (e.g., financial transactions, public posting), Quackchat holds the workflow. The agent proposes a decision; the human clicks "Approve" to release the ticket.

### 4️⃣ Explainability & Audit

Quackchat renders the **LLM-optimized summaries** and full manifests. It answers the human's question: *"Why did the agent decide to use this specific clip?"* by pulling the reasoning recorded in the ledger.

---

## 🧪 The Handshake Workflow

1. **Intent:** Human enters "Research the latest OpenClaw updates" in **Quackchat**.
2. **Signal:** Quackchat signals **Temporal** to start the Research Workflow.
3. **Reasoning:** Agent (OpenClaw) proposes a search plan; Human reviews in the Cockpit.
4. **Execution:** Temporal triggers **QuackResearch** limbs via Async Tickets.
5. **Review:** Quackchat displays the `summary.md` and the final **QuackBrief** for human consumption.

---

## 📦 Project Structure (Indicative)

```text
quackchat/
├── apps/
│   ├── web/              # React/Next.js Dashboard
│   └── desktop/          # Local tray app for notifications
├── src/
│   ├── api/              # Local Ledger & Temporal clients
│   ├── components/       # Artifact & Lineage renderers
│   ├── safety/           # Approval interceptor logic
│   └── store/            # Local project state (.quack/ observer)
└── README.md

```

---

## 🎓 Pedagogical Mandate

Quackchat is the **Sovereign Classroom**. It must make the invisible visible. It teaches the operator how the architecture functions by exposing the relationship between tickets, manifests, and agent reasoning.

---

## 🧭 Governance Rules (Non-Negotiable)

1. **No Shadow Logic:** Quackchat never calculates; it only displays and signals.
2. **Read-Only Artifacts:** The UI never modifies an artifact; only limbs can mutate state.
3. **The Human is the Circuit Breaker:** High-risk `QC_ERROR_CODES` must escalate here.
4. **Sovereign Privacy:** The UI works entirely against the local `.quack/` store.
5. **Transparency First:** The Agent's internal monologue must be legible.

---

## 🧠 Closing Statement

**Quackchat is the eye and the hand of the Commander.** It turns a complex swarm of autonomous agents into a manageable, steerable, and auditable business operation. It ensures that while the agents are sovereign, the human is in charge.