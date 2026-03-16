# 🧠 **Quack Agents**

**Judgment, Logic, and Monologue in the Sovereign Architecture**

> **Agents decide.**
> They do not execute limbs.
> They do not own the artifact store.
> They do not provision infrastructure.
> Agents exist to **manage the digital factory** by applying judgment, policy, and planning.

---

## 🧭 What Quack Agents Are

**Quack Agents are the "Managers" in Ring C** of the QuackVerse.

In the Sovereign Agent Architecture, they act as the primary operators of the system (e.g., OpenClaw). They are reasoning services that:

* **Manipulate Atomic Limbs** in Ring B via the CLI/Runner.
* **Maintain an Internal Monologue** by reading `summary.md` context snippets.
* **Verify Reality** by checking `manifest.json` checksums in the `.quack/` store.
* **Signal Workflows** to Temporal to ensure durability and human-in-the-loop triggers.

Agents answer one question:

> **“Given the current state of the ledger, what mutation should I perform next?”**

---

## ❌ What Quack Agents Are Not

Quack Agents are **not**:

* **Tools (Limbs):** They do not perform the deterministic work (e.g., they don't render video; they tell `QuackVideo` to do it).
* **The System of Record:** They do not own the truth; the local `.quack/` store does.
* **The Watchdog:** They do not handle their own retries or process persistence; Temporal does.
* **The Command:** They do not define the final business goal; the Human Commander does.

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

**Quack Agents live in Ring C.** They sit above the limbs and use Ring A (The Sovereign Brain) to ensure they are not hallucinating.

---

## 🧠 Core Responsibilities

### Agents Do

* **Read Context:** Parse the `summary.md` from the Artifact Store.
* **Self-Teach:** Use the `--discovery` verb on limbs to learn available schemas.
* **Issue Commands:** Trigger Ring B tools and handle the **Async Ticket** (RunID).
* **Verify Proof:** Admit a task is done only when a `manifest.json` is verified.
* **Explain:** Provide a rationale for why a specific limb or parameter was chosen.

### Agents Do Not

* **Lie:** They are prohibited from reporting success without a manifest checksum.
* **Monolith:** They do not perform multi-step jobs in one process; they chain atomic limbs.
* **Silent Fail:** They must escalate to the Human Cockpit (Quackchat) via Temporal when they hit a `QC_ERROR_CODE`.

---

## 🧠 Agents vs Tools (The Manager/Limb Distinction)

| Aspect | Agent (Manager) | Tool (Limb) |
| --- | --- | --- |
| **Role** | Management & Judgment | Mutation & Execution |
| **Logic** | Heuristic & Policy | Deterministic & Atomic |
| **Memory** | Reasoning Monologue | manifest.json + summary.md |
| **Handshake** | Issues the Ticket (RunID) | Performs the Work |
| **Success** | Interprets the Summary | Signs the Manifest |

---

## 🔌 The Sovereign Handshake

Agents follow the **Authoritative Job-State Pattern**:

1. **Discovery:** Agent runs `quack --discovery` to map its current "limbs."
2. **Action:** Agent triggers a limb and stores the **RunID Ticket**.
3. **Observation:** Agent polls `quack status <RunID>` via Temporal.
4. **Integration:** Agent reads `explain <RunID>` to ingest the result into its reasoning.

---

## 🧠 Decision Payloads & The Ledger

Agents do not just "think" in a vacuum. Every decision that results in a tool call must be recorded in the project-local `ledger.db`.

A decision payload includes:

* **Intent:** The high-level goal (e.g., "Normalize audio for Pillar A asset").
* **Limb Selection:** Why `QuackVideo` was chosen over `QuackAudio`.
* **Parameter Rationale:** Why a specific LUFS or codec was selected.
* **The RunID Link:** The connection to the resulting Artifact Store entry.

---

## 🧭 Governance Rules (Non-Negotiable)

1. **Verify or Deny:** Success is a manifest checksum, not a guess.
2. **Respect the Context Window:** Use `summary.md` to avoid "context shredding."
3. **Atomic Limbs Only:** Chain small, verifiable mutations.
4. **Discoverable Limbs:** Never hardcode tool flags; always use `--discovery`.
5. **Human Escalation:** When `QC_*` errors occur, signal the Cockpit for steering.
6. **Local sovereignty:** Read and write only to the local `.quack/` store.

---

## 🧠 Closing Statement

**Agents are the managers of the Digital Employee Factory.**
They plan the production line, monitor the atomic limbs, and report back to the Human Commander. By strictly separating **Judgment (Agent)** from **Mutation (Tool)** and **Proof (Core)**, the organization remains auditable, durable, and genuinely sovereign.