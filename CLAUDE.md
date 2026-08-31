# Local Governance Entrypoint

**zeocore is an IMPLEMENTATION REPO, not a corpus.** Its SOWs, rulings and design
records live in the `zeroemployeeorg/org` corpus under `projects/zeocore/{sow,ruling,design}`
— never in this repo. `zeo orient` from here reports `corpus: null` by design and
names `org` as the associated corpus; that is correct, not a defect to fix.

## Canonical doctrine

Doctrine is imported below from the canonical corpus. The line is Claude Code's
native `@path` import — **not** zeo's `@import "..."` syntax, which Claude Code
does not recognise (`zero_employee/scaffold.py:18`; only `zeo` expands it).

@../org/claude-md/CLAUDE.md

Role boot docs and authoring skills are reachable on this machine via symlinks to
the corpus — read YOURS first (CLAUDE.md §5a):

- `roles/` → `../org/roles` — `BOOT-MASTER.md` · `BOOT-SPARRING.md` · `BOOT-SUBAGENT.md` · `TOOL-RUNBOOK.md`
- `authoring/` → `../org/authoring` — sow · ruling · design · learnings · stream-instruments skills

**These symlinks are machine-local and deliberately untracked** (see `.gitignore`).
They escape the repo into a sibling private checkout; a public clone of zeocore
must not carry dangling links or leak the private corpus layout. If `roles/` is
missing, clone `zeroemployeeorg/org` as a sibling of this repo and recreate:

    ln -s ../org/roles roles && ln -s ../org/authoring authoring

## Running `zeo` from here

Because this repo is deliberately NOT a corpus, bare `zeo --board` from here
fails with "couldn't find a corpus" — **expected, not a defect.** Point it at the
corpus (this is the documented path, `BOOT-SPARRING.md` §2):

    ZEO_SOWS_ROOT=../org zeo --board
    ZEO_SOWS_ROOT=../org zeo --locate <stream>

`zeo orient --json` works from here with no env var and reports
`corpus: null` + `associated_corpus: .../org`. Do NOT "fix" this by creating a
local `claude-md/CLAUDE.md` — that path is zeo's corpus-discovery marker
(`zero_employee/core.py:82`), and creating it would make zeocore its own corpus
root, stranding `projects/zeocore/` back in org where the SOWs actually are.

## Local Overrides & Context

- **Primary Workstreams:** `org/projects/zeocore/sow/` (in the corpus, not here)
- **Build/Test Gate:** `make verify`
- **Agent first command:** `zeo orient --json`
