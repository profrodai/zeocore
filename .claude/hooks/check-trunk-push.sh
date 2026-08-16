#!/usr/bin/env bash
# PreToolUse hook: deny `git push` only when it resolves to the trunk branch,
# regardless of how the destination is spelled (bare push, explicit refspec,
# origin HEAD:main, main:main, etc). Every other git push - a stream's own
# feature branch, a worktree branch, anything not trunk - is untouched.
#
# WHY A HOOK AND NOT A PERMISSION GLOB: a glob string-matches the INVOCATION
# ("git push origin main"); this resolves the ACTUAL DESTINATION the way git
# itself would, the same way a bare `git push` on a branch tracking main
# would land on main even though the literal text never says "main". A glob
# can be spelled around; this cannot, because it asks git the same question
# git itself answers before pushing.
#
# Reads the tool_input JSON from stdin (piped by the PreToolUse hook wiring),
# extracts .tool_input.command, and if it's a git-push invocation, resolves
# the destination branch and denies only if that branch is TRUNK_BRANCH.

set -euo pipefail

TRUNK_BRANCH="${TRUNK_BRANCH:-main}"

cmd="$(jq -r '.tool_input.command // empty')"
[ -z "$cmd" ] && exit 0

# Only look at commands that actually invoke git push (allow anything else
# through immediately - status/log/diff/commit/branch/worktree/etc are never
# touched by this hook).
if ! echo "$cmd" | grep -qE '(^|[;&|]|\s)git\s+push(\s|$)'; then
  exit 0
fi

deny() {
  local reason="$1"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}\n' \
    "$(printf '%s' "$reason" | jq -Rs .)"
  exit 0
}

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
# Strip the leading "git push" and any flags, keep positional args.
rest="$(echo "$cmd" | sed -E 's/^.*git[[:space:]]+push[[:space:]]*//')"
# First positional arg after `push` that isn't a flag is the remote (if any);
# the one after that (if present) is the refspec.
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
    deny "git push to '$TRUNK_BRANCH' (explicit destination '$explicit_dest') is blocked here. Own-branch pushes are unrestricted - push, manage, and merge your own branches freely. Trunk landings need a passed gate or the operator's own push - this is a semantic check (it resolves the real destination git would push to), not a string match on the command, so it can't be spelled around."
  fi
  exit 0
fi

# No explicit destination in the command text - a bare `git push` (or
# `git push <remote>` with no refspec) resolves via the CURRENT BRANCH's
# push target, exactly as git itself would resolve it. Ask git the same
# question.
current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
[ -z "$current_branch" ] && exit 0

if [ "$current_branch" = "$TRUNK_BRANCH" ]; then
  deny "git push while checked out on '$TRUNK_BRANCH' itself is blocked here (a bare push resolves to this branch). Own-branch pushes are unrestricted - checkout your own branch and push freely. Trunk landings need a passed gate or the operator's own push."
fi

exit 0
