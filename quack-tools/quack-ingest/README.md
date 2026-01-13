# 🦆 QuackIngest

**A QuackTool for Canonical Media Ingestion, Provenance Tracking, and Root Asset Registration**

> **QuackIngest turns raw media chaos into a canonical root asset.**
> It does not edit content.
> It does not derive value.
> It does not decide what matters.

---

## 🧠 What QuackIngest Is

QuackIngest is a **Ring B QuackTool** and the **mandatory entry point for Pillar A**.

It consumes **raw media inputs**—such as recordings, exports, camera files, and clips—and emits a **RootAssetManifest**, which becomes the **single source of truth** for all downstream work.

QuackIngest performs:

* fingerprinting of all inputs
* provenance recording (where this came from, when, how)
* metadata normalization
* canonical directory layout creation

QuackIngest answers one question only:

> **“What is the root asset this organization is allowed to build from?”**

---

## ❌ What QuackIngest Is Not

QuackIngest is **not**:

* a video editor
* a transcoding or processing engine
* a clipper or segmenter
* a workflow orchestrator
* a publishing system
* an autonomous agent

It never:

* trims or modifies media
* derives secondary content
* infers meaning or structure
* talks to SaaS platforms
* triggers downstream tools

All transformation happens **after ingestion**, never during.

---

## 🧭 Position in the QuackVerse Doctrine

```
┌────────────────────────────────────────────┐
│        EXPERIENCES / ORCHESTRATION         │
│  Quackchat · Temporal · n8n · Agents       │
├────────────────────────────────────────────┤
│               TOOLS (WORKERS)              │
│        ▶ QuackIngest ◀                    │
├────────────────────────────────────────────┤
│              CORE (KERNEL)                 │
│  QuackCore: FS · Schemas · IO · Results   │
└────────────────────────────────────────────┘
```

QuackIngest:

* imports **QuackCore only**
* is executed via **QuackRunner**
* emits **artifacts + manifest**
* is stateless across runs

---

## 🧱 Pillar A Non-Negotiable

QuackIngest enforces the core rule of the AI-First Media Company:

> **If it is not derived from a root asset, it does not exist.**

Every downstream artifact must trace back to a **RootAssetManifest** produced by QuackIngest.

No exceptions.
No shortcuts.
No “just this once.”

---

## 🧰 Canonical CLI Surface

QuackIngest does **not** expose its own CLI.

All execution happens via the **single canonical CLI**:

```bash
quack ingest <verb> [options]
```

Required verbs:

* `run`
* `validate`
* `doctor`
* `explain`

---

## 🚀 Common Commands

### Ingest raw media into a root asset

```bash
quack ingest run ./incoming_media --out ./dist/root_assets
```

Produces:

* a canonical root asset directory
* a `root_asset_manifest.json`
* normalized metadata for all inputs

---

### Validate an ingestion source

```bash
quack ingest validate ./incoming_media
```

Checks:

* file integrity
* supported media types
* duplicate detection
* metadata extractability

---

### Diagnose environment readiness

```bash
quack ingest doctor
```

Reports:

* filesystem access
* hashing / fingerprinting support
* metadata extraction capabilities

---

### Explain a root asset

```bash
quack ingest explain ./dist/root_assets/<run-id>/
```

Explains:

* what files were ingested
* how they were fingerprinted
* where they came from
* how downstream systems must reference them

---

## 📥 Supported Input Sources (Indicative)

QuackIngest is designed to accept **raw, unstructured inputs**, including:

* Riverside / Streamyard exports
* camera card dumps
* phone video clips
* audio recordings
* robot / automation footage
* mixed-format directories

Inputs are treated as **opaque blobs** at ingestion time.

---

## 📦 Output Artifacts

Each run produces a **root asset bundle**.

Example:

```text
dist/
└── root_assets/
    └── run-2025-03-22T07-12-09/
        ├── media/
        │   ├── video_01.mp4
        │   ├── audio_01.wav
        │   └── camera_b_roll.mov
        ├── metadata/
        │   └── normalized.json
        ├── root_asset_manifest.json
        └── manifest.json
```

---

### RootAssetManifest Is Sacred

The `root_asset_manifest.json` records:

* content hashes (fingerprints)
* original filenames and paths
* ingestion timestamp
* source system (if known)
* media type and basic properties

All downstream tools **must reference this manifest**.

If an artifact cannot point back to a root asset fingerprint, it is invalid.

---

## 🔗 How QuackIngest Fits into Workflows

QuackIngest is always **first**.

Typical flow:

1. Raw media appears (recording, export, upload)
2. **Quackchat / Agent** requests ingestion
3. **Temporal** records the ingestion event
4. **QuackRunner** executes `quack ingest run`
5. Root asset bundle + manifest are written
6. **All other tools** reference the root asset
7. Derivation begins elsewhere

QuackIngest exits immediately after registration.

---

## ⚙️ Configuration (Indicative)

Configuration is injected via **QuackCore primitives**.

```yaml
ingest:
  fingerprint:
    algorithm: sha256
  metadata:
    extract_basic: true
  deduplication:
    enabled: true
```

Configuration is:

* explicit
* typed
* auditable
* environment-agnostic

---

## 🧭 Governance Rules

1. QuackIngest is mandatory for all media
2. No transformation or derivation
3. No orchestration or sequencing
4. No SaaS integrations
5. Emits root assets + manifest
6. Uses QuackCore only
7. Runs via the canonical `quack` CLI

---

## 🧠 Closing Statement

QuackIngest exists to kill a dangerous assumption:

> *“The file already exists.”*

In an AI-first organization, **nothing exists until it is registered**.

QuackIngest turns:

* chaos → canon
* files → assets
* memory → provenance

So that:

* Pillar A is enforceable
* automation is auditable
* agents cannot hallucinate inputs
* humans trust the system

QuackIngest does not create value.

It **protects the source of all value**.
