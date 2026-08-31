"""
Policy-enforcing request builder for Google Docs `batchUpdate`.

Per RULING-408 DESIGN-03 approach B: `DocsRequestBuilder` is NOT a thin list
wrapper -- it enforces the one hazard-avoidance policy that matters for Docs
body edits: requests must be sent to `batchUpdate` in DESCENDING index order.

Why: Docs represents document content as a flat sequence of UTF-16 code
units, and every `Request` that touches the body (`insertText`,
`deleteContentRange`, `insertInlineImage`, etc.) is anchored to an index (or
a range of indices) into that sequence. `batchUpdate` applies its `requests`
list in the given ORDER, each one mutating the document before the next is
applied. If an edit at a lower index is applied first, it shifts every index
after it (insert grows the document, delete shrinks it) -- so a second
request's index, computed against the ORIGINAL document, silently points at
the wrong place (or an out-of-range place) once the document has already
been mutated by the first. Applying from the highest index down avoids this
entirely: an edit at a high index never disturbs the indices of edits that
still need to happen at lower indices.

This mirrors an existing ordering-hazard precedent already in the repo for
Drive/other integrations (per the spawn brief; not re-derived here, built to
the same shape: a builder that enforces a documented ordering invariant
rather than trusting every caller to already know and apply it themselves).
"""

from typing import Any


def _request_sort_index(request: dict[str, Any]) -> int:
    """
    Extract the anchoring index used to order a single Docs `Request` dict
    for `batchUpdate` submission.

    Docs `Request` union members that touch the body carry their anchor
    index in different places depending on the request kind:

    - Range-based requests (`deleteContentRange`, `insertPageBreak`
      inside a range, `updateTextStyle`, `updateParagraphStyle`, etc.)
      anchor on `range.startIndex`.
    - `insertText` anchors on `location.index` (a single point).
    - Requests with no discoverable index (e.g. `replaceAllText`, which
      matches by string rather than offset, or any other index-free
      request kind) sort last-most-in-forward-terms -- i.e. FIRST when
      applied in descending order, since they carry no risk of index
      invalidation and there is nothing more "downstream" to shift past.
      Using -1 here means they end up at the END of the descending-sorted
      list (executed last of all), which is a safe, arbitrary tie-break:
      they don't move any index-anchored request's anchor because they
      don't touch the body via an index at all.

    Args:
        request: A single Docs `Request` dict, e.g.
            `{"insertText": {"location": {"index": 5}, "text": "hi"}}` or
            `{"deleteContentRange": {"range": {"startIndex": 3, "endIndex":
            7}}}`.

    Returns:
        The integer index to sort on, or -1 if this request kind carries
        no body-anchoring index.
    """
    for _kind, payload in request.items():
        if not isinstance(payload, dict):
            continue

        location = payload.get("location")
        if isinstance(location, dict) and isinstance(location.get("index"), int):
            return int(location["index"])

        range_ = payload.get("range")
        if isinstance(range_, dict) and isinstance(range_.get("startIndex"), int):
            return int(range_["startIndex"])

        end_of_segment = payload.get("endOfSegmentLocation")
        if isinstance(end_of_segment, dict):
            # endOfSegmentLocation has no numeric index by definition (it
            # means "wherever the end of the segment currently is") -- it
            # is never invalidated by an earlier edit shifting indices, so
            # it is safe to run at any point. Treat it like an index-free
            # request for sort purposes.
            return -1

    return -1


class DocsRequestBuilder:
    """Policy-enforcing builder for a Google Docs `batchUpdate` request
    list.

    Callers add `Request` dicts (each shaped exactly like the real Docs API
    `Request` union member, e.g. `{"insertText": {...}}`,
    `{"deleteContentRange": {...}}`) via `add()`, or construct the builder
    directly from an existing list via `from_requests()`. `build()` returns
    the requests reverse-sorted by their body-anchoring index, ready to hand
    to `documents.batchUpdate(body={"requests": builder.build()})` -- this
    is the ONE policy this class exists to enforce; it is intentionally not
    a generic list wrapper.
    """

    def __init__(self) -> None:
        """Initialize an empty request builder."""
        self._requests: list[dict[str, Any]] = []

    @classmethod
    def from_requests(cls, requests: list[dict[str, Any]]) -> "DocsRequestBuilder":
        """
        Construct a builder pre-loaded with an existing list of requests.

        Args:
            requests: Docs API `Request` dicts, in any order.

        Returns:
            A new `DocsRequestBuilder` containing `requests`.
        """
        builder = cls()
        builder._requests.extend(requests)
        return builder

    def add(self, request: dict[str, Any]) -> "DocsRequestBuilder":
        """
        Add a single Docs API `Request` dict to the builder.

        Args:
            request: A Docs API `Request` dict, e.g.
                `{"insertText": {"location": {"index": 5}, "text": "hi"}}`.

        Returns:
            self, for chaining.
        """
        self._requests.append(request)
        return self

    def __len__(self) -> int:
        """Number of requests currently queued."""
        return len(self._requests)

    def build(self) -> list[dict[str, Any]]:
        """
        Return the queued requests reverse-sorted by their body-anchoring
        index (descending), ready for `batchUpdate`.

        Applying edits from the highest index down means an edit never
        shifts the index that a not-yet-applied, lower-indexed edit is
        anchored to -- see this module's docstring for the full rationale.
        Python's `sorted()` is stable, so requests that share the same
        (or no) index keep their original relative order.

        Returns:
            The requests, ordered highest-index-first.
        """
        return sorted(self._requests, key=_request_sort_index)
