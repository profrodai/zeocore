Here is a **fully doctrine-compliant `README.md` for `quacktools/quack-calendar`**, aligned with **QuackVerse v3**, **DuckTyper**, and the established style of your other QuackTool READMEs.

This frames **QuackCalendar as a planning compiler**, not a scheduler, not a dashboard, and not a decision-maker.

---

# 🦆 QuackCalendar

**A QuackTool for Deterministic Publishing Timeline Compilation and Content Load Analysis**

> **QuackCalendar compiles proposed publishing timelines from content artifacts.**
> It does not schedule.
> It does not publish.
> It does not decide priorities.

---

## 🧠 What QuackCalendar Is

QuackCalendar is a **Ring B QuackTool**.

It consumes **content artifact metadata** (e.g. posts, clips, briefs, publish packs) and produces **proposed timeline artifacts**, such as:

* draft publishing calendars
* saturation and overlap indicators
* conflict flags across properties
* gap analysis for underutilized days or channels

Each execution emits:

* timeline artifacts
* a manifest describing assumptions, inputs, and detected signals

QuackCalendar answers one question only:

> **“Given these content artifacts and time constraints, what does a proposed publishing timeline look like?”**

---

## ❌ What QuackCalendar Is Not

QuackCalendar is **not**:

* a scheduler
* a calendar UI or dashboard
* a publishing system
* a workflow engine
* a prioritization or strategy tool
* an autonomous agent

It never:

* posts content
* sets final publish times
* resolves conflicts automatically
* optimizes for engagement
* triggers external systems

All judgment, approvals, and execution live in **Ring C**
(Agents, Temporal, Quackchat, n8n).

---

## 🧭 Position in the DuckTyper / QuackVerse Doctrine

```
┌────────────────────────────────────────────┐
│        RING C — EXPERIENCES / CONTROL      │
│  Quackchat · Temporal · n8n · Agents       │
├────────────────────────────────────────────┤
│        RING B — TOOLS (WORKERS)            │
│        ▶ QuackCalendar ◀                  │
├────────────────────────────────────────────┤
│        RING A — CORE (KERNEL)              │
│  QuackCore: Schemas · Config · Results    │
└────────────────────────────────────────────┘
```

QuackCalendar:

* imports **QuackCore only**
* is executed via **QuackRunner**
* emits **artifacts + manifest**
* is stateless across runs

---

## 🧰 Canonical CLI Surface

QuackCalendar does **not** expose its own CLI.

All execution happens via the **single canonical CLI**:

```bash
quack calendar <verb> [options]
```

Every QuackTool implements the required verbs:

* `run`
* `validate`
* `doctor`
* `explain`

---

## 🚀 Common Commands

### Generate a proposed publishing timeline

```bash
quack calendar run content_bundles/ --window 14d --out ./dist/calendar
```

Produces:

* proposed timeline artifacts
* saturation and overlap annotations
* gap analysis markers
* a manifest describing inputs and assumptions

---

### Validate inputs and constraints

```bash
quack calendar validate content_bundles/
```

Checks:

* artifact metadata completeness
* timestamp validity
* property and channel definitions
* determinism guarantees

---

### Diagnose environment readiness

```bash
quack calendar doctor
```

Reports:

* configuration resolution
* time window parsing
* filesystem permissions

---

### Explain a calendar bundle

```bash
quack calendar explain ./dist/calendar/<run-id>/
```

Explains:

* what artifacts were considered
* how conflicts were detected
* how saturation was calculated
* how gaps were identified

---

## 📅 What QuackCalendar Analyzes

QuackCalendar can analyze signals such as:

* number of posts per property per day
* cross-property audience overlap (if declared)
* minimum / maximum cadence constraints
* blackout dates or protected windows
* unused or underutilized content

> **Important:**
> QuackCalendar detects patterns.
> It does not resolve them.

---

## 📦 Output Artifacts

Each run produces a **timeline artifact bundle**.

Example:

```text
dist/
└── calendar/
    └── run-2025-03-22T10-42-19/
        ├── timeline.json
        ├── saturation.json
        ├── conflicts.json
        ├── gaps.json
        └── manifest.json
```

---

### Manifest Is the System of Record

The `manifest.json` captures:

* source artifact references and hashes
* time window and constraints
* detected conflicts and saturation metrics
* produced artifacts
* timestamps and checksums

If it is not in the manifest, **the calendar does not exist**.

---

## 🔗 How QuackCalendar Fits into Larger Workflows

QuackCalendar never orchestrates.

Typical flow:

1. **Upstream tools** produce content artifacts
   (QuackDistro, QuackQuote, QuackClip, QuackPublishPack)
2. **Quackchat** captures intent (“plan next two weeks”)
3. **Temporal** coordinates workflow state
4. **QuackRunner** executes `quack calendar run`
5. Timeline artifacts + manifest are written
6. **Humans and agents** reason over the plan
7. **Scheduling happens elsewhere**

QuackCalendar exits immediately after producing artifacts.

---

## ⚙️ Configuration (Indicative)

Configuration is injected via **QuackCore primitives**.

```yaml
calendar:
  window_days: 14
  properties:
    - prof_rod
    - rasa
    - aiac
    - aipe
  cadence:
    max_per_day: 3
    min_gap_hours: 4
  blackout_dates:
    - 2025-03-29
```

Configuration is:

* typed
* validated
* auditable
* environment-agnostic

---

## 🧭 Governance Rules

1. QuackCalendar proposes — it does not decide
2. No scheduling or publishing
3. No dashboards or UI
4. No SaaS side-effects
5. Emits artifacts + manifest
6. Uses QuackCore only
7. Runs via the canonical `quack` CLI

---

## 🧠 Closing Statement

QuackCalendar exists to answer one operational question:

> **“Are we about to overwhelm ourselves or our audience?”**

It turns:

* scattered content → visible load
* implicit conflicts → explicit artifacts
* guesswork → inspectable plans

So that:

* humans can choose wisely
* agents can propose changes
* systems remain calm and auditable

QuackCalendar does not manage time.

It **makes time visible**.