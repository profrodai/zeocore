# 🦆 QuackCompliance

**A QuackTool for Deterministic Compliance Validation and Guardrail Enforcement**

> **QuackCompliance validates artifacts against explicit compliance rules.**
> It does not interpret intent.
> It does not give legal advice.
> It does not decide what should be published.

---

## 🧠 What QuackCompliance Is

QuackCompliance is a **Ring B QuackTool**.

It consumes **content artifacts** (text, media, metadata, manifests) and **explicit compliance rule sets**, and emits **compliance reports** indicating whether artifacts:

* pass validation
* fail validation
* require human review

Validation domains include:

* employer constraints (e.g. Rasa policies)
* licensing requirements
* disclosure rules
* safety and content policies

Each execution emits:

* a structured pass/fail report
* a manifest describing applied rules and findings

QuackCompliance answers one question only:

> **“Do these artifacts comply with the declared rules?”**

---

## ❌ What QuackCompliance Is Not

QuackCompliance is **not**:

* a legal advisor
* a policy authoring system
* a creative editor
* a publishing gatekeeper
* a workflow orchestrator
* an autonomous agent

It never:

* rewrites content
* negotiates tradeoffs
* decides risk tolerance
* blocks workflows permanently
* publishes or deletes artifacts
* talks to external services

All judgment, escalation, and final decisions live in **Ring C**
(Agents, Temporal, Quackchat).

---

## 🧭 Position in the QuackVerse Doctrine

```
┌────────────────────────────────────────────┐
│        EXPERIENCES / ORCHESTRATION         │
│  Quackchat · Temporal · n8n · Agents       │
├────────────────────────────────────────────┤
│               TOOLS (WORKERS)              │
│        ▶ QuackCompliance ◀                │
├────────────────────────────────────────────┤
│              CORE (KERNEL)                 │
│  QuackCore: Schemas · Policies · Results  │
└────────────────────────────────────────────┘
```

QuackCompliance:

* imports **QuackCore only**
* is executed via **QuackRunner**
* emits **artifacts + manifests**
* is stateless across runs

---

## 🧰 Canonical CLI Surface

QuackCompliance does **not** expose a standalone CLI.

All execution happens via the **single canonical CLI**:

```bash
quack compliance <verb> [options]
```

Required verbs:

* `run`
* `validate`
* `doctor`
* `explain`

---

## 🚀 Common Commands

### Validate artifacts for compliance

```bash
quack compliance run artifact_bundle/ --rules rules.yaml --out ./dist/compliance
```

Produces:

* a compliance report
* pass / fail / review status per artifact
* a manifest recording applied rules

---

### Validate inputs and rule definitions

```bash
quack compliance validate artifact_bundle/ --rules rules.yaml
```

Checks:

* rule schema correctness
* artifact metadata completeness
* rule–artifact compatibility
* determinism guarantees

---

### Diagnose environment readiness

```bash
quack compliance doctor
```

Reports:

* rule resolution
* policy engine availability
* filesystem permissions

---

### Explain a compliance report

```bash
quack compliance explain ./dist/compliance/<run-id>/
```

Explains:

* which rules were applied
* which artifacts passed or failed
* exact reasons for failures
* what downstream systems should do next

---

## 🔐 What QuackCompliance Validates

QuackCompliance validates **explicitly declared constraints**, such as:

### Employer & Organizational Constraints

* employer separation rules (e.g. Rasa vs Prof Rod)
* forbidden topics or claims
* disclosure requirements

### Licensing & Attribution

* asset license compatibility
* attribution presence
* reuse permissions

### Safety & Content Policies

* prohibited content categories
* sensitive claims
* audience restrictions

> **Important:**
> If a rule is not declared, it is not enforced.
> QuackCompliance enforces *only what is written*.

---

## 📦 Output Artifacts

Each run produces a **compliance artifact bundle**.

Example:

```text
dist/
└── compliance/
    └── run-2025-03-22T13-41-02/
        ├── report.json
        ├── summary.md
        └── manifest.json
```

---

### Compliance Report Semantics

Each artifact is assigned one of:

* **PASS** — compliant with all rules
* **FAIL** — violates one or more rules
* **REVIEW** — ambiguous, requires human judgment

Failures always include **explicit reasons**.

---

### Manifest Is the System of Record

The `manifest.json` captures:

* artifact references and hashes
* rule identifiers and versions
* validation outcomes
* timestamps and checksums

If a rule is not listed, **it was not applied**.

---

## 🔗 How QuackCompliance Fits into Workflows

QuackCompliance never orchestrates.

Typical flow:

1. **Upstream tools** produce content artifacts
   (QuackClip, QuackQuote, QuackBrandPack, QuackPublishPack)
2. **Quackchat / Agents** request compliance validation
3. **Temporal** manages gating logic
4. **QuackRunner** executes `quack compliance run`
5. Compliance artifacts + manifest are written
6. **Agents or humans** decide next steps
7. **Publishing happens elsewhere**

QuackCompliance exits immediately after producing artifacts.

---

## ⚙️ Configuration (Indicative)

Configuration is provided via **QuackCore policy primitives**.

```yaml
compliance:
  employer: rasa
  disclosures:
    required:
      - "Views are personal and do not represent my employer"
  forbidden_topics:
    - roadmap speculation
    - competitor claims
  licensing:
    require_attribution: true
```

Configuration is:

* explicit
* typed
* auditable
* environment-agnostic

---

## 🧭 Governance Rules

1. QuackCompliance validates — it does not judge
2. No rewriting or content mutation
3. No publishing or blocking side-effects
4. No SaaS integrations
5. Emits reports + manifest
6. Uses QuackCore only
7. Runs via the canonical `quack` CLI

---

## 🧠 Closing Statement

QuackCompliance exists to replace **implicit trust with explicit guardrails**.

It turns:

* “this should be fine” → provable checks
* tribal knowledge → declared rules
* manual review → inspectable reports

So that:

* one person can safely operate many brands
* employer boundaries are enforced mechanically
* agents can reason about risk
* audits are boring and fast

QuackCompliance does not say *no*.

It says **why** — and records it forever.
