"""Tests for `DocsRequestBuilder` -- the policy-enforcing reverse-sort-by-
index builder (RULING-408 DESIGN-03). This is one of the two candidate
guards named in the spawn brief for the live mutation test (see this
package's service tests for the other candidate, the recursive table-
descent in text extraction)."""

from typing import Any

from zeo_core.integrations.google.docs.request_builder import (
    DocsRequestBuilder,
    _request_sort_index,
)


class TestRequestSortIndex:
    def test_location_index(self) -> None:
        request = {"insertText": {"location": {"index": 42}, "text": "hi"}}
        assert _request_sort_index(request) == 42

    def test_range_start_index(self) -> None:
        request = {"deleteContentRange": {"range": {"startIndex": 10, "endIndex": 20}}}
        assert _request_sort_index(request) == 10

    def test_end_of_segment_location_sorts_last(self) -> None:
        request = {"insertText": {"endOfSegmentLocation": {}, "text": "end"}}
        assert _request_sort_index(request) == -1

    def test_index_free_request_sorts_last(self) -> None:
        request = {
            "replaceAllText": {
                "containsText": {"text": "a", "matchCase": False},
                "replaceText": "b",
            }
        }
        assert _request_sort_index(request) == -1

    def test_non_dict_payload_ignored(self) -> None:
        # A malformed/unexpected request shape (payload not a dict) should
        # not raise; it should simply not contribute an index.
        request = {"someWeirdKind": "not-a-dict"}
        assert _request_sort_index(request) == -1


class TestDocsRequestBuilderAddAndLen:
    def test_add_returns_self_for_chaining(self) -> None:
        builder = DocsRequestBuilder()
        result = builder.add({"insertText": {"location": {"index": 1}, "text": "a"}})
        assert result is builder

    def test_len_tracks_queued_requests(self) -> None:
        builder = DocsRequestBuilder()
        assert len(builder) == 0
        builder.add({"insertText": {"location": {"index": 1}, "text": "a"}})
        assert len(builder) == 1
        builder.add({"insertText": {"location": {"index": 2}, "text": "b"}})
        assert len(builder) == 2

    def test_from_requests_preloads(self) -> None:
        requests: list[dict[str, Any]] = [
            {"insertText": {"location": {"index": 1}, "text": "a"}},
            {"insertText": {"location": {"index": 2}, "text": "b"}},
        ]
        builder = DocsRequestBuilder.from_requests(requests)
        assert len(builder) == 2


class TestDocsRequestBuilderReverseSort:
    """The core policy this class exists to enforce: build() returns
    requests reverse-sorted (descending) by their body-anchoring index."""

    def test_reverse_sorts_ascending_input_by_index(self) -> None:
        # Construct requests with insert/delete at multiple different
        # indices in ASCENDING order as input (per the spawn brief's
        # required specific test).
        requests: list[dict[str, Any]] = [
            {"insertText": {"location": {"index": 5}, "text": "a"}},
            {"deleteContentRange": {"range": {"startIndex": 10, "endIndex": 15}}},
            {"insertText": {"location": {"index": 20}, "text": "b"}},
        ]

        builder = DocsRequestBuilder.from_requests(requests)
        ordered = builder.build()

        # Assert descending-index order in the output.
        assert ordered[0]["insertText"]["location"]["index"] == 20
        assert ordered[1]["deleteContentRange"]["range"]["startIndex"] == 10
        assert ordered[2]["insertText"]["location"]["index"] == 5

    def test_reverse_sorts_already_descending_input_unchanged(self) -> None:
        requests: list[dict[str, Any]] = [
            {"insertText": {"location": {"index": 30}, "text": "c"}},
            {"insertText": {"location": {"index": 10}, "text": "a"}},
        ]
        ordered = DocsRequestBuilder.from_requests(requests).build()
        assert ordered[0]["insertText"]["location"]["index"] == 30
        assert ordered[1]["insertText"]["location"]["index"] == 10

    def test_index_free_requests_execute_last(self) -> None:
        requests: list[dict[str, Any]] = [
            {
                "replaceAllText": {
                    "containsText": {"text": "x", "matchCase": False},
                    "replaceText": "y",
                }
            },
            {"insertText": {"location": {"index": 3}, "text": "a"}},
        ]
        ordered = DocsRequestBuilder.from_requests(requests).build()
        assert "insertText" in ordered[0]
        assert "replaceAllText" in ordered[1]

    def test_empty_builder_returns_empty_list(self) -> None:
        assert DocsRequestBuilder().build() == []

    def test_stable_sort_preserves_relative_order_for_ties(self) -> None:
        requests: list[dict[str, Any]] = [
            {"insertText": {"location": {"index": 5}, "text": "first"}},
            {"insertText": {"location": {"index": 5}, "text": "second"}},
        ]
        ordered = DocsRequestBuilder.from_requests(requests).build()
        assert ordered[0]["insertText"]["text"] == "first"
        assert ordered[1]["insertText"]["text"] == "second"
