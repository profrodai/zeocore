# 🦆 QuackDeck

**A QuackTool for Deterministic Presentation Deck Compilation from Structured Outlines**

> **QuackDeck turns structured outlines into presentation artifacts.**
> It does not design narratives.
> It does not decide teaching strategy.
> It does not present.

---

## 🧠 What QuackDeck Is

QuackDeck is a **Ring B QuackTool**.

It consumes **structured presentation outlines** and emits **presentation artifacts**, such as:

* Marp Markdown decks
* Reveal.js slide decks
* PowerPoint (`.pptx`) files
* code-highlighted slides
* brand-templated variants

Each execution emits:

* one or more deck artifacts
* a manifest describing formats, templates, and transforms

QuackDeck answers one question only:

> **“Given this outline and these templates, produce these presentation decks.”**

---

## ❌ What QuackDeck Is Not

QuackDeck is **not**:

* a slide editor UI
* a storytelling engine
* a curriculum designer
* a live presentation tool
* a workflow orchestrator
* an autonomous agent

It never:

* writes teaching content
* invents examples
* chooses pacing or emphasis
* presents slides
* publishes decks
* triggers other tools

All narrative judgment and sequencing live in **Ring C**
(Agents, Temporal, Quackchat).

---

## 🧭 Position in the QuackVerse Doctrine

```
┌────────────────────────────────────────────┐
│        EXPERIENCES / ORCHESTRATION         │
│  Quackchat · Temporal · n8n · Agents       │
├────────────────────────────────────────────┤
│               TOOLS (WORKERS)              │
│        ▶ QuackDeck ◀                      │
├────────────────────────────────────────────┤
│              CORE (KERNEL)                 │
│  QuackCore: Schemas · Config · Results    │
└────────────────────────────────────────────┘
```

QuackDeck:

* imports **QuackCore only**
* is executed via **QuackRunner**
* emits **artifacts + manifests**
* is stateless across runs

---

## 🧰 Canonical CLI Surface

QuackDeck does **not** expose a standalone CLI.

All execution happens via the **single canonical CLI**:

```bash
quack deck <verb> [options]
```

Required verbs:

* `run`
* `validate`
* `doctor`
* `explain`

---

## 🚀 Common Commands

### Compile a presentation deck

```bash
quack deck run outline.yaml --templates templates.yaml --out ./dist/deck
```

Produces:

* presentation decks in configured formats
* code-highlighted slides (if applicable)
* brand-templated variants
* a manifest recording all transforms

---

### Validate outlines and templates

```bash
quack deck validate outline.yaml --templates templates.yaml
```

Checks:

* outline schema correctness
* slide structure validity
* template compatibility
* determinism guarantees

---

### Diagnose environment readiness

```bash
quack deck doctor
```

Reports:

* rendering backends (Marp / Reveal / PPTX)
* code highlighting support
* filesystem permissions

---

### Explain a deck bundle

```bash
quack deck explain ./dist/deck/<run-id>/
```

Explains:

* which outline was used
* which formats were produced
* which templates were applied
* how downstream systems should consume outputs

---

## 🧩 Supported Output Formats

QuackDeck can emit:

* **Marp** (Markdown → slides)
* **Reveal.js** decks
* **PowerPoint (.pptx)** files

Formats are **configured, not inferred**.

---

## 🎨 Templates and Branding

Templates are **explicit inputs**, defining:

* typography
* color schemes
* layout grids
* logo placement
* code block styling

> **Important:**
> QuackDeck applies templates.
> It does not invent design.

---

## 📦 Output Artifacts

Each run produces a **deck artifact bundle**.

Example:

```text
dist/
└── deck/
    └── run-2025-03-22T14-55-18/
        ├── slides.marp.md
        ├── slides.reveal.html
        ├── slides.pptx
        └── manifest.json
```

---

### Manifest Is the System of Record

The `manifest.json` captures:

* outline references and hashes
* template identifiers and versions
* produced formats
* rendering parameters
* timestamps and checksums

If it is not in the manifest, **the deck does not exist**.

---

## 🔗 How QuackDeck Fits into Workflows

QuackDeck never orchestrates.

Typical flow:

1. **Upstream systems** define an outline
   (QuackTutorial, QuackBrief, Quackchat)
2. **Quackchat / Agents** request deck generation
3. **Temporal** coordinates sequencing
4. **QuackRunner** executes `quack deck run`
5. Deck artifacts + manifest are written
6. **Humans present or record**
7. **Publishing happens elsewhere**

QuackDeck exits immediately after producing artifacts.

---

## ⚙️ Configuration (Indicative)

Configuration is provided via **QuackCore primitives**.

```yaml
deck:
  formats:
    - marp
    - reveal
    - pptx
  code_highlighting: true
  template: prof_rod_default
```

Configuration is:

* explicit
* typed
* auditable
* environment-agnostic

---

## 🧭 Governance Rules

1. QuackDeck compiles — it does not teach
2. No narrative or pedagogical decisions
3. No publishing or presenting
4. No SaaS integrations
5. Emits artifacts + manifest
6. Uses QuackCore only
7. Runs via the canonical `quack` CLI

---

## 🧠 Closing Statement

QuackDeck exists to replace **manual slide production**, not expertise.

It turns:

* outlines → decks
* repetition → templates
* formatting toil → deterministic output

So that:

* Prof Rod can teach live without friction
* AIPE lessons stay consistent
* deep dives are faster to produce
* agents can reason about presentation assets

QuackDeck does not present ideas.

It **makes them presentable** — exactly as specified.
