"""Tests for Bluesky rich-text facet byte-offset computation.

The wrinkle RULING-409 s6c names explicitly: facet indices are UTF-8 BYTE
offsets, not character offsets. These tests specifically exercise the case
where they diverge -- multi-byte characters preceding the span being
annotated -- because that divergence is exactly what a naive
`str.find()`-only implementation gets wrong.
"""

from zeo_core.integrations.social.bluesky.facets import (
    LinkSpan,
    MentionSpan,
    compute_facets,
)


def _index(facet: dict[str, object]) -> dict[str, int]:
    """Narrow a facet's `"index"` value (typed `object` on the
    `dict[str, object]` `compute_facets` returns) back to the concrete
    `dict[str, int]` it always actually is, for mypy's benefit in these
    tests."""
    index = facet["index"]
    assert isinstance(index, dict)
    return index


def _features(facet: dict[str, object]) -> list[dict[str, object]]:
    """Same narrowing, for `"features"`."""
    features = facet["features"]
    assert isinstance(features, list)
    return features


class TestComputeFacetsAscii:
    def test_single_link_pure_ascii(self) -> None:
        text = "Check out https://example.com today"
        facets = compute_facets(
            text,
            links=[LinkSpan(text="https://example.com", uri="https://example.com")],
        )

        assert len(facets) == 1
        facet = facets[0]
        char_start = text.index("https://example.com")
        char_end = char_start + len("https://example.com")
        # Pure ASCII: byte offsets equal character offsets.
        assert _index(facet) == {"byteStart": char_start, "byteEnd": char_end}
        assert _features(facet) == [
            {"$type": "app.bsky.richtext.facet#link", "uri": "https://example.com"}
        ]

    def test_single_mention(self) -> None:
        text = "hello @alice.bsky.social welcome"
        facets = compute_facets(
            text,
            mentions=[MentionSpan(text="@alice.bsky.social", did="did:plc:abc123")],
        )

        assert len(facets) == 1
        facet = facets[0]
        char_start = text.index("@alice.bsky.social")
        assert _index(facet)["byteStart"] == char_start
        assert _features(facet) == [
            {"$type": "app.bsky.richtext.facet#mention", "did": "did:plc:abc123"}
        ]


class TestComputeFacetsMultiByte:
    """The actual wrinkle: byte offsets must diverge from character offsets
    when a multi-byte UTF-8 character precedes the annotated span."""

    def test_link_after_multibyte_emoji_diverges_from_char_offset(self) -> None:
        # 🎉 is a 4-byte UTF-8 codepoint but ONE Python string character.
        text = "🎉 check https://example.com"
        char_start = text.index("https://example.com")
        # Byte offset must be 3 bytes further than char offset: 🎉 is 4
        # bytes in UTF-8 but len("🎉") == 1 as a Python str.
        expected_byte_start = len("🎉".encode()) + len(" check ")

        facets = compute_facets(
            text,
            links=[LinkSpan(text="https://example.com", uri="https://example.com")],
        )

        assert len(facets) == 1
        byte_start = _index(facets[0])["byteStart"]
        assert byte_start != char_start, (
            "byte offset must differ from char offset once a multi-byte "
            "character precedes the span -- if this assertion fails the "
            "implementation is silently using character offsets"
        )
        assert byte_start == expected_byte_start

        # Round-trip proof: slicing the UTF-8 BYTES of text at
        # [byteStart:byteEnd] recovers exactly the link's own text -- this
        # is what a real AT Protocol client does to render the facet, so
        # it is the actual behavioral proof, not just an arithmetic check.
        byte_end = _index(facets[0])["byteEnd"]
        text_bytes = text.encode("utf-8")
        assert text_bytes[byte_start:byte_end].decode("utf-8") == "https://example.com"

    def test_mention_after_non_ascii_accented_text(self) -> None:
        # "café" -- 'é' is 2 bytes in UTF-8 but 1 Python character.
        text = "café @bob.bsky.social"
        char_start = text.index("@bob.bsky.social")

        facets = compute_facets(
            text, mentions=[MentionSpan(text="@bob.bsky.social", did="did:plc:xyz")]
        )

        byte_start = _index(facets[0])["byteStart"]
        # "café " as chars is 5 chars; as UTF-8 bytes it is 6 (é is 2 bytes).
        assert byte_start == char_start + 1
        text_bytes = text.encode("utf-8")
        byte_end = _index(facets[0])["byteEnd"]
        assert text_bytes[byte_start:byte_end].decode("utf-8") == "@bob.bsky.social"


class TestComputeFacetsMultipleAndEdgeCases:
    def test_multiple_links_and_mentions_sorted_by_byte_start(self) -> None:
        text = "@alice.bsky.social said check https://example.com please"
        facets = compute_facets(
            text,
            links=[LinkSpan(text="https://example.com", uri="https://example.com")],
            mentions=[MentionSpan(text="@alice.bsky.social", did="did:plc:abc")],
        )

        assert len(facets) == 2
        # Mention comes first in the text, so it must be sorted first.
        starts = [_index(f)["byteStart"] for f in facets]
        assert starts == sorted(starts)
        assert _features(facets[0])[0]["$type"] == "app.bsky.richtext.facet#mention"
        assert _features(facets[1])[0]["$type"] == "app.bsky.richtext.facet#link"

    def test_no_spans_returns_empty_list(self) -> None:
        assert compute_facets("plain text, no links or mentions") == []

    def test_span_text_not_found_is_skipped_not_raised(self) -> None:
        # A caller-supplied link text that doesn't actually appear in the
        # post body degrades to "no facet for it" rather than raising --
        # posting itself must never be blocked by a facet mismatch.
        facets = compute_facets(
            "hello world",
            links=[
                LinkSpan(text="https://not-in-text.example", uri="https://x.example")
            ],
        )
        assert facets == []

    def test_mention_text_not_found_is_skipped_not_raised(self) -> None:
        facets = compute_facets(
            "hello world",
            mentions=[MentionSpan(text="@not-in-text.bsky.social", did="did:plc:x")],
        )
        assert facets == []

    def test_byte_slice_round_trips_for_every_facet_multiple_emoji(self) -> None:
        text = "🎉🎉 great news https://example.com and @carol.bsky.social too"
        facets = compute_facets(
            text,
            links=[LinkSpan(text="https://example.com", uri="https://example.com")],
            mentions=[MentionSpan(text="@carol.bsky.social", did="did:plc:carol")],
        )
        text_bytes = text.encode("utf-8")
        for facet in facets:
            start = _index(facet)["byteStart"]
            end = _index(facet)["byteEnd"]
            # Must decode cleanly -- a wrong (character-based) offset would
            # very likely land mid-codepoint and raise UnicodeDecodeError,
            # or simply decode to the wrong substring.
            recovered = text_bytes[start:end].decode("utf-8")
            assert recovered in (
                "https://example.com",
                "@carol.bsky.social",
            )
