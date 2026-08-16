#!/usr/bin/env bash
# PreToolUse hook: deny `git push` only when (a) it targets a git command
# running in THIS repo (not some other repo the session's command happens to
# `cd` into) and (b) it resolves to the trunk branch there.
#
# WHY A HOOK AND NOT A PERMISSION GLOB: a glob string-matches the INVOCATION
# ("git push origin main"); this asks git the same question git itself would
# ask before pushing - what repo, what destination - rather than pattern-
# matching the command text. A glob can be spelled around by rewording the
# command; this cannot, because it does not care how the command is spelled,
# only what it would actually do.
#
# PAID (2026-08-16): the first version of this hook resolved "does the
# command's TEXT contain the trunk branch name" without ever checking WHICH
# repo that name belonged to - a PreToolUse hook fires on every Bash call in
# a SESSION, not just calls inside the repo whose settings.json declared it.
# A ducktyper-project session running `cd ~/code/zeroemployeeorg/org && git
# push origin main` got denied by ducktyper's hook, even though the push
# targeted org (a different repo with its own, different push policy) and
# ducktyper's own trunk was never touched. Diagnosed and reported live by a
# peer session; fixed here by resolving the REAL target directory before
# doing anything else, and refusing to opine on a push this hook's own repo
# does not own.
#
# Reads the tool_input JSON from stdin (piped by the PreToolUse hook wiring).

set -euo pipefail

TRUNK_BRANCH="${TRUNK_BRANCH:-main}"
# The repo this hook is deployed to. Resolved from THIS SCRIPT's own location
# (.claude/hooks/check-trunk-push.sh lives at <repo>/.claude/hooks/...), not
# from the session's launch cwd - the two are not the same thing, which is
# the whole bug being fixed here.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OWN_REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"

cmd="$(jq -r '.tool_input.command // empty')"
[ -z "$cmd" ] && exit 0

# Only look at commands that actually invoke git push (allow anything else
# through immediately - status/log/diff/commit/branch/worktree/etc are never
# touched by this hook). Two shapes: `git push` adjacent, or `git -C <path>
# push` where -C separates them - the adjacent-only version of this check
# was a dead-code trap for the -C branch below (it never matched, so -C
# handling could never run; caught by the automated test suite, not by eye).
if ! echo "$cmd" | grep -qE '(^|[;&|]|\s)git\s+(-C\s+\S+\s+)?push(\s|$)'; then
  exit 0
fi

deny() {
  local reason="$1"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}\n' \
    "$(printf '%s' "$reason" | jq -Rs .)"
  exit 0
}

# ── RESOLVE THE REAL TARGET DIRECTORY, NOT THE SESSION'S LAUNCH CWD ──────────
# The command text may redirect where the push actually runs, three ways:
#   cd <path> && ... git push ...        (most common shape in this org)
#   cd <path>; ... git push ...
#   git -C <path> push ...
# Take the LAST such redirect before the push clause - a chain can `cd`
# multiple times, and only the one immediately governing the push matters.
# If none is present, the push runs wherever this hook process itself runs,
# which for a PreToolUse hook is the session's own working directory - safe
# to read directly.
target_dir=""

# git -C <path> push ...  (path is whatever -C names, may itself be relative
# to a prior cd - good enough for the common case; not chasing every nested
# form here, this hook's job is the common shapes doctrine actually produces)
if echo "$cmd" | grep -qE '(^|[;&|]|\s)git\s+-C\s+\S+\s+push(\s|$)'; then
  # -o (print only the match) avoids the greedy-leading-.* capture-group trap
  # that silently swallowed the whole command on first attempt - grep -o on
  # the "-C <path>" fragment specifically, then strip the flag, is exact.
  target_dir="$(echo "$cmd" | grep -oE 'git\s+-C\s+\S+\s+push' | sed -E 's/^git[[:space:]]+-C[[:space:]]+//; s/[[:space:]]+push$//')"
else
  # Last `cd <path>` before the final `git push` in the chain.
  before_push="$(echo "$cmd" | sed -E 's/(.*)git[[:space:]]+push.*/\1/')"
  last_cd="$(echo "$before_push" | grep -oE 'cd[[:space:]]+[^;&|]+' | tail -1 || true)"
  if [ -n "$last_cd" ]; then
    # Strip the leading "cd", quotes, AND trailing whitespace left by the
    # greedy [^;&|]+ capture (it eats right up to a trailing "&&"'s own
    # leading space) - an unstripped trailing space breaks `git -C "$dir"`
    # silently, which looks exactly like "not this repo" and exits early.
    # Paid once already in testing; pinned here so it is not paid again.
    target_dir="$(echo "$last_cd" | sed -E 's/^cd[[:space:]]+//' | sed -E "s/^['\"]//; s/['\"]?[[:space:]]*\$//")"
  fi
fi

if [ -n "$target_dir" ]; then
  # Expand ~ the way a shell would, since sed above can't.
  target_dir="${target_dir/#\~/$HOME}"
  resolved_target_root="$(git -C "$target_dir" rev-parse --show-toplevel 2>/dev/null || true)"
else
  resolved_target_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
fi

# THE GUARD THIS HOOK EXISTS TO ADD: if the push's real target repo is not
# THIS hook's own repo, this hook has no standing to deny it - some OTHER
# repo's own hook (or lack of one) governs that push, not this one. Get out
# of the way entirely rather than guessing.
if [ -z "$OWN_REPO_ROOT" ] || [ -z "$resolved_target_root" ] || [ "$resolved_target_root" != "$OWN_REPO_ROOT" ]; then
  exit 0
fi

# ── FROM HERE ON: the push genuinely targets THIS repo. Same destination
# logic as before, now actually scoped to where it applies. ─────────────────

# Explicit force-push spellings are always denied outright, whatever the
# destination - force is its own hazard class, not a trunk-only one.
if echo "$cmd" | grep -qE '(^|[;&|]|\s)git\s+push\b.*(-f\b|--force\b)'; then
  deny "git push --force / -f is blocked in this repo: force-push rewrites history other seats or the operator may already have pulled. If a rewrite is genuinely needed, that is the operator's act."
fi

# Try to read an explicit destination out of the command itself first:
#   git push <remote> <refspec>
#   git push <remote> HEAD:<branch>
#   git push <remote> <local>:<remote-branch>
# A refspec's REMOTE-side name is what lands where - for "HEAD:main" or
# "main:main" or "main" alone (as a refspec, not just a branch), that's the
# part after the colon, or the bare name if there is no colon.
explicit_dest=""
# Strip everything through the LAST "push" keyword (whether reached via
# `git push` adjacent or `git -C <path> push` with -C between them - the
# earlier gate now accepts both shapes, this must match it or the -C form
# parses garbage: the whole original command, `-C` and all, as if it were
# positional push args). Anchoring on "push" alone rather than "git push"
# is deliberately looser here since the two detectors above already
# confirmed this command IS a push invocation before we ever reach this line.
rest="$(echo "$cmd" | sed -E 's/^.*[[:space:]]push[[:space:]]*//')"
read -r -a words <<< "$rest"
remote=""
refspec=""
for w in "${words[@]+"${words[@]}"}"; do
  case "$w" in
    -*) continue ;;
    *)
      if [ -z "$remote" ]; then remote="$w"; else refspec="$w"; break; fi
      ;;
  esac
done

if [ -n "$refspec" ]; then
  if [[ "$refspec" == *:* ]]; then
    explicit_dest="${refspec##*:}"
  else
    explicit_dest="$refspec"
  fi
fi

if [ -n "$explicit_dest" ]; then
  if [ "$explicit_dest" = "$TRUNK_BRANCH" ]; then
    deny "git push to '$TRUNK_BRANCH' in $(basename "$OWN_REPO_ROOT") (explicit destination '$explicit_dest') is blocked here. Own-branch pushes are unrestricted - push, manage, and merge your own branches freely. Trunk landings need the operator's own push - this is a semantic check scoped to this repo's own destination, not a string match on the command, so it can't be spelled around and it does not fire on a push aimed at some other repo."
  fi
  exit 0
fi

# No explicit destination in the command text - a bare `git push` (or
# `git push <remote>` with no refspec) resolves via the CURRENT BRANCH's
# push target, exactly as git itself would resolve it. Ask git the same
# question, IN THE RESOLVED TARGET DIRECTORY - not wherever this hook
# process happens to be running.
if [ -n "$target_dir" ]; then
  current_branch="$(git -C "$target_dir" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
else
  current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
fi
[ -z "$current_branch" ] && exit 0

if [ "$current_branch" = "$TRUNK_BRANCH" ]; then
  deny "git push while checked out on '$TRUNK_BRANCH' in $(basename "$OWN_REPO_ROOT") itself is blocked here (a bare push resolves to this branch). Own-branch pushes are unrestricted - checkout your own branch and push freely. Trunk landings need the operator's own push."
fi

exit 0
