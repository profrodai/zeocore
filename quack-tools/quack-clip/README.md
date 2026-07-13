# 🦆 QuackClip

**A QuackTool for Deterministic Short-Form Video Curation and Clip Production**

> **QuackClip produces platform-ready short video clips from explicit segments.**
> It does not decide what is interesting.
> It does not choose what to publish.
> It does not optimize for engagement.

---

## 🧠 What QuackClip Is

QuackClip is a **Ring B QuackTool**.

It consumes **explicit clip instructions**—such as segment manifests or timestamp ranges—and produces **short-form video artifacts**, including:

* 9:16 vertical clips (reels / shorts)
* 1:1 square clips
* 16:9 horizontal clips
* optional burned-in captions
* normalized audio output
* platform-safe framing variants

Each execution emits:

* clip video files
* per-variant derivatives
* a manifest describing all transformations

QuackClip answers one question only:

> **“Given these segments and these rules, produce these short-form video clips.”**

---

## ❌ What QuackClip Is Not

QuackClip is **not**:

* a creative video editor
* a clip-selection engine
* a content strategist
* a publishing or scheduling system
* a workflow orchestrator
* an autonomous agent

It never:

* chooses which segments are worth clipping
* decides aspect ratios implicitly
* applies hidden heuristics
* publishes content
* talks to SaaS platforms
* triggers other tools

All judgment and intent live in **Ring C**
(Agents, Temporal, Quackchat).

---

## 🧭 Position in the DuckTyper / QuackVerse Doctrine

```
┌────────────────────────────────────────────┐
│        RING C — EXPERIENCES / CONTROL      │
│  Quackchat · Temporal · n8n · Agents       │
├────────────────────────────────────────────┤
│        RING B — TOOLS (WORKERS)            │
│        ▶ QuackClip ◀                      │
├────────────────────────────────────────────┤
│        RING A — CORE (KERNEL)              │
│  QuackCore: FS · Schemas · Results · IO   │
└────────────────────────────────────────────┘
```

QuackClip:

* imports **QuackCore only**
* is executed via **QuackRunner**
* emits **artifacts + manifest**
* is stateless across runs

---

## 🧰 Canonical CLI Surface

QuackClip does **not** expose a standalone CLI.

All execution happens via the **single canonical CLI**:

```bash
quack clip <verb> [options]
```

Every QuackTool implements the required verbs:

* `run`
* `validate`
* `doctor`
* `explain`

---

## 🚀 Common Commands

### Produce short-form clips

```bash
quack clip run segments.json --out ./dist/clips
```

Produces:

* short-form video clips
* multiple aspect-ratio variants
* optional captioned versions
* a manifest describing all outputs

---

### Validate segments and configuration

```bash
quack clip validate segments.json
```

Checks:

* segment schema correctness
* timestamp validity
* aspect-ratio configuration
* deterministic framing rules

---

### Diagnose environment readiness

```bash
quack clip doctor
```

Reports:

* FFmpeg / codec availability
* caption rendering support
* filesystem permissions

---

### Explain a clip bundle

```bash
quack clip explain ./dist/clips/<run-id>/
```

Explains:

* which segments were used
* what variants were produced
* which transforms were applied
* how downstream systems should consume outputs

---

## ✂️ Inputs

QuackClip consumes **explicit curation instructions**, typically:

* `segments.json` produced by **QuackSegment**
* manual timestamp ranges
* caption configuration
* framing rules

Inputs are treated as **authoritative and immutable**.

---

## 📦 Output Artifacts

Each run produces a **clip artifact bundle**.

Example:

```text
dist/
└── clips/
    └── run-2025-03-22T12-09-44/
        ├── clip_01_9x16.mp4
        ├── clip_01_1x1.mp4
        ├── clip_01_16x9.mp4
        ├── clip_01_captioned.mp4
        └── manifest.json
```

---

### Manifest Is the System of Record

The `manifest.json` captures:

* source video references and hashes
* segment definitions
* applied transforms
* produced variants
* checksums and timestamps

If a clip is not listed in the manifest, **it does not exist**.

---

## 🔗 How QuackClip Fits into Larger Workflows

QuackClip never orchestrates.

Typical flow:

1. **QuackSegment** proposes candidate segments
2. **Quackchat / Agents** select segments explicitly
3. **Temporal** coordinates workflow state
4. **QuackRunner** executes `quack clip run`
5. Clip artifacts + manifest are written
6. **Downstream tools** consume clips:

   * **QuackBrandPack** → brand-safe variants
   * **QuackPublishPack** → platform bundles
   * **QuackCalendar** → load planning

QuackClip exits immediately after producing artifacts.

---

## ⚙️ Configuration (Indicative)

Configuration is injected via **QuackCore primitives**.

```yaml
clip:
  variants:
    - ratio: 9x16
    - ratio: 1x1
    - ratio: 16x9
  captions:
    enabled: true
    style: burned
  audio:
    normalize: true
```

Configuration is:

* typed
* validated
* auditable
* environment-agnostic

---

## 🧭 Governance Rules

1. QuackClip curates — it does not decide
2. No segment selection logic
3. No publishing or scheduling
4. No SaaS side-effects
5. Emits artifacts + manifest
6. Uses QuackCore only
7. Runs via the canonical `quack` CLI

---

## 🧠 Closing Statement

QuackClip exists to replace **manual short-form editing** without replacing judgment.

It turns:

* chosen moments → platform-ready clips
* implicit editing steps → explicit artifacts
* manual effort → reproducible output

So that:

* Rod can ship daily
* billion.robots can scale faceless content
* agents can reason about video output
* nothing happens invisibly

QuackClip does not choose moments.

It **cuts exactly what it is told** — and proves it.