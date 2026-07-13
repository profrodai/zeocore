# 🦆 QuackPublishPack

**A QuackTool for Deterministic Packaging of Platform-Ready Publishing Bundles**

> **QuackPublishPack prepares content for publishing.**
> It does not post.
> It does not schedule.
> It does not choose strategy.

---

## 🧠 What QuackPublishPack Is

QuackPublishPack is a **Ring B QuackTool**.

It consumes **content artifacts** (text, images, clips, metadata) and produces **platform-ready publish bundles**, including:

* captions
* hashtags
* alt-text
* media references
* CTAs
* platform-specific constraints

Each run emits:

* one or more **PublishPack bundles**
* a manifest describing how those bundles were assembled

QuackPublishPack answers one question only:

> **“Given these artifacts and rules, how should they be packaged for publishing?”**

---

## ❌ What QuackPublishPack Is Not

QuackPublishPack is **not**:

* a social media scheduler
* a publishing system
* a marketing automation tool
* a workflow engine
* a creative agent
* a dashboard or CMS

It never:

* posts to platforms
* calls SaaS APIs
* schedules content
* tracks engagement
* decides messaging strategy

Those responsibilities live in **Ring C**:

* **Temporal** → when
* **Agents / Humans** → what and why
* **n8n** → how publishing actually happens

---

## 🧭 Position in the QuackVerse Doctrine

```
┌────────────────────────────────────────────┐
│        EXPERIENCES / ORCHESTRATION         │
│  Quackchat · Temporal · n8n · Agents       │
├────────────────────────────────────────────┤
│               TOOLS (WORKERS)              │
│      ▶ QuackPublishPack ◀                 │
├────────────────────────────────────────────┤
│              CORE (KERNEL)                 │
│  QuackCore: Schemas · IO · Results        │
└────────────────────────────────────────────┘
```

QuackPublishPack:

* imports **QuackCore only**
* runs via **QuackRunner**
* emits **artifacts + manifest**
* is stateless across runs

---

## 🧾 The Role QuackPublishPack Replaces

In traditional teams:

* one person rewrites captions per platform
* another adds hashtags
* someone else checks alt-text
* publishing logic lives in heads and checklists

QuackPublishPack replaces the **social media coordinator role** with **deterministic packaging**.

---

## 🧰 Canonical CLI Surface

QuackPublishPack does **not** expose a standalone CLI.

All execution happens via the **single canonical CLI**:

```bash
quack publishpack <verb> [options]
```

Required verbs:

* `run`
* `validate`
* `doctor`
* `explain`

---

## 🚀 Common Commands

### Generate publish-ready bundles

```bash
quack publishpack run ./artifacts --out ./dist/publishpack
```

Produces:

* per-platform publish bundles
* captions + metadata
* media references (paths / URIs)
* a manifest describing bundle composition

---

### Validate publish constraints

```bash
quack publishpack validate ./artifacts
```

Checks:

* platform length limits
* required fields (alt-text, captions)
* missing media references
* brand / safety constraints (if present)

---

### Diagnose environment readiness

```bash
quack publishpack doctor
```

Reports:

* schema availability
* configuration health
* filesystem permissions

---

### Explain a publish bundle

```bash
quack publishpack explain ./dist/publishpack/<run-id>/
```

Explains:

* which artifacts were packaged
* which platforms were targeted
* what metadata was generated
* how downstream systems should consume outputs

---

## 📦 Output Artifacts

Each run produces one or more **PublishPack bundles**.

Example:

```text
dist/
└── publishpack/
    └── run-2025-03-22T11-20-41/
        ├── linkedin/
        │   ├── caption.txt
        │   ├── hashtags.txt
        │   ├── alt_text.txt
        │   └── media.json
        ├── instagram/
        │   ├── caption.txt
        │   ├── hashtags.txt
        │   ├── alt_text.txt
        │   └── media.json
        ├── x/
        │   ├── caption.txt
        │   └── media.json
        └── manifest.json
```

---

### Manifest Is the System of Record

The `manifest.json` captures:

* input artifact references
* packaging rules applied
* platforms targeted
* bundle contents
* checksums and timestamps

If it is not in the manifest, **it was not packaged**.

---

## 🔗 How QuackPublishPack Fits into Workflows

QuackPublishPack never publishes.

Typical flow:

1. **Upstream tools** produce content artifacts
   (QuackVideo, QuackClip, QuackDistro, QuackImage)
2. **Agents / Humans** approve messaging intent
3. **Temporal** decides timing
4. **QuackRunner** executes `quack publishpack run`
5. PublishPack bundles + manifest are written
6. **n8n** consumes bundles and performs posting side-effects
7. **QuackLedger** records what was used

QuackPublishPack exits immediately after packaging.

---

## ⚙️ Configuration (Indicative)

Configuration is injected via **QuackCore primitives**.

```yaml
publishpack:
  platforms:
    linkedin:
      max_length: 3000
      hashtags: true
      alt_text_required: true
    instagram:
      hashtags: true
      max_hashtags: 10
    x:
      max_length: 280
  cta:
    enabled: true
```

Configuration is:

* explicit
* typed
* auditable
* environment-agnostic

---

## 🧭 Governance Rules

1. QuackPublishPack packages — it does not publish
2. No scheduling or timing logic
3. No SaaS or platform API calls
4. Emits bundles + manifest only
5. Uses QuackCore only
6. Runs via the canonical `quack` CLI

---

## 🧠 Closing Statement

QuackPublishPack exists to make publishing **boringly reliable**.

It turns:

* creative artifacts → platform-ready bundles
* implicit checklists → explicit files
* tribal knowledge → manifests

So that:

* agents can reason safely
* n8n can post without guesswork
* brands stay consistent
* humans never copy-paste captions again

QuackPublishPack does not publish.

It **prepares reality for publishing** — and proves how it was done.
