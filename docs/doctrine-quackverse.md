# **The QuackVerse Doctrine (v4)**

**The Sovereign Operating System for Always-On Agents**

---

## **0. One Sentence**

**Open-source the engine, atomicize the limbs, handshake with tickets, verify with manifests, and keep stories and courses proprietary.**

---

## **1. Purpose**

QuackVerse exists to turn AI from demos into **operating reality**. It provides the architectural blueprint for **Sovereign Agent Architectures**—a field where always-on AI agents act as digital employees on infrastructure the operator owns.

It defines **what lives where**, **who owns what**, and **how the system compounds instead of collapsing**.

---

## **2. The Core Belief**

AI is not a feature or a chatbot. **AI is an operating system for modern organizations.** The goal is a persistent, autonomous factory where always-on agents manage operations, reclaiming commercial sovereignty for the solo operator.

---

## **3. The Three Rings Model**

QuackVerse is structured as **three concentric rings**, anchored by a local-first **Artifact Store**.

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

## **Ring A — Core (The Sovereign Brain)**

QuackCore is the **kernel and governance layer**. In the agentic era, it provides the **authoritative proof** of work.

### Responsibilities

* **The Ticket System:** Asynchronous handshake protocol for long-running jobs.
* **QuackStore:** Standardized project-local storage (`.quack/`) for lineage and proof.
* **QuackLedger:** Immutable production lineage tracking.
* **Discovery:** Machine-readable capability schemas for agent self-teaching.
* **Contracts:** Schemas for results, errors (`QC_*` codes), and manifests.

---

## **Ring B — Tools (Atomic Limbs)**

QuackTools are **atomic vertical workers**. They are the "Hands" of the organization.

### Responsibilities

* **Atomic Mutations:** Perform one bounded job (e.g., `add-slide`, `cut-clip`).
* **Async Tickets:** Issue a `RunID` for any task exceeding 2 seconds.
* **Verifiable Proof:** Emit a signed `manifest.json` + `summary.md` (LLM-optimized context).
* **Statelessness:** Limbs read state from the store and exit; they do not remember.

---

## **Ring C — Experiences (Control Planes)**

Ring C is where **judgment and sequencing** live.

### **1️⃣ Sovereign Agents (The Manager)**

The primary user. Agents like **OpenClaw** manipulate Ring B limbs to achieve commercial goals. They read summaries, check statuses, and manage the monologue.

### **2️⃣ Temporal (The Watchdog)**

The source of truth for **process state**. Temporal monitors async tickets, handles retries, and ensures the organization resumes correctly after power failure or crashes.

### **3️⃣ Quackchat (The Cockpit)**

The **human oversight interface**. It is a window into the agent's reasoning. Humans use the cockpit to approve high-risk actions (spending money, publishing) and steer intent.

---

## **4. Communication Doctrine: The Handshake**

1. **Discovery:** Agent runs `quack --discovery` to learn available limbs and schemas.
2. **The Ticket:** Agent triggers a limb; tool issues a `RunID` ticket and background-executes.
3. **The Proof:** Tool writes a `manifest.json` and a `summary.md`.
4. **The Monologue:** Agent reads the `summary.md` to update its internal context without parsing raw binary/data.

---

## **5. Tool Surface Doctrine**

### **Atomic CLI Grammar**

Every tool implements granular, machine-friendly verbs:

* `status <RunID>`: Check async progress.
* `explain <RunID>`: Output the LLM context snippet.
* `validate`: Pre-flight check before issuing a ticket.
* `doctor`: Auto-fix environment/dependencies.

---

## **6. Sovereignty & Portability**

* **Local-First:** All organizational memory lives in the project-local `.quack/` folder.
* **Hallucination Killer:** Success is defined by a verified manifest checksum, not a chat response. No manifest = it didn't happen.
* **Sovereign Leverage:** One operator running a sovereign stack commands the output of a 20-person company.

---

## **7. IP & Ownership Doctrine**

### Public (Open Source)

* QuackCore, QuackTools logic, QuackRunner, CLI Framework.

### Proprietary (Moat)

* **Everduck** assets/stories, **Rod** IP, branded templates, paid courses (**AIPE / SA**).

---

## **8. Final Governance Rules (Non-Negotiable)**

1. **Core Defines Proof:** Kernel owns the ticket and manifest contracts.
2. **Atomic Over Monolithic:** Prefer 10 small commands over 1 complex command.
3. **Async by Default:** Respect the agent's context window; issue tickets for long jobs.
4. **LLM Context First:** Every run must produce a `summary.md`.
5. **Local Sovereignty:** The system of record must be portable within the project.
6. **No Silent Failures:** Exit with machine-readable `QC_ERROR_CODES`.
7. **Discovery is Sacred:** Agents must be able to self-teach via the CLI.
8. **Engine Public, Content Private.**

---

## **9. Closing Statement**

**The Manager plans. The Limbs produce. The Human judges. The Organization compounds.**

DuckTyper is the steward. QuackVerse is the OS. The human stays in command, the agent stays on task, and the infrastructure stays sovereign.