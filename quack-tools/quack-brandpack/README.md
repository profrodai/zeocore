# 🦆 QuackBrandPack

**An Atomic Limb for Deterministic Brand Constraint Application and Safe Content Reuse**

> **QuackBrandPack applies brand-specific rules to neutral content artifacts.**
> It does not invent messaging. It does not choose audiences. It does not decide strategy.

---

## 🧠 What QuackBrandPack Is

QuackBrandPack is a **Ring B Atomic Limb**.

It is a deterministic worker designed to be manipulated by Sovereign Agents (e.g., OpenClaw). It consumes **neutral, already-derived artifacts** (text, clips, images) and produces **brand-specific variants** by applying explicit constraints such as:

* tone and voice rules
* CTA policies and hashtag requirements
* employer or sponsor disclosure mandates
* safety and compliance guardrails

QuackBrandPack answers one question only:

> **“Given these neutral inputs and these brand rules, produce compliant brand-specific variants and provide proof.”**

---

## ❌ What QuackBrandPack Is Not

QuackBrandPack is **not**:

* a creative writing agent
* a design or brand strategy engine
* a publishing system
* an autonomous decision-maker

It never:

* decides *which* brand should be used for a specific piece (The Agent decides)
* invents tone beyond configured parameters
* performs side-effects or talks to social media APIs

Those responsibilities belong to **Ring C** (Sovereign Agents, Temporal, Quackchat).

---

## 🧭 Position in the QuackVerse Doctrine

```
┌──────────────────────────────────────────────────────────┐
│             RING C — AGENTIC CONTROL                     │
│    OpenClaw (Manager) · Temporal · Quackchat (Cockpit)   │
├──────────────────────────────────────────────────────────┤
│             RING B — ATOMIC LIMBS (WORKERS)              │
│        ▶ QuackBrandPack ◀                                │
├──────────────────────────────────────────────────────────┤
│             RING A — THE SOVEREIGN BRAIN                 │
│    Ticket System · QuackStore (.quack/) · QuackLedger    │
└──────────────────────────────────────────────────────────┘

```

QuackBrandPack:

* imports **QuackCore only**
* issues **Async Tickets** for high-volume batch processing
* stores all outputs in the local **Artifact Store** (`.quack/`)
* is orchestrated by always-on agents

---

## 🧰 Canonical CLI Surface

QuackBrandPack does **not** expose its own standalone CLI. All interaction happens via the **single canonical CLI**:

```bash
quack brandpack <limb> [options]

```

### Mandatory Agentic Verbs

* `status <RunID>` — Check progress of a brand-packaging ticket.
* `explain <RunID>` — Output the `summary.md` for LLM context.
* `--discovery` — Output JSON-formatted capability and schema map for the agent.
* `validate` — Pre-flight check of brand rules and input artifacts.
* `doctor` — Auto-fix local configuration or schema dependencies.

---

## 🚀 Common Atomic Limbs

### Apply Brand Rules (Async)

```bash
quack brandpack apply ./neutral_assets --brands brands.yaml

```

Produces a `RunID` ticket. Agent polls `quack status` until completion.

### Extract Brand Metadata

```bash
quack brandpack metadata --brand prof_rod

```

---

## 📦 Output Artifacts

Each run produces a **brand-segmented artifact bundle** within the project's local store.

```text
.quack/
└── runs/
    └── run_brand_abc_123/
        ├── prof-rod/
        │   ├── post.txt
        │   └── manifest.json
        ├── summary.md      <-- LLM-optimized context snippet
        └── manifest.json   <-- Machine-readable proof

```

### The Manifest & Summary

* **`manifest.json`**: Records exactly which rules (hashes/versions) were applied to which artifacts.
* **`summary.md`**: A textual summary (e.g., "Generated variants for Prof Rod and Rasa. Applied mandatory employer disclosures to Rasa assets.") to prevent Agent context-shredding.

---

## 🔗 The Agentic Handshake

QuackBrandPack follows the **Sovereign Handshake**:

1. **Trigger:** Agent calls `quack brandpack apply` and receives a `RunID`.
2. **Poll:** Agent monitors `quack status <RunID>`.
3. **Verify:** Once finished, the tool writes verified manifests for each brand.
4. **Context:** Agent reads `explain <RunID>` to see exactly how the neutral content was "branded."

---

## 🧭 Governance Rules

1. **Atomic Application:** Tools apply constraints; they do not invent strategy.
2. **Async by Default:** High-volume packaging tasks issue a `RunID` ticket.
3. **No Silent Failures:** Exit with `QC_ERROR_CODES` if rules or assets are missing.
4. **Local Sovereignty:** All brand assets and manifests live in the project’s `.quack/` folder.
5. **Everything Emits Proof:** If it didn't emit a manifest, the branding "did not happen."

---

## 🧠 Closing Statement

QuackBrandPack is a **limb** for operational safety. It ensures that one core idea can safely serve multiple brands without manual policing, enforcing organizational boundaries mechanically through the **Sovereign Brain**.