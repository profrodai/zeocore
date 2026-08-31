"""Rich-text facet computation for Bluesky posts.

RULING-409 s6c/6b names this the one real implementation wrinkle in an
otherwise trivial provider: a facet's `index` is a **UTF-8 BYTE** range
(`byteStart`/`byteEnd`), never a character or codepoint offset. Python
string indexing is codepoint-based, so `text.find(...)` positions must be
converted to byte offsets before being placed in a facet, or every post
containing a non-ASCII character before a link/mention will corrupt the
facet's placement (and, for text with 4-byte codepoints like most emoji,
`str` indexing and UTF-8 byte indexing diverge on ASCII-only text too, the
moment ANY prior character is outside the BMP or non-ASCII).

Every shape here is read from the official AT Protocol lexicon,
`app.bsky.richtext.facet` (`lexicons/app/bsky/richtext/facet.json`,
bluesky-social/atproto) -- never from Postiz (RULING-409 s1/s6b A: Postiz is
a specification and test oracle at most, never a source, including in
translation). The lexicon's `ByteSlice` requires `byteStart`/`byteEnd`
(both non-negative integers, `byteStart` inclusive, `byteEnd` exclusive);
`Main` requires `index` plus a `features` array; `Link` requires `uri`;
`Mention` requires `did` (the account's DID, not its handle -- the visible
text is the "@handle" substring, but the facet references the resolved
identity, which this module does not resolve on its own: callers pass the
DID they already have).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LinkSpan:
    """A URL substring to annotate as a link facet.

    `text` is the exact substring as it appears in the post body (used to
    locate its byte offsets); `uri` is the facet's target, which the
    lexicon explicitly allows to differ from the visible text ("The text
    URL may have been simplified or truncated, but the facet reference
    should be a complete URL").
    """

    text: str
    uri: str


@dataclass(frozen=True)
class MentionSpan:
    """An "@handle" substring to annotate as a mention facet.

    `text` is the exact "@handle" substring as it appears in the post body;
    `did` is the resolved account DID the mention refers to. Resolving a
    handle to a DID is a separate AT Protocol call
    (`com.atproto.identity.resolveHandle`) this module does not perform --
    callers supply the DID they already resolved.
    """

    text: str
    did: str


def _byte_offset(text: str, char_offset: int) -> int:
    """The UTF-8 byte offset corresponding to `text[:char_offset]`.

    This is the whole wrinkle: `len(text[:char_offset].encode("utf-8"))` is
    NOT `char_offset` whenever any character before it is outside ASCII,
    because Python string indexing is codepoint-based while the AT Protocol
    facet spec is byte-based.
    """
    return len(text[:char_offset].encode("utf-8"))


def compute_facets(
    text: str,
    links: list[LinkSpan] | None = None,
    mentions: list[MentionSpan] | None = None,
) -> list[dict[str, object]]:
    """Compute `app.bsky.richtext.facet`-shaped facets for `text`.

    Locates each `LinkSpan`/`MentionSpan`'s `text` substring inside the
    post body (first occurrence, left to right) and converts its character
    offsets to UTF-8 byte offsets. A span whose text is not found in
    `text` is silently skipped -- not raised -- because a caller passing a
    mismatched substring (e.g. from independently-truncated text) should
    degrade to a plain-text post rather than fail outright; RULING-409's own
    scope note says facets are only on the critical path when the rest is
    solid, so a defensive skip here keeps posting itself never blocked by a
    facet computation edge case.

    Args:
        text: The full post text these spans are located within.
        links: Link spans to annotate.
        mentions: Mention spans to annotate.

    Returns:
        A list of facet dicts, each shaped
        `{"index": {"byteStart": int, "byteEnd": int}, "features": [...]}`,
        sorted by `byteStart` (the lexicon does not require sorted facets,
        but sorted output is deterministic and easier to review/test).
    """
    facets: list[dict[str, object]] = []

    for link in links or []:
        char_start = text.find(link.text)
        if char_start == -1:
            continue
        char_end = char_start + len(link.text)
        facets.append(
            {
                "index": {
                    "byteStart": _byte_offset(text, char_start),
                    "byteEnd": _byte_offset(text, char_end),
                },
                "features": [
                    {"$type": "app.bsky.richtext.facet#link", "uri": link.uri}
                ],
            }
        )

    for mention in mentions or []:
        char_start = text.find(mention.text)
        if char_start == -1:
            continue
        char_end = char_start + len(mention.text)
        facets.append(
            {
                "index": {
                    "byteStart": _byte_offset(text, char_start),
                    "byteEnd": _byte_offset(text, char_end),
                },
                "features": [
                    {"$type": "app.bsky.richtext.facet#mention", "did": mention.did}
                ],
            }
        )

    def _byte_start(facet: dict[str, object]) -> int:
        index = facet["index"]
        assert isinstance(index, dict)  # noqa: S101 -- narrows dict[str, object]'s
        # value type back to a concrete dict for mypy; this module's own
        # facet dicts always shape "index" this way (built two blocks above),
        # so this is a real invariant, not a test-only assertion.
        byte_start = index["byteStart"]
        assert isinstance(byte_start, int)  # noqa: S101 -- same reasoning
        return byte_start

    facets.sort(key=_byte_start)
    return facets
