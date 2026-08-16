#!/usr/bin/env python3
# === QV-LLM:BEGIN ===
# path: scripts/prune_branches.py
# === QV-LLM:END ===

"""
scripts/prune_branches.py

Remove local git branches whose upstream tracking branch is gone (deleted on remote).

Equivalent to the original Makefile one-liner:
    git fetch -p && for branch in $(git branch -vv | grep ': gone]' ...); do git branch -D $branch; done

Improvements over the shell version:
  - --dry-run flag: preview what would be deleted without touching anything.
  - Explicit confirmation prompt when deleting more than one branch (bypass with --yes).
  - Clear output: lists branches found, skips the current branch safely, reports results.
  - Proper error handling with non-zero exit on failure.

Usage:
    python scripts/prune_branches.py
    python scripts/prune_branches.py --dry-run
    python scripts/prune_branches.py --yes          # skip confirmation prompt
    python scripts/prune_branches.py --no-fetch     # skip 'git fetch -p'
"""

from __future__ import annotations

import argparse
import subprocess
import sys


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def run(cmd: list[str], *, capture: bool = True, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check,
    )


def fetch_prune() -> None:
    print("Fetching and pruning remote refs...")
    run(["git", "fetch", "--prune"], capture=False)


def current_branch() -> str:
    result = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout.strip()


def gone_branches() -> list[str]:
    """
    Return local branch names whose upstream tracking ref is marked as gone.

    `git branch -vv` output looks like:
      * main          abc1234 [origin/main] some message
        stale-branch  def5678 [origin/stale-branch: gone] old message
        local-only    ghi9012 some local message
    """
    result = run(["git", "branch", "-vv"])
    branches: list[str] = []
    for line in result.stdout.splitlines():
        # Strip the leading '* ' or '  '
        stripped = line.lstrip("* ").lstrip()
        # Branch name is the first token
        parts = stripped.split()
        if not parts:
            continue
        branch_name = parts[0]
        if ": gone]" in line:
            branches.append(branch_name)
    return branches


def delete_branch(branch: str, *, dry_run: bool = False) -> bool:
    """Force-delete a local branch. Returns True on success."""
    if dry_run:
        print(f"  [dry-run] would delete: {branch}")
        return True
    try:
        run(["git", "branch", "-D", branch])
        print(f"  Deleted: {branch}")
        return True
    except subprocess.CalledProcessError as exc:
        print(f"  ERROR deleting {branch}: {exc.stderr.strip()}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Remove local branches whose upstream is gone.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print branches that would be deleted without deleting them.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt.",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Skip 'git fetch --prune' (use cached remote state).",
    )
    args = parser.parse_args(argv)

    # Verify we're inside a git repo
    try:
        run(["git", "rev-parse", "--git-dir"])
    except subprocess.CalledProcessError:
        print("Error: not inside a git repository.", file=sys.stderr)
        return 1

    if not args.no_fetch:
        try:
            fetch_prune()
        except subprocess.CalledProcessError as exc:
            print(f"Error during git fetch: {exc.stderr.strip()}", file=sys.stderr)
            return 1

    branches = gone_branches()

    if not branches:
        print("No stale branches found. Nothing to do.")
        return 0

    active = current_branch()
    # Safety: never delete the branch we're currently on (shouldn't appear
    # in gone_branches, but guard explicitly)
    safe = [b for b in branches if b != active]
    skipped = [b for b in branches if b == active]

    if skipped:
        print(f"Note: skipping current branch '{active}' even though its upstream is gone.")

    print(f"\nFound {len(safe)} stale branch(es) to delete:")
    for b in safe:
        print(f"  {b}")

    if not safe:
        return 0

    if not args.dry_run and not args.yes:
        try:
            answer = input("\nDelete all of the above? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return 0
        if answer != "y":
            print("Aborted.")
            return 0

    print()
    errors = 0
    for branch in safe:
        ok = delete_branch(branch, dry_run=args.dry_run)
        if not ok:
            errors += 1

    if args.dry_run:
        print(f"\n[dry-run] {len(safe)} branch(es) would have been deleted.")
    elif errors:
        print(f"\nDone with {errors} error(s).", file=sys.stderr)
        return 1
    else:
        print(f"\nRemoved {len(safe)} stale branch(es).")

    return 0


if __name__ == "__main__":
    sys.exit(main())