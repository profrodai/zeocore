#!/usr/bin/env python3
# === QV-LLM:BEGIN ===
# path: scripts/flatten.py
# role: module
# neighbors: annotate_headers.py, fix_imports.py, fix_remaining_tests.py, verify_installation.py
# exports: FileStat, should_skip_dir, iter_files, safe_slug, read_text_file, count_lines, flatten_to_file, write_manifest (+1 more)
# git_branch: feat/9-make-setup-work
# git_commit: 2f6d56ab
# === QV-LLM:END ===

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

DEFAULT_EXTENSIONS = [".py", ".yaml", ".yml", ".toml", ".env", ".example", ".md"]
DEFAULT_SKIP_DIR_PARTS = [
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
]

BANNER_WIDTH = 88


@dataclass(frozen=True)
class FileStat:
    relpath: str
    bytes: int
    lines: int


def should_skip_dir(path: Path, skip_parts: List[str]) -> bool:
    s = str(path)
    return any(part in s.split(os.sep) for part in skip_parts)


def iter_files(
    root: Path,
    extensions: Tuple[str, ...],
    skip_dir_parts: List[str],
    exclude_globs: List[str],
) -> Iterable[Path]:
    root = root.resolve()

    for dirpath, dirs, files in os.walk(root):
        dpath = Path(dirpath)

        # prune dirs in-place
        pruned = []
        for d in dirs:
            dp = dpath / d
            if should_skip_dir(dp, skip_dir_parts):
                continue
            pruned.append(d)
        dirs[:] = pruned

        for name in files:
            p = dpath / name
            if p.suffix not in extensions:
                continue

            rel = p.relative_to(root)

            # exclusions
            excluded = False
            for g in exclude_globs:
                if rel.match(g):
                    excluded = True
                    break
            if excluded:
                continue

            yield p


def safe_slug(path: str) -> str:
    return path.replace("/", "__").replace("\\", "__").replace(":", "")


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def count_lines(text: str) -> int:
    # handle files without trailing newline consistently
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def flatten_to_file(
    *,
    scope_root: Path,
    files: List[Path],
    out_path: Path,
    max_bytes: int | None,
    max_files: int | None,
) -> Tuple[List[FileStat], dict]:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    stats: List[FileStat] = []
    total_bytes = 0
    digest = hashlib.sha256()

    if max_files is not None:
        files = files[:max_files]

    with out_path.open("w", encoding="utf-8") as out:
        for p in files:
            rel = str(p.relative_to(scope_root)).replace("\\", "/")
            content = read_text_file(p)

            b = len(content.encode("utf-8", errors="replace"))
            if max_bytes is not None and total_bytes + b > max_bytes:
                break

            total_bytes += b
            digest.update(content.encode("utf-8", errors="replace"))

            out.write("=" * BANNER_WIDTH + "\n")
            out.write(f"FILE: {rel}\n")
            out.write("=" * BANNER_WIDTH + "\n\n")
            out.write(content)
            if not content.endswith("\n"):
                out.write("\n")
            out.write("\n")

            stats.append(FileStat(relpath=rel, bytes=b, lines=count_lines(content)))

    meta = {
        "out_path": str(out_path),
        "files_written": len(stats),
        "bytes_written": total_bytes,
        "sha256": digest.hexdigest(),
    }
    return stats, meta


def write_manifest(out_dir: Path, manifest: dict) -> None:
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # human-friendly
    lines = []
    lines.append("# Flatten manifest\n")
    for entry in manifest.get("outputs", []):
        lines.append(f"## {entry['name']}\n")
        lines.append(f"- Path: `{entry['out_path']}`")
        lines.append(f"- Files: {entry['files_written']}")
        lines.append(f"- Lines: {entry['lines_written']}")
        lines.append(f"- Bytes: {entry['bytes_written']}")
        lines.append(f"- SHA256: `{entry['sha256']}`\n")

        top = entry.get("top_files", [])
        if top:
            lines.append("Top files:\n")
            for t in top:
                lines.append(f"- {t['relpath']} — {t['lines']} lines")
            lines.append("")
    (out_dir / "manifest.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Flatten code into shareable text bundles.")
    ap.add_argument("--mode", choices=["scope", "tree"], default="scope")
    ap.add_argument("--scope", required=True, help="Directory to flatten (relative or absolute).")
    ap.add_argument("--out-dir", default="_transient-files/flatten", help="Output base directory.")
    ap.add_argument("--extensions", default=",".join(DEFAULT_EXTENSIONS))
    ap.add_argument("--skip-dirs", default=",".join(DEFAULT_SKIP_DIR_PARTS))
    ap.add_argument("--exclude", action="append", default=[], help="Glob patterns to exclude (repeatable).")
    ap.add_argument("--max-bytes", type=int, default=None, help="Cap total bytes written per output.")
    ap.add_argument("--max-files", type=int, default=None, help="Cap number of files per output.")
    args = ap.parse_args()

    scope_root = Path(args.scope).resolve()
    out_dir = Path(args.out_dir).resolve()
    exts = tuple([e.strip() for e in args.extensions.split(",") if e.strip()])
    skip_dir_parts = [s.strip() for s in args.skip_dirs.split(",") if s.strip()]

    if not scope_root.exists() or not scope_root.is_dir():
        raise SystemExit(f"Scope directory not found: {scope_root}")

    outputs = []
    manifest = {"scope": str(scope_root), "mode": args.mode, "outputs": outputs}

    def output_entry(name: str, out_path: Path, stats: List[FileStat], meta: dict):
        top_files = sorted(stats, key=lambda x: x.lines, reverse=True)[:10]
        outputs.append(
            {
                "name": name,
                **meta,
                "lines_written": sum(s.lines for s in stats),
                "top_files": [{"relpath": t.relpath, "lines": t.lines} for t in top_files],
            }
        )

    if args.mode == "scope":
        files = sorted(iter_files(scope_root, exts, skip_dir_parts, args.exclude))
        out_path = out_dir / "scopes" / f"{safe_slug(str(scope_root))}.flat.txt"
        stats, meta = flatten_to_file(
            scope_root=scope_root,
            files=files,
            out_path=out_path,
            max_bytes=args.max_bytes,
            max_files=args.max_files,
        )
        output_entry("scope", out_path, stats, meta)

    else:  # tree
        # one output per *immediate* child directory (plus __root__)
        children = [p for p in scope_root.iterdir() if p.is_dir() and not should_skip_dir(p, skip_dir_parts)]
        buckets = [("__root__", scope_root)] + [(c.name, c) for c in sorted(children)]

        base = out_dir / "tree" / safe_slug(str(scope_root))
        for name, sub in buckets:
            files = sorted(iter_files(sub, exts, skip_dir_parts, args.exclude))
            out_path = base / f"{name}.flat.txt"
            stats, meta = flatten_to_file(
                scope_root=scope_root,
                files=files,
                out_path=out_path,
                max_bytes=args.max_bytes,
                max_files=args.max_files,
            )
            output_entry(name, out_path, stats, meta)

    write_manifest(out_dir, manifest)
    print(f"Wrote outputs to: {out_dir}")
    print(f"- manifest: {out_dir / 'manifest.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
