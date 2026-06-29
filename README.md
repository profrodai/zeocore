# 🦆 QuackVerse

**The Sovereign Operating System for Always-On Agents**

> Open-source the engine.
> Atomicize the limbs.
> Handshake with tickets.
> Verify with manifests.
> Own the infrastructure.

QuackVerse is an architectural doctrine for building **Sovereign Agent Architectures**. It turns raw compute into a **Digital Employee Factory** where always-on agents (like OpenClaw) act as the managers of deterministic, auditable limbs.

---

## ✨ One Sentence

**QuackVerse provides the local-first "Userland" for Sovereign Agents by separating kernel contracts, atomic CLI limbs, and an authoritative artifact store.**

---

## 🧭 System Model (QuackVerse): The Sovereign Stack

QuackVerse is implemented using **three strict architectural rings**, anchored by a local **Artifact Store**.

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

---

## 🟦 Ring A — Core (The Sovereign Brain)

The **Constitutional Layer**. In the Sovereign Agent era, Ring A moves from "definition" to "authoritative proof."

#### `.quack/` (The Artifact Store)

The system of record lives hidden within each project.

* **`ledger.db`**: The immutable lineage of every action taken.
* **`runs/`**: Individual directories for every `RunID`.
* **`limbs.json`**: The discovery manifest (tells Agents what limbs they have).

#### The Ticket System (Async Handshake)

To prevent agents from hallucinating success, all long-running tasks follow the **Ticket Protocol**:

1. **Trigger:** Agent calls a limb; tool issues a `RunID` ticket and exits.
2. **Poll:** Agent must poll `quack status <RunID>` for progress.
3. **Verify:** Success is only valid when the tool writes a `QC_MANIFEST_VERIFIED` checksum.

---

## 🟨 Ring B — Atomic Limbs (The Hands)

Ring B tools are no longer monolithic "batch" scripts; they are **Atomic Limbs**.

* **Granular Verbs:** `add-slide`, `cut-clip`, `normalize-audio`.
* **Stateless:** They do not remember the past; they read the current state from the `.quack/` store.
* **Machine-First:** Every limb implements `--discovery` to output its own documentation for LLM consumption.

> **QuackLimbs answer:** > *“Given this specific instruction, mutate the project state and provide proof.”*

---

## 🟩 Ring C — Experience (The Manager & Cockpit)

#### Sovereign Agents (e.g., OpenClaw)

The **Primary User**. The Agent is the "Manager" that sequences the Atomic Limbs of Ring B based on the "Sovereign Agent Guide" (Pillar A).

#### Temporal (The Watchdog)

The **Durable Memory**. Temporal tracks the long-running async tickets. If an Agent crashes or the power fails, Temporal ensures the "Manager" knows exactly where to resume.

#### Quackchat (The Cockpit)

Reframed from a "Chatbot" to a **Human Oversight Interface**. It is where the human "Operator" monitors the Agent’s "Monologue" and approves high-risk actions (spending money, publishing content).

---

## 🔌 Communication Doctrine: The Handshake

1. **Discovery (Pre-flight):** Agent runs `quack --discovery` to learn available limbs.
2. **The Ticket (Trigger):** Agent triggers an async limb and receives a `RunID`.
3. **The Proof (Manifest):** Tool emits a `manifest.json` + `summary.md`.
4. **The Monologue (Context):** Agent reads the `summary.md` (LLM-optimized snippet) to update its internal context without parsing raw data.

---

## 🧰 Canonical CLI Surface

Every tool in the QuackVerse follows the **Atomic Grammar**:

```bash
quack <tool> <limb> [options]

```

**Mandatory Verbs for Agents:**

* `status <RunID>`: Check the async ticket state.
* `explain <RunID>`: Output the `summary.md` for LLM context.
* `doctor`: Auto-fix the local environment.
* `--discovery`: Output machine-readable capability map.

---

## 📦 Monorepo Layout (Sovereign Edition)

```text
quackverse/
├── quackcore/              # Ring A: Ticket system & Ledger
├── quacktools/             # Ring B: Atomic Limbs (Video, Ingest, etc.)
├── quackrunner/            # Ring C: Local execution gateway
├── quackchat/              # Ring C: Operator cockpit (TS/Web)
├── agents/                 # Ring C: Sovereign Agent definitions (OpenClaw config)
└── README.md

```

---

## 🧭 Governance Rules (Agentic OS)

1. **Artifacts are Canon:** If it isn't in the `.quack/` store, it never happened.
2. **No Hallucinations:** Success requires a verified manifest checksum.
3. **Atomic Limbs:** Prefer 10 small commands over 1 big command with 10 flags.
4. **LLM Context First:** Every run must produce a `summary.md` for the agent.
5. **Local-First:** The system of record must be portable within the project folder.
6. **Async by Default:** Respect the agent’s context window; issue tickets for long jobs.
7. **Sovereignty:** No cloud dependency for core organizational memory.

---

## 🧠 Closing Statement

QuackVerse is built to empower **Sovereign Operators**.

* **QuackCore** is the constitution.
* **The Artifact Store** is the organizational memory.
* **Atomic Limbs** are the digital hands.
* **Sovereign Agents** are the digital managers.
* **The Human** is the Commander-in-Chief.

**The Manager plans. The Limbs produce. The Human judges. The Organization compounds.**

---

**Would you like me to update the specific "Governance Rules" or "Communication Doctrine" for any of the other Ring B tools (Video, Tutorial, Research) to reflect this atomic shift?**