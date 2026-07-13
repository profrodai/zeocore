# 🦆 QuackBrief

**A QuackTool for Deterministic Executive Briefing Compilation from Research Artifacts**

> **QuackBrief compiles structured research artifacts into human-readable briefings.**
> It does not think.
> It does not prioritize strategy.
> It does not decide what matters.

---

## 🧠 What QuackBrief Is

QuackBrief is a **Ring B QuackTool**.

It consumes **research artifacts** produced by upstream workers (e.g. `QuackResearch`) and emits **executive briefing artifacts**, such as:

* daily or weekly briefings (Markdown / PDF)
* lens-filtered digests
* optionally narrated audio briefs
* structured summaries suitable for human review

Each execution emits:

* briefing files
* a manifest describing sources, lenses, and compilation rules

QuackBrief answers one question only:

> **“Given these research artifacts and these lenses, compile a readable briefing.”**

---

## ❌ What QuackBrief Is Not

QuackBrief is **not**:

* a research engine
* a prioritization system
* a strategist or planner
* an autonomous agent
* a recommendation engine
* a dashboard or UI
* a publishing tool

It never:

* decides which topic Rod should pursue
* ranks ideas by business value
* filters based on hidden heuristics
* publishes content
* triggers workflows
* mutates upstream artifacts

All judgment, selection, and intent live in **Ring C**
(Agents, Temporal, Quackchat).

---

## 🧭 Position in the DuckTyper / QuackVerse Doctrine

```
┌────────────────────────────────────────────┐
│        RING C — EXPERIENCES / CONTROL      │
│  Quackchat · Temporal · n8n · Agents       │
├────────────────────────────────────────────┤
│        RING B — TOOLS (WORKERS)            │
│        ▶ QuackBrief ◀                     │
├────────────────────────────────────────────┤
│        RING A — CORE (KERNEL)              │
│  QuackCore: FS · Schemas · Results        │
└────────────────────────────────────────────┘
```

QuackBrief:

* imports **QuackCore only**
* is executed via **QuackRunner**
* emits **artifacts + manifest**
* is stateless across runs

---

## 🧰 Canonical CLI Surface

QuackBrief does **not** expose a standalone CLI.

All execution occurs through the **single canonical CLI**:

```bash
quack brief <verb> [options]
```

Every QuackTool implements the required verbs:

* `run`
* `validate`
* `doctor`
* `explain`

---

## 🚀 Common Commands

### Compile a briefing

```bash
quack brief run research_bundle/ --lenses lenses.yaml --out ./dist/brief
```

Produces:

* human-readable briefing documents
* per-lens filtered sections
* a manifest recording compilation logic

---

### Validate inputs and lenses

```bash
quack brief validate research_bundle/ --lenses lenses.yaml
```

Checks:

* research artifact integrity
* lens configuration schemas
* completeness of references
* determinism guarantees

---

### Diagnose environment readiness

```bash
quack brief doctor
```

Reports:

* rendering backends (Markdown / PDF / audio)
* text rendering dependencies
* filesystem permissions

---

### Explain a briefing bundle

```bash
quack brief explain ./dist/brief/<run-id>/
```

Explains:

* which sources were used
* how lenses filtered content
* what sections were generated
* how downstream systems should consume outputs

---

## 🔎 Lenses (Core Concept)

A **lens** is an explicit, declarative filter applied to research artifacts.

Lenses define:

* audience perspective
* domain focus
* inclusion / exclusion rules

Example lenses:

* **AIPE** → educational, code-centric, tutorial-ready
* **Rasa** → employer-safe, product-adjacent, DevRel-appropriate
* **AIAC** → operator-focused, rollup-relevant
* **Prof Rod** → narrative-friendly, opinion-ready

> Lenses do not rank or judge.
> They *filter and frame*.

---

## 📦 Output Artifacts

Each run produces a **briefing artifact bundle**.

Example:

```text
dist/
└── brief/
    └── run-2025-03-22T08-01-12/
        ├── daily_brief.md
        ├── lenses/
        │   ├── aipe.md
        │   ├── rasa.md
        │   ├── aiac.md
        │   └── prof_rod.md
        ├── audio/
        │   └── daily_brief.mp3
        └── manifest.json
```

---

### Manifest Is the System of Record

The `manifest.json` captures:

* source artifact references and hashes
* lens definitions and versions
* compilation parameters
* produced artifacts
* timestamps and checksums

If it is not in the manifest, **the briefing did not happen**.

---

## 🔗 How QuackBrief Fits into Larger Workflows

QuackBrief never orchestrates.

Typical flow:

1. **QuackResearch** produces structured research artifacts
2. **Quackchat** captures intent (“compile morning brief”)
3. **Temporal** coordinates workflow state
4. **QuackRunner** executes `quack brief run`
5. Briefing artifacts + manifest are written
6. **Humans and agents** read the brief
7. **Decisions happen elsewhere**

QuackBrief exits immediately after producing artifacts.

---

## ⚙️ Configuration (Indicative)

Configuration is injected via **QuackCore primitives**.

```yaml
brief:
  format:
    - markdown
    - pdf
    - audio
  lenses:
    - aipe
    - rasa
    - aiac
    - prof_rod
  max_items_per_lens: 5
```

Configuration is:

* typed
* validated
* auditable
* environment-agnostic

---

## 🧭 Governance Rules

1. QuackBrief compiles — it does not decide
2. No ranking or prioritization logic
3. No publishing or scheduling
4. No SaaS side-effects
5. Emits artifacts + manifest
6. Uses QuackCore only
7. Runs via the canonical `quack` CLI

---

## 🧠 Closing Statement

QuackBrief exists for one reason:

> **Humans should not read raw data to decide what to do.**

QuackBrief turns:

* JSON → narrative
* signals → context
* research → understanding

So that:

* Rod chooses what to talk about
* agents choose what to propose
* systems remain auditable and teachable

It does not advise.

It **makes understanding possible**.
