# A WORK REPO IS NOT THE CORPUS

`org/` is TRUNK-ONLY for filings: a SOW on a branch is invisible to every other seat's
`--inbox`. **THIS repo is the opposite** - it holds CODE that genuinely collides, so
s10's worktree ritual applies: one worktree per stream, on `<seat>/<topic>`, cut from
`origin/main`, ONE STEP PER BLOCK.

**`make verify` is the gate** (s6a). Apply -> verify -> THEN commit. A gate whose output
you discard is not a gate: run it visibly and branch on its exit status.

**A seat pushes its OWN branch** (RULING-007 standing clearance). Pushing `main`,
merging, rebasing and force-pushing are MASTER's - denied here mechanically, not by
convention.

**Your SOW lives in the corpus repo, not here.** `sow_repo` is where you REPORT,
`work_repo` is where you CHANGE CODE, and they are different fields for a reason (s15).

## YOUR SEAT DEFINITION IS HERE, YOUR CHAIN IS NOT

`.claude/agents/` ships in every repo so a session opens with its seat wherever you start it.
**But your SOWs do not live here.** `sow_repo` is where you REPORT and `work_repo` is where you
CHANGE CODE - two fields for a reason (s15). Find your chain with `zeo --locate <stream>
<path-to-corpus>`; file there; commit the work here on YOUR OWN BRANCH.

## NEVER `git stash` IN A WORKTREE - `refs/stash` IS SHARED ACROSS ALL OF THEM

Confirmed twice in one session (2026-08-16, `quackverse-lint-mypy-backlog` rounds 8
`paths-adapters` and `contracts-plugins`, filed independently, same failure): every worktree
under this repo's ONE `.git` common dir shares the SAME `refs/stash`. A `git stash` (or
`stash pop`) run in YOUR worktree while a SIBLING seat's worktree also happens to stash at the
same moment can silently swap working-tree CONTENTS BETWEEN worktrees - your files revert to
someone else's stashed state, or vice versa, with no error and no warning.

**Do not use `git stash` for anything inside a `.claude/worktrees/` checkout.** For the "test
before/after" pattern every lint-mypy-backlog round uses: build a SECOND worktree from the
pre-edit commit instead (`git worktree add <path> <pre-edit-sha>`), or `git diff`/`git show`
the pre-edit tree directly rather than round-tripping through the working directory. Both
recovering streams used `git fsck --unreachable --no-reflog` to find the dangling WIP commit
and `git checkout <sha> -- <files>` to restore - that recovery path works, but avoiding the
hazard is cheaper than recovering from it.
