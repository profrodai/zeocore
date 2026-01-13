#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
from pathlib import Path
from typing import Iterable, Optional

# -----------------------------
# Defaults / constants
# -----------------------------
SKIP_DIR_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "build",
    "dist",
    ".egg-info",
    "node_modules",
}

# Header markers (must be on their own lines to count as a "real" header)
BEGIN = "# === QV-LLM:BEGIN ==="
END = "# === QV-LLM:END ==="

ENCODING_RE = re.compile(r"^#.*coding[:=]\s*[-\w.]+")
SHEBANG_RE = re.compile(r"^#!")

PRIORITY_NEIGHBORS = [
    "__init__.py",
    "main.py",
    "app.py",
    "service.py",
    "models.py",
    "protocols.py",
    "plugin.py",
    "config.py",
    "registry.py",
    "_ops.py",
    "results.py",
    "utils.py",
]

ROLE_KEYS = [
    "models",
    "protocols",
    "service",
    "_ops",
    "plugin",
    "utils",
    "api",
    "cli",
    "adapters",
    "tests",
]

DEFAULT_EXTENSIONS = [".py", ".yaml", ".yml", ".toml", ".env"]  # intentionally skipping .md/.json

# Never annotate these (prevents self-modifying tool scripts & other footguns)
DEFAULT_EXCLUDE = {
    "flat.txt",
    "_transient-files",
    # IMPORTANT: don't let this script annotate itself (or other tool scripts if you want)
    "scripts/annotate_headers.py",
}

# -----------------------------
# File discovery / filtering
# -----------------------------
def iter_files(root: Path, extensions: tuple[str, ...]) -> Iterable[Path]:
    for dirpath, dirs, files in os.walk(root):
        dpath = Path(dirpath)

        # prune dirs in-place
        dirs[:] = [
            d for d in dirs
            if d not in SKIP_DIR_PARTS and d != "_transient-files"
        ]

        for name in files:
            p = dpath / name
            if p.suffix in extensions:
                yield p


def should_exclude(relpath: str, exclude: set[str]) -> bool:
    # exact file match
    if relpath in exclude:
        return True

    # prefix folder match (e.g. "_transient-files")
    for item in exclude:
        if item.endswith("/"):
            if relpath.startswith(item):
                return True
        else:
            # allow excluding whole top-level dirs by listing them without trailing slash
            if "/" not in item and relpath.split("/", 1)[0] == item:
                return True

    return False


# -----------------------------
# Git metadata
# -----------------------------
def get_git_meta(repo_root: Path) -> dict:
    def run(cmd: list[str]) -> str:
        try:
            out = subprocess.check_output(cmd, cwd=repo_root, stderr=subprocess.DEVNULL)
            return out.decode().strip()
        except Exception:
            return ""

    return {
        "git_branch": run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "git_commit": run(["git", "rev-parse", "--short", "HEAD"]),
    }


# -----------------------------
# Python-only helpers
# -----------------------------
def compute_module(relpath: str) -> Optional[str]:
    # heuristic: find ".../src/<pkg>/.../file.py"
    parts = relpath.split("/")
    if "src" not in parts:
        return None
    i = parts.index("src")
    tail = parts[i + 1 :]
    if not tail or not tail[-1].endswith(".py"):
        return None
    tail[-1] = tail[-1][:-3]  # strip .py
    return ".".join(tail)


def infer_role(relpath: str) -> str:
    p = relpath.lower()
    for key in ROLE_KEYS:
        if f"/{key}/" in p or p.endswith(f"/{key}.py"):
            return key
    return "module"


def compute_neighbors(file_path: Path, max_items: int = 6) -> Optional[str]:
    siblings = sorted([p.name for p in file_path.parent.glob("*.py") if p.name != file_path.name])
    if not siblings:
        return None

    prioritized = [n for n in PRIORITY_NEIGHBORS if n in siblings]
    remaining = [n for n in siblings if n not in set(prioritized)]
    ordered = prioritized + remaining

    shown = ordered[:max_items]
    extra = len(ordered) - len(shown)
    if extra > 0:
        return f"{', '.join(shown)} (+{extra} more)"
    return ", ".join(shown)


def extract_exports_from_python(text: str, max_items: int = 8) -> Optional[str]:
    """
    Returns a concise string like: "Foo, Bar, baz" (classes first, then functions),
    limited to max_items. If __all__ exists and is statically resolvable, prefer it.
    """
    try:
        tree = ast.parse(text)
    except Exception:
        return None

    # 1) Prefer __all__ if it is a simple literal list/tuple of strings
    all_names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    value = node.value
                    elts = None
                    if isinstance(value, (ast.List, ast.Tuple)):
                        elts = value.elts
                    if elts is not None:
                        for e in elts:
                            if isinstance(e, ast.Constant) and isinstance(e.value, str):
                                all_names.append(e.value)
                    if all_names:
                        shown = all_names[:max_items]
                        extra = len(all_names) - len(shown)
                        return f"{', '.join(shown)}" + (f" (+{extra} more)" if extra > 0 else "")
                    break

    # 2) Otherwise: top-level defs/classes (ignore private _names)
    classes: list[str] = []
    funcs: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            funcs.append(node.name)

    names = classes + funcs
    if not names:
        return None

    shown = names[:max_items]
    extra = len(names) - len(shown)
    return f"{', '.join(shown)}" + (f" (+{extra} more)" if extra > 0 else "")


# -----------------------------
# Header insertion / replacement
# -----------------------------
def detect_insertion_index_py(lines: list[str]) -> int:
    idx = 0
    if idx < len(lines) and SHEBANG_RE.match(lines[idx]):
        idx += 1
    if idx < len(lines) and ENCODING_RE.match(lines[idx]):
        idx += 1
    return idx


def remove_legacy_path_comment(lines: list[str], relpath: str) -> list[str]:
    """
    Remove old single-line path comment that exactly matches "# <relpath>".
    """
    legacy = f"# {relpath}"
    out: list[str] = []
    removed = False
    for line in lines:
        if not removed and line.strip() == legacy:
            removed = True
            continue
        out.append(line)
    return out


def has_real_header_block(lines: list[str], search_first_n: int = 160) -> bool:
    """
    True only if we find a *real* header marker line (exact match),
    not merely a string literal containing BEGIN/END.
    """
    limit = min(len(lines), search_first_n)
    try:
        begin_i = next(i for i in range(limit) if lines[i].strip() == BEGIN)
    except StopIteration:
        return False

    for j in range(begin_i + 1, limit):
        if lines[j].strip() == END:
            return True

    return False


def build_block(
    *,
    relpath: str,
    module: Optional[str],
    git_meta: dict,
    role: str,
    neighbors: Optional[str],
    exports: Optional[str],
) -> list[str]:
    lines = [
        BEGIN,
        f"# path: {relpath}",
    ]
    if module:
        lines.append(f"# module: {module}")
    lines.append(f"# role: {role}")
    if neighbors:
        lines.append(f"# neighbors: {neighbors}")
    if exports:
        lines.append(f"# exports: {exports}")
    if git_meta.get("git_branch"):
        lines.append(f"# git_branch: {git_meta['git_branch']}")
    if git_meta.get("git_commit"):
        lines.append(f"# git_commit: {git_meta['git_commit']}")
    lines.append(END)
    return lines


def insert_or_replace_header(
    text: str,
    header_lines: list[str],
    *,
    relpath: str,
    is_python: bool,
    remove_legacy: bool,
) -> str:
    lines = text.splitlines()
    idx = detect_insertion_index_py(lines) if is_python else 0

    if has_real_header_block(lines, search_first_n=160):
        # replace the first real header block occurrence
        limit = min(len(lines), 160)
        begin_i = next(i for i in range(limit) if lines[i].strip() == BEGIN)

        out: list[str] = []
        out.extend(lines[:begin_i])
        out.extend(header_lines)

        # skip until END
        end_i = begin_i + 1
        while end_i < len(lines) and lines[end_i].strip() != END:
            end_i += 1
        if end_i < len(lines):
            end_i += 1  # skip END line too

        out.extend(lines[end_i:])
        new_lines = out
    else:
        # insert at idx
        new_lines = lines[:idx] + header_lines + [""] + lines[idx:]

    if is_python and remove_legacy:
        new_lines = remove_legacy_path_comment(new_lines, relpath)

    return "\n".join(new_lines) + ("\n" if text.endswith("\n") else "")


# -----------------------------
# CLI
# -----------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Add/update QV-LLM header blocks for repo files.")
    ap.add_argument("--scope", default=".", help="Directory to process")
    ap.add_argument(
        "--extensions",
        default=",".join(DEFAULT_EXTENSIONS),
        help="Comma-separated extensions to process (e.g. .py,.toml,.yml)",
    )
    ap.add_argument(
        "--exclude",
        default=",".join(sorted(DEFAULT_EXCLUDE)),
        help="Comma-separated relpaths or top-level dirs to exclude (e.g. scripts,_transient-files,foo/bar.py)",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-neighbors", type=int, default=6)
    ap.add_argument("--max-exports", type=int, default=8)
    ap.add_argument(
        "--remove-legacy-path-line",
        action="store_true",
        help="Remove legacy '# <relpath>' single-line comments (Python only).",
    )
    args = ap.parse_args()

    scope = Path(args.scope).resolve()
    repo_root = Path(".").resolve()
    git_meta = get_git_meta(repo_root)

    exts = tuple(e.strip() for e in args.extensions.split(",") if e.strip())
    exclude = {e.strip() for e in args.exclude.split(",") if e.strip()}

    changed = 0
    total = 0
    skipped = 0

    for f in sorted(iter_files(scope, exts)):
        rel = f.relative_to(repo_root).as_posix()

        if should_exclude(rel, exclude):
            skipped += 1
            continue

        is_python = f.suffix == ".py"
        original = f.read_text(encoding="utf-8", errors="replace")

        module = compute_module(rel) if is_python else None
        role = infer_role(rel)
        neighbors = compute_neighbors(f, max_items=args.max_neighbors) if is_python else None
        exports = extract_exports_from_python(original, max_items=args.max_exports) if is_python else None

        header = build_block(
            relpath=rel,
            module=module,
            git_meta=git_meta,
            role=role,
            neighbors=neighbors,
            exports=exports,
        )

        updated = insert_or_replace_header(
            original,
            header,
            relpath=rel,
            is_python=is_python,
            remove_legacy=args.remove_legacy_path_line,
        )

        total += 1
        if updated != original:
            changed += 1
            if args.dry_run:
                print(f"[DRY] would update: {rel}")
            else:
                f.write_text(updated, encoding="utf-8")
                print(f"updated: {rel}")

    print(f"done: {changed}/{total} files updated, {skipped} skipped (extensions: {exts})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

