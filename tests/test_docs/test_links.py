"""Keep repository-relative links in public documentation valid."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_DOC_NAMES = {
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "GET-STARTED.md",
    "README.md",
    "RELEASE_NOTES.md",
    "SECURITY.md",
}
LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(\s*<?([^)\s>]+)>?")
HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
EXPLICIT_ANCHOR_PATTERN = re.compile(
    r"""<(?:a|[A-Za-z][^>]*)\s+(?:id|name)=["']([^"']+)["']""",
    re.IGNORECASE,
)
MARKDOWN_FORMATTING_PATTERN = re.compile(r"[^\w\- ]", re.UNICODE)


def _public_markdown_files() -> Iterable[Path]:
    """Yield Markdown intended for package users and contributors."""
    yield from sorted(
        path for path in REPO_ROOT.glob("*.md") if path.name in ROOT_DOC_NAMES
    )
    yield REPO_ROOT / "docs" / "README.md"
    yield from sorted((REPO_ROOT / "docs" / "tutorials").glob("*.md"))
    yield from sorted((REPO_ROOT / "src" / "zeo_core" / "contracts").glob("*.md"))


def _github_slug(heading: str) -> str:
    """Approximate GitHub's stable heading-anchor generation."""
    plain = re.sub(r"<[^>]+>", "", heading)
    plain = re.sub(r"[*_`~]", "", plain).strip().lower()
    plain = MARKDOWN_FORMATTING_PATTERN.sub("", plain)
    return re.sub(r"\s+", "-", plain)


def _anchors(markdown: str) -> set[str]:
    """Return explicit and generated anchors, including duplicate suffixes."""
    anchors = {
        unquote(anchor).lower() for anchor in EXPLICIT_ANCHOR_PATTERN.findall(markdown)
    }
    counts: dict[str, int] = {}
    for heading in HEADING_PATTERN.findall(markdown):
        slug = _github_slug(heading)
        duplicate_number = counts.get(slug, 0)
        counts[slug] = duplicate_number + 1
        anchors.add(slug if duplicate_number == 0 else f"{slug}-{duplicate_number}")
    return anchors


def _resolve_target(source: Path, raw_target: str) -> tuple[Path, str]:
    """Resolve a Markdown target and separate its decoded fragment."""
    parsed = urlsplit(raw_target)
    target_path = unquote(parsed.path)
    if not target_path:
        target = source
    elif target_path.startswith("/"):
        target = REPO_ROOT / target_path.lstrip("/")
    else:
        target = source.parent / target_path
    return target.resolve(), unquote(parsed.fragment).lower()


def test_repository_relative_documentation_links_are_valid() -> None:
    """Fail with all missing paths and anchors so drift is easy to repair."""
    failures: list[str] = []

    for source in _public_markdown_files():
        markdown = source.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(markdown):
            parsed = urlsplit(raw_target)
            if parsed.scheme or raw_target.startswith("//"):
                continue

            target, fragment = _resolve_target(source, raw_target)
            display_source = source.relative_to(REPO_ROOT)
            try:
                target.relative_to(REPO_ROOT)
            except ValueError:
                failures.append(
                    f"{display_source}: link escapes repository: {raw_target}"
                )
                continue

            if not target.exists():
                failures.append(f"{display_source}: missing target: {raw_target}")
                continue

            if fragment and target.suffix.lower() == ".md":
                target_anchors = _anchors(target.read_text(encoding="utf-8"))
                if fragment not in target_anchors:
                    failures.append(
                        f"{display_source}: missing anchor in "
                        f"{target.relative_to(REPO_ROOT)}: #{fragment}"
                    )

    assert not failures, "Invalid documentation links:\n" + "\n".join(failures)
