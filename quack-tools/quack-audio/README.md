# 🦆 QuackAudio

**An Atomic Limb for Deterministic Audio Processing and Voice Production**

> **QuackAudio transforms structured specifications into reproducible audio artifacts.**
> It does not write scripts. It does not direct performances. It does not decide creative intent.

---

## 🧠 What QuackAudio Is

QuackAudio is a **Ring B Atomic Limb**.

It is a deterministic worker designed for manipulation by Sovereign Agents (e.g., OpenClaw). It consumes **audio inputs and specifications** to produce **audio-derived artifacts**, such as:

* mastered podcast episodes and stems
* stitched audio sequences (intro/outro/body)
* deterministic TTS voice tracks (e.g., Prof Rod, Mator)
* time-aligned narration for video and animation
* per-run manifests + LLM-optimized summaries

QuackAudio answers one question only:

> **“Given these audio inputs and parameters, produce these audio artifacts and provide proof.”**

---

## ❌ What QuackAudio Is Not

QuackAudio is **not**:

* a DAW or creative editor UI
* a storytelling or screenplay engine
* an autonomous talent scout
* a workflow orchestrator

It never:

* decides *what* dialogue should be spoken (The Agent/Manager decides)
* chooses emotional delivery or pacing (The Manager decides via parameters)
* performs side-effects like publishing to Spotify/RSS directly

Those responsibilities belong to **Ring C** (Sovereign Agents, Temporal, Quackchat).

---

## 🧭 Position in the QuackVerse Doctrine

```
┌──────────────────────────────────────────────────────────┐
│             RING C — AGENTIC CONTROL                     │
│    OpenClaw (Manager) · Temporal · Quackchat (Cockpit)   │
├──────────────────────────────────────────────────────────┤
│             RING B — ATOMIC LIMBS (WORKERS)              │
│        ▶ QuackAudio ◀                                    │
├──────────────────────────────────────────────────────────┤
│             RING A — THE SOVEREIGN BRAIN                 │
│    Ticket System · QuackStore (.quack/) · QuackLedger    │
└──────────────────────────────────────────────────────────┘

```

QuackAudio:

* imports **QuackCore only**
* issues **Async Tickets** for long-running masters or TTS generations
* stores all outputs in the local **Artifact Store** (`.quack/`)
* is orchestrated externally by always-on agents

---

## 🧰 Canonical CLI Surface

QuackAudio does **not** expose its own standalone CLI. All interaction happens via the **single canonical CLI**:

```bash
quack audio <limb> [options]

```

### Mandatory Agentic Verbs

* `status <RunID>` — Check progress of an audio processing or TTS ticket.
* `explain <RunID>` — Output the `summary.md` for LLM context.
* `--discovery` — Output JSON capability and schema map for the agent.
* `validate` — Pre-flight check of audio scripts, voice IDs, and files.
* `doctor` — Auto-fix local dependencies (FFmpeg, SoX, TTS engines).

---

## 🚀 Common Atomic Limbs

### Master Episode (Async)

```bash
quack audio master input.wav --preset podcast-lufs-16

```

Produces a `RunID` ticket. Agent polls `quack status` until completion.

### Render Voice (Atomic/Async)

```bash
quack audio render --voice mator --text "Hello, Prof Rod!"

```

### Stitch Assets

```bash
quack audio stitch --parts intro.wav,body.wav,outro.wav

```

---

## 📦 Output Artifacts

Each run produces an **audio artifact bundle** within the project's local store.

```text
.quack/
└── runs/
    └── run_audio_xyz_789/
        ├── mastered_output.mp3
        ├── summary.md      <-- LLM-optimized context snippet
        ├── manifest.json   <-- Machine-readable proof
        └── artifacts/
            └── waveform.png

```

### The Manifest & Summary

* **`manifest.json`**: Records LUFS levels, sample rates, voice provider versions, and checksums.
* **`summary.md`**: A textual summary (e.g., "Rendered 5s of audio using Mator voice. Mastered to -16 LUFS. Verified file integrity.") to prevent Agent context-shredding.

---

## 🔗 The Agentic Handshake

QuackAudio follows the **Sovereign Handshake**:

1. **Trigger:** Agent calls `quack audio render` and receives a `RunID`.
2. **Poll:** Agent monitors `quack status <RunID>`.
3. **Verify:** Once finished, the tool writes verified manifests and audio checksums.
4. **Context:** Agent reads `explain <RunID>` to verify the audio matches the intent.

---

## 🧭 Governance Rules

1. **Atomic Mutations:** Use granular commands for audio processing chains.
2. **Async by Default:** Any rendering or mastering task issues a `RunID` ticket.
3. **No Silent Failures:** Exit with `QC_ERROR_CODES` if voices or hardware are unavailable.
4. **Local Sovereignty:** All processed audio and manifests live in the project’s `.quack/` folder.
5. **Everything Emits Proof:** If it didn't emit a manifest, the audio "did not happen."

---

## 🧠 Closing Statement

QuackAudio is a **limb** of the organization.

It does not perform; it produces. It executes the technical mastering and voice generation exactly as specified, providing the Sovereign Agent with the audible proof required for Pillar A production.