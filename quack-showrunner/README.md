# 🎬 **Quackshowrunner**

**The Infrastructure-as-Code Engine for Sovereign Agent Architectures**

Quackshowrunner wires the Sovereign Stack together.

It does **not** think, decide, render, or create content.

It provisions, connects, and operates the **local-first runtime** in which Sovereign Agents (e.g., OpenClaw) manage organizational operations.

---

## 🧠 **What Quackshowrunner Is**

Quackshowrunner is the **infrastructure layer of the QuackVerse**.

In the Sovereign Agent era, it is the **declarative blueprint** for deploying an always-on "Digital Employee Factory" on operator-owned hardware (e.g., Mac Mini clusters). It ensures that while tools are atomic and agents are autonomous, the underlying environment is durable, reproducible, and portable.

Quackshowrunner answers one question only:

> **“What services are running on this local node, how are they secured, and how do we replicate the entire environment on a new machine?”**

---

## ❌ **What Quackshowrunner Is Not**

Quackshowrunner does **not** contain:

* **Sovereign Agent Logic:** It deploys OpenClaw but doesn't write its prompts.
* **Organizational Memory:** It deploys the database but doesn't own the `.quack/ledger.db`.
* **Atomic Limb Logic:** It doesn't know how to render video or ingest media.
* **Business Logic:** It doesn't define what a "Lead" or a "Course" is.

---

## 🧭 **Position in the QuackVerse**

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

══════════════════════════════════════════════
RUNTIME / OPERATIONS (Outside the Rings)
Quackshowrunner — Infrastructure-as-Code
══════════════════════════════════════════════

```

**Quackshowrunner lives outside the rings.** It is the "Physical Factory" that houses the Sovereign Brain, the Atomic Limbs, and the Agentic Manager.

---

## 🏗 **Responsibilities**

### **1️⃣ Local Service Provisioning**

* **Temporal & QuackRunner:** Provisions the durable process OS and the execution muscle.
* **n8n:** Wires the integration fabric for external side-effects (notifications, SaaS posting).
* **Sovereign Agent Runtimes:** Deploys always-on environments for OpenClaw and other digital employees.
* **Business Primitives:** Provisions **Twenty CRM** (State) and **Docusaurus** (Knowledge KB).

### **2️⃣ Sovereign Wiring & Security**

* **Local Networking:** Isolates the `.quack/` store and internal service traffic.
* **Credential Injection:** Safely injects scoped tokens and service account keys into Agent runtimes.
* **Local Object Storage:** Provisions MinIO or local FS mounts for the **Artifact Store**.

### **3️⃣ Portability & "Nuclear Recovery"**

* **Idempotent Setup:** Ensures `quackshowrunner up` produces an identical environment every time.
* **Portable Backups:** Manages snapshots of the `.quack/` directory and Postgres state.
* **Environment Parity:** Enables an operator to move their entire "Sovereign Stack" from a laptop to a dedicated Mac Mini in minutes.

---

## 🧠 **Runtime Components (The Sovereign Stack)**

### **Temporal — The Watchdog**

Temporal owns the **authoritative status** of Async Tickets. Quackshowrunner ensures Temporal is always-on to monitor background limbs.

### **OpenClaw / Agents — The Manager**

Quackshowrunner deploys the Agent services. It provides them with the **limbs.json** (Discovery) and the credentials needed to act.

### **The Sovereign Store (.quack/)**

Quackshowrunner manages the persistent volumes where the **Ledger** and **Artifacts** live. It ensures this directory is protected and backed up.

---

## 📦 **Directory Structure**

```text
quackshowrunner/
├── compose/                # Sovereign Stack definitions
│   ├── core.yml           # Temporal, Postgres, QuackRunner
│   ├── agents.yml         # OpenClaw & Role-bound services
│   ├── store.yml          # MinIO / Local FS mounts
│   └── business.yml       # Twenty CRM & Docusaurus
├── scripts/                # The Operator's Toolbelt
│   ├── bootstrap.sh       # Hardware prep (Docker, env)
│   ├── backup-sovereign.sh # Snapshot .quack/ and DBs
│   └── restore-sovereign.sh # Reconstitute stack on new hardware
├── env/                    # Local environment config
└── README.md

```

---

## 🧭 **Governance Rules (Non-Negotiable)**

1. **Infrastructure is Silent:** Quackshowrunner never executes business tasks; it only provides the room for them to happen.
2. **Local-First Priority:** Default all storage and connectivity to local-first; cloud is the exception.
3. **No Logic Leakage:** If you have to write a "Prompt" or a "Rule" in a YAML file here, it belongs in an Agent or a Limb instead.
4. **Credential Isolation:** Agents never see the master host keys; they only see scoped tokens injected by the showrunner.
5. **Artifact Store is Sacred:** The `.quack/` directory is the only state that matters for portability.

---

## 🧠 **Closing Statement**

**Quackshowrunner is the Physical Factory.**
**Temporal is the flight recorder.**
**The Artifact Store is the memory.**
**Sovereign Agents are the managers.**
**Atomic Limbs are the machines.**

Quackshowrunner ensures that the factory exists, is powered, and is ready for the Commander's intent. It is the foundation of **Infrastructure Sovereignty**.