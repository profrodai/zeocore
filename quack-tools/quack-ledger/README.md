# 🦆 QuackLedger

**A QuackTool for Deterministic Production Lineage Tracking and Operational Memory**

> **QuackLedger records what happened.**
> It does not plan.
> It does not decide.
> It does not optimize.

---

## 🧠 What QuackLedger Is

QuackLedger is a **Ring B QuackTool**.

It consumes **artifacts and manifests** produced by other QuackTools and emits a **ledger of production lineage**, tracking:

* what artifacts were produced
* which root asset they derive from
* where and how they were used
* which assets remain unused

QuackLedger answers one question only:

> **“What has this system actually produced, and how has it been used?”**

---

## ❌ What QuackLedger Is Not

QuackLedger is **not**:

* a workflow engine
* a scheduler or planner
* a dashboard or analytics UI
* a database of record
* a recommendation system
* an autonomous agent

It never:

* triggers tools
* schedules content
* publishes artifacts
* infers intent
* prioritizes work
* modifies upstream data

All judgment and action live in **Ring C**
(Agents, Temporal, Quackchat).

---

## 🧭 Position in the QuackVerse Doctrine

```
┌────────────────────────────────────────────┐
│        EXPERIENCES / ORCHESTRATION         │
│  Quackchat · Temporal · n8n · Agents       │
├────────────────────────────────────────────┤
│               TOOLS (WORKERS)              │
│        ▶ QuackLedger ◀                    │
├────────────────────────────────────────────┤
│              CORE (KERNEL)                 │
│  QuackCore: Schemas · IO · Results        │
└────────────────────────────────────────────┘
```

QuackLedger:

* imports **QuackCore only**
* is executed via **QuackRunner**
* emits **artifacts + manifests**
* is stateless across runs

---

## 🧾 The Role QuackLedger Replaces

Traditional organizations rely on:

* spreadsheets
* tribal knowledge
* “I think we already posted that”
* Slack archaeology

QuackLedger replaces **operations memory** with **artifacts + lineage**.

---

## 🧰 Canonical CLI Surface

QuackLedger does **not** expose a standalone CLI.

All execution happens via the **single canonical CLI**:

```bash
quack ledger <verb> [options]
```

Required verbs:

* `run`
* `validate`
* `doctor`
* `explain`

---

## 🚀 Common Commands

### Generate a production ledger

```bash
quack ledger run ./artifact_store --out ./dist/ledger
```

Produces:

* a structured ledger of produced artifacts
* lineage mappings to root assets
* usage and reuse records
* unused / dormant asset listings

---

### Validate artifact lineage

```bash
quack ledger validate ./artifact_store
```

Checks:

* manifest completeness
* root asset references
* derivation consistency
* missing or orphaned artifacts

---

### Diagnose environment readiness

```bash
quack ledger doctor
```

Reports:

* artifact store accessibility
* manifest schema resolution
* filesystem permissions

---

### Explain a ledger bundle

```bash
quack ledger explain ./dist/ledger/<run-id>/
```

Explains:

* what was produced
* where it came from
* how it flowed through the system
* what remains unused

---

## 📦 Output Artifacts

Each run produces a **ledger artifact bundle**.

Example:

```text
dist/
└── ledger/
    └── run-2025-03-22T09-55-07/
        ├── produced.json
        ├── lineage.json
        ├── usage.json
        ├── unused.json
        └── manifest.json
```

---

### Ledger Semantics

* **Produced** → every artifact ever emitted
* **Lineage** → root asset → derived artifact chains
* **Usage** → where artifacts were consumed (tools, workflows, publishes)
* **Unused** → artifacts with no downstream references

> **Unused does not mean useless.**
> It means *available leverage*.

---

### Manifest Is the System of Record

The `manifest.json` captures:

* source artifact references and hashes
* ledger construction parameters
* produced reports
* timestamps and checksums

If it is not in the manifest, **it is not remembered**.

---

## 🔗 How QuackLedger Fits into Workflows

QuackLedger never orchestrates.

Typical flow:

1. **All tools** emit artifacts + manifests
2. **Artifact store** accumulates history
3. **Quackchat / Agent** requests a ledger snapshot
4. **Temporal** records the request
5. **QuackRunner** executes `quack ledger run`
6. Ledger artifacts + manifest are written
7. **Humans and agents** reason over reality

QuackLedger exits immediately after recording history.

---

## 🧪 The Monday Morning Briefing Test

QuackLedger exists to answer:

> **“What did we actually do last week?”**

Without:

* opening dashboards
* asking Slack
* relying on memory

If QuackLedger cannot produce that answer, the system is broken.

---

## ⚙️ Configuration (Indicative)

Configuration is injected via **QuackCore primitives**.

```yaml
ledger:
  track_unused: true
  include_external_usage: false
  max_history_days: 90
```

Configuration is:

* explicit
* typed
* auditable
* environment-agnostic

---

## 🧭 Governance Rules

1. QuackLedger records — it does not decide
2. No scheduling, planning, or publishing
3. No dashboards or UI
4. No SaaS integrations
5. Emits reports + manifest
6. Uses QuackCore only
7. Runs via the canonical `quack` CLI

---

## 🧠 Closing Statement

QuackLedger exists to eliminate **organizational amnesia**.

It turns:

* “I think we did that” → proof
* scattered artifacts → lineage
* unused work → visible leverage

So that:

* one person can run a media operation
* agents can reason about reality
* audits are trivial
* breaks and vacations do not erase context

QuackLedger does not remember *ideas*.

It remembers **what actually happened** — and nothing more.
