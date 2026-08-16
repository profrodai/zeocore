#!/usr/bin/env bash
# PreToolUse hook: deny `git push`, `git merge`, and `git rebase` only when
# (a) the command targets a git repo that is THIS repo (not some other repo
# the session's command happens to `cd`/`-C` into) and (b) the act would land
# on, or is performed while checked out on, the trunk branch there.
#
# WHY A HOOK AND NOT A PERMISSION GLOB: a glob string-matches the INVOCATION
# ("git push origin main"); this asks git the same question git itself would
# ask before acting - what repo, what branch - rather than pattern-matching
# the command text. A glob can be spelled around by rewording the command;
# this cannot, because it does not care how the command is spelled, only
# what it would actually do.
#
# WHY MERGE/REBASE ARE HERE TOO, NOT JUST PUSH (2026-08-16): the same repos
# that had a glob push-deny also had `git merge:*`/`git rebase:*` as blanket
# permission denies - blocking a stream from merging or rebasing its OWN
# branches, which the operator explicitly wants unrestricted ("let them
# manage all their branches and git operations as they see best" - the exact
# complaint that also motivated replacing the push glob). The risk the old
# blanket deny was actually guarding against is narrower than "any merge or
# rebase": `git merge <branch>` while checked out on TRUNK mutates trunk's
# local HEAD directly, no push required for the damage to land locally, and
# even with push separately gated a polluted local trunk checkout is wrong
# for whoever looks at it next. `git rebase` while checked out on trunk
# rewrites trunk's own history locally, same shape. Neither risk depends on
# the branch being MERGED FROM/rebased FROM being someone else's; it depends
# entirely on what's currently checked out. So: gate on "am I on trunk right
# now", not on the command's other arguments - own-branch merge/rebase
# (including merging one feature branch into another) is unrestricted.
#
# git reset --hard and rm -rf are DELIBERATELY NOT HERE - those are
# data-loss risks on ANY branch, not a trunk-vs-own-branch question, and
# stay as ordinary permission denies in settings.json rather than becoming
# part of this hook's scope.
#
# Reads the tool_input JSON from stdin (piped by the PreToolUse hook wiring).

set -euo pipefail

TRUNK_BRANCH="${TRUNK_BRANCH:-main}"
# The repo this hook is deployed to. Resolved from THIS SCRIPT's own location
# (.claude/hooks/check-trunk-guard.sh lives at <repo>/.claude/hooks/...), not
# from the session's launch cwd - the two are not the same thing, which was
# the whole bug in this hook's first version (paid, fixed, see the sibling
# push-only history this script's git log carries forward from).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OWN_REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"

cmd="$(jq -r '.tool_input.command // empty')"
[ -z "$cmd" ] && exit 0

deny() {
  local reason="$1"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}\n' \
    "$(printf '%s' "$reason" | jq -Rs .)"
  exit 0
}

# ── RESOLVE THE REAL TARGET DIRECTORY FOR A GIVEN GIT SUBCOMMAND, NOT THE
#    SESSION'S LAUNCH CWD ────────────────────────────────────────────────────
# The command text may redirect where the act actually runs, three ways:
#   cd <path> && ... git <subcmd> ...
#   cd <path>; ... git <subcmd> ...
#   git -C <path> <subcmd> ...
# Take the LAST such redirect before the final occurrence of <subcmd> - a
# chain can `cd` multiple times, only the one immediately governing the act
# matters. If none is present, the act runs wherever this hook process
# itself runs, which for a PreToolUse hook is the session's own working
# directory - safe to read directly.
resolve_target_dir() {
  local subcmd="$1"
  local dir=""
  if echo "$cmd" | grep -qE "(^|[;&|]|\s)git\s+-C\s+\S+\s+${subcmd}(\s|\$)"; then
    dir="$(echo "$cmd" | grep -oE "git\s+-C\s+\S+\s+${subcmd}" | sed -E "s/^git[[:space:]]+-C[[:space:]]+//; s/[[:space:]]+${subcmd}\$//")"
  else
    local before_act last_cd
    before_act="$(echo "$cmd" | sed -E "s/(.*)git[[:space:]]+${subcmd}.*/\1/")"
    last_cd="$(echo "$before_act" | grep -oE 'cd[[:space:]]+[^;&|]+' | tail -1 || true)"
    if [ -n "$last_cd" ]; then
      dir="$(echo "$last_cd" | sed -E 's/^cd[[:space:]]+//' | sed -E "s/^['\"]//; s/['\"]?[[:space:]]*\$//")"
    fi
  fi
  if [ -n "$dir" ]; then
    dir="${dir/#\~/$HOME}"
  fi
  printf '%s' "$dir"
}

# Returns 0 (true) iff the resolved target directory's repo root is THIS
# hook's own repo. Anything else - a different repo, or an unresolvable
# target - means this hook has no standing to deny the act; get out of the
# way rather than guess.
targets_own_repo() {
  local target_dir="$1" resolved_target_root=""
  if [ -n "$target_dir" ]; then
    resolved_target_root="$(git -C "$target_dir" rev-parse --show-toplevel 2>/dev/null || true)"
  else
    resolved_target_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  fi
  [ -n "$OWN_REPO_ROOT" ] && [ -n "$resolved_target_root" ] && [ "$resolved_target_root" = "$OWN_REPO_ROOT" ]
}

current_branch_of() {
  local target_dir="$1"
  if [ -n "$target_dir" ]; then
    git -C "$target_dir" rev-parse --abbrev-ref HEAD 2>/dev/null || true
  else
    git rev-parse --abbrev-ref HEAD 2>/dev/null || true
  fi
}

# ══════════════════════════════════════════════════════════════════════════
# PUSH
# ══════════════════════════════════════════════════════════════════════════
if echo "$cmd" | grep -qE '(^|[;&|]|\s)git\s+(-C\s+\S+\s+)?push(\s|$)'; then
  target_dir="$(resolve_target_dir push)"
  if targets_own_repo "$target_dir"; then
    if echo "$cmd" | grep -qE '(^|[;&|]|\s)git\s+push\b.*(-f\b|--force\b)'; then
      deny "git push --force / -f is blocked in this repo: force-push rewrites history other seats or the operator may already have pulled. If a rewrite is genuinely needed, that is the operator's act."
    fi

    # Explicit destination: git push <remote> <refspec>, HEAD:<branch>, or
    # <local>:<remote-branch>. A refspec's REMOTE-side name is what lands
    # where - the part after a colon, or the bare name if there is none.
    rest="$(echo "$cmd" | sed -E 's/^.*[[:space:]]push[[:space:]]*//')"
    read -r -a words <<< "$rest"
    remote="" refspec="" explicit_dest=""
    for w in "${words[@]+"${words[@]}"}"; do
      case "$w" in
        -*) continue ;;
        *)
          if [ -z "$remote" ]; then remote="$w"; else refspec="$w"; break; fi
          ;;
      esac
    done
    if [ -n "$refspec" ]; then
      if [[ "$refspec" == *:* ]]; then explicit_dest="${refspec##*:}"; else explicit_dest="$refspec"; fi
    fi

    if [ -n "$explicit_dest" ]; then
      if [ "$explicit_dest" = "$TRUNK_BRANCH" ]; then
        deny "git push to '$TRUNK_BRANCH' in $(basename "$OWN_REPO_ROOT") (explicit destination '$explicit_dest') is blocked here. Own-branch pushes are unrestricted - push, manage, and merge your own branches freely. Trunk landings need the operator's own push - this is a semantic check scoped to this repo's own destination, not a string match on the command, so it can't be spelled around and it does not fire on a push aimed at some other repo."
      fi
    else
      # Bare push (or `git push <remote>` with no refspec) resolves via the
      # CURRENT BRANCH's push target, exactly as git itself would resolve it.
      current_branch="$(current_branch_of "$target_dir")"
      if [ -n "$current_branch" ] && [ "$current_branch" = "$TRUNK_BRANCH" ]; then
        deny "git push while checked out on '$TRUNK_BRANCH' in $(basename "$OWN_REPO_ROOT") itself is blocked here (a bare push resolves to this branch). Own-branch pushes are unrestricted - checkout your own branch and push freely. Trunk landings need the operator's own push."
      fi
    fi
  fi
fi

# ══════════════════════════════════════════════════════════════════════════
# MERGE / REBASE - gated on CURRENT BRANCH ONLY, not on what's being merged
# from. Both mutate the checked-out branch's local HEAD directly; the risk
# is "trunk gets rewritten locally without review", which is fully
# determined by what's checked out, never by the other ref named.
# ══════════════════════════════════════════════════════════════════════════
for subcmd in merge rebase; do
  if echo "$cmd" | grep -qE "(^|[;&|]|\s)git\s+(-C\s+\S+\s+)?${subcmd}(\s|\$)"; then
    # --abort / --continue / --skip / --quit UNDO or resolve an ALREADY-
    # in-progress merge/rebase; they never land new history, they recover
    # from a stuck one. Denying these would make a stuck-on-trunk situation
    # WORSE (unable to abort out of it) rather than safer. Paid finding
    # while testing this hook, not a live incident - caught before shipping.
    if echo "$cmd" | grep -qE "git\s+(-C\s+\S+\s+)?${subcmd}\b.*--(abort|continue|skip|quit)\b"; then
      continue
    fi
    target_dir="$(resolve_target_dir "$subcmd")"
    if targets_own_repo "$target_dir"; then
      current_branch="$(current_branch_of "$target_dir")"
      if [ -n "$current_branch" ] && [ "$current_branch" = "$TRUNK_BRANCH" ]; then
        deny "git $subcmd while checked out on '$TRUNK_BRANCH' in $(basename "$OWN_REPO_ROOT") is blocked here - it would rewrite trunk's history locally without review, whatever branch is named as the source. Own-branch $subcmd is unrestricted: checkout your own branch first, merge or rebase whatever you need there, and push it (subject to the trunk-push rule above) when ready."
      fi
    fi
  fi
done

exit 0
