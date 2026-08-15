#!/usr/bin/env python3
# === QV-LLM:BEGIN ===
# path: scripts/aggregate.py
# role: module
# neighbors: annotate_headers.py, fix_imports.py, fix_remaining_tests.py, flatten.py, prune_branches.py, verify_installation.py
# exports: resolve_path, git_available, is_git_ignored, already_added, collect_files, main
# git_branch: main
# git_commit: f0715f0c
# === QV-LLM:END ===

"""
scripts/aggregate.py

Aggregate text files from a directory into a single timestamped output file.
Output is written to <target>/_transient-files/YYYY-MM-DD-<dirname>.txt.

Files already present in the output are skipped (idempotent re-runs).
Files whose basename starts with 'deprecated_' are skipped.
If a .gitignore exists in the target and git is available, ignored paths are excluded.

Usage:
    python scripts/aggregate.py <directory>
    python scripts/aggregate.py .
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FILE_EXTENSIONS = (
    "*.txt",
    "*.md",
    "*.py",
    "*.yaml",
    "*.template",
    "*.toml",
    "Makefile",
    "*.ts",
    "*.tsx",
    "*.mdx",
    "*.js",
    "*.jsx",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def resolve_path(p: str) -> Path:
    """Return an absolute, resolved Path, expanding ~ if present."""
    return Path(p).expanduser().resolve()


def git_available() -> bool:
    try:
        subprocess.run(
            ["git", "--version"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def is_git_ignored(path: Path, repo_root: Path) -> bool:
    """Return True if *path* is ignored according to git in *repo_root*."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "check-ignore", str(path)],
            capture_output=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def already_added(output_file: Path, filepath: Path) -> bool:
    """Return True if *filepath* already has an entry in *output_file*."""
    marker = f"here is {filepath}:"
    try:
        return marker in output_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def collect_files(target: Path, transient_dir: Path) -> list[Path]:
    """
    Walk *target* and return all matching files, excluding the transient dir
    and hidden files (name starting with '.').
    Order mirrors the original shell script: per-extension, then find order.
    Duplicates are removed while preserving first-seen order.
    """
    seen: set[Path] = set()
    results: list[Path] = []

    for pattern in FILE_EXTENSIONS:
        for f in sorted(target.rglob(pattern)):
            # Skip hidden files
            if f.name.startswith("."):
                continue
            # Skip anything inside the transient output directory
            try:
                f.relative_to(transient_dir)
                continue
            except ValueError:
                pass
            resolved = f.resolve()
            if resolved not in seen:
                seen.add(resolved)
                results.append(f)

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate text files from a directory into one file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Target directory to aggregate (default: current directory).",
    )
    args = parser.parse_args(argv)

    target = resolve_path(args.directory)

    if not target.is_dir():
        print(f"Error: not a directory: {target}", file=sys.stderr)
        print(
            "Hint: run from repo root, e.g.  "
            "python scripts/aggregate.py ./quack-core/src/quack_core/config",
            file=sys.stderr,
        )
        return 1

    transient_dir = target / "_transient-files"
    timestamp = date.today().isoformat()
    output_file = transient_dir / f"{timestamp}-{target.name}.txt"

    use_gitignore = (target / ".gitignore").exists() and git_available()

    transient_dir.mkdir(parents=True, exist_ok=True)

    if not output_file.exists():
        output_file.touch()
        print(f"Created output file: {output_file}")
    else:
        print(f"Output file already exists: {output_file}")

    candidates = collect_files(target, transient_dir)

    if not candidates:
        print("No files found matching the specified criteria. Exiting.")
        return 0

    files_processed = 0
    files_added = 0

    with output_file.open("a", encoding="utf-8") as out:
        for f in candidates:
            filepath = f.resolve()

            # Gitignore check
            if use_gitignore and is_git_ignored(filepath, target):
                continue

            # Deprecated prefix check
            if f.name.startswith("deprecated_"):
                print(f"Skipping deprecated file: {filepath}")
                files_processed += 1
                continue

            files_processed += 1

            if already_added(output_file, filepath):
                print(f"Skipping already added file: {filepath}")
                continue

            print(f"Processing: {filepath}")
            out.write(f"here is {filepath}:\n")
            out.write(f"<{f.name}>\n")
            out.write(filepath.read_text(encoding="utf-8", errors="replace"))
            out.write(f"\n</{f.name}>\n\n")
            files_added += 1

    if files_added == 0:
        print("No new files to add. Exiting.")
    else:
        print(f"All files aggregated into: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())