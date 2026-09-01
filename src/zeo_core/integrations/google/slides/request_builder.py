"""
Policy-enforcing request builder for Google Slides `batchUpdate`.

Per RULING-408 DESIGN-03 approach B: `SlidesRequestBuilder` is NOT a thin
list wrapper -- it enforces the one hazard-avoidance policy that matters
for Slides `batchUpdate` requests, and that policy is the OPPOSITE of
Docs' own `DocsRequestBuilder` policy.

DO NOT COPY DOCS' SORT HERE. THIS IS NOT AN OVERSIGHT -- READ ON.
=====================================================================

`docs/request_builder.py` reverse-sorts its requests by body-anchoring
index before submission, because Docs represents document content as a
flat sequence of UTF-16 code units and every body-touching request is
anchored to a numeric index into that sequence -- an earlier edit at a
lower index shifts every index after it, so applying highest-index-first
avoids one edit invalidating another's already-computed index.

Slides has NO such index-shifting hazard, because Slides does not address
its objects by position at all. Every addressable object on a Slides page
(a slide, a shape, a text box, an image placeholder) carries a stable,
CALLER-ASSIGNABLE `objectId` string -- confirmed directly against the
Slides v1 discovery document (revision 20260828): `CreateSlideRequest`,
`CreateShapeRequest`, `CreateTextBoxRequest`, etc. all carry an `objectId`
field the caller may set explicitly. Nothing about applying one request
shifts the `objectId` any other request refers to -- `objectId`s are
opaque strings, not positions, so there is no analogue of Docs' index-
invalidation hazard to guard against by reordering.

Instead, Slides has the OPPOSITE hazard: a batch commonly contains a
CREATE request for some object (e.g. `{"createSlide": {"objectId":
"slide_1", ...}}`) immediately followed by requests that REFERENCE that
same `objectId` (e.g. `{"insertText": {"objectId": "slide_1", "text":
...}}`, or a second `createShape` whose `elementProperties.pageObjectId`
points at `"slide_1"`). The Slides API applies `batchUpdate`'s `requests`
list IN THE GIVEN ORDER, and a request that references an `objectId` no
prior request in the batch has created yet is rejected by the API at
apply time. So request N+1 in a caller's list routinely, and correctly,
depends on request N having already run -- meaning CALLER ORDER *IS* THE
DEPENDENCY GRAPH, and any reordering (by index, alphabetically, by
request kind, or any other key) can silently break a reference chain that
was correct as submitted.

The policy this builder enforces is therefore the mirror image of Docs':
PRESERVE CALLER ORDER, ALWAYS. `build()` returns exactly the sequence
`add()` was called in -- no `sorted()` call anywhere in this module, on
purpose. If a future maintainer is tempted to "fix" this by adding a sort
(e.g. because Docs has one and this file looks like it is missing the
same treatment): DON'T. That would reintroduce exactly the reference-
chain-breaking defect this docstring exists to prevent. This module's own
test suite mutation-tests this guard: a sort is added, a test that builds
a create-then-reference chain is confirmed to go red, and the sort is
removed again -- see `test_request_builder.py`.

The second policy this builder enforces: generating a caller-safe,
collision-resistant `objectId` when a caller wants one assigned rather
than inventing their own, so a caller building a create-then-reference
chain never has to hand-roll uniqueness.
"""

import uuid
from typing import Any


class SlidesRequestBuilder:
    """Policy-enforcing builder for a Google Slides `batchUpdate` request
    list.

    Callers add `Request` dicts (each shaped exactly like the real Slides
    API `Request` union member, e.g. `{"createSlide": {...}}`,
    `{"insertText": {...}}`) via `add()`, or construct the builder
    directly from an existing list via `from_requests()`. `build()`
    returns the requests in EXACTLY THE ORDER THEY WERE ADDED -- see this
    module's docstring for why that is the one policy this class exists
    to enforce (the opposite of `DocsRequestBuilder`'s reverse-sort).
    """

    def __init__(self) -> None:
        """Initialize an empty request builder."""
        self._requests: list[dict[str, Any]] = []

    @classmethod
    def from_requests(cls, requests: list[dict[str, Any]]) -> "SlidesRequestBuilder":
        """
        Construct a builder pre-loaded with an existing list of requests,
        in the given order.

        Args:
            requests: Slides API `Request` dicts, in caller-intended
                execution order.

        Returns:
            A new `SlidesRequestBuilder` containing `requests`.
        """
        builder = cls()
        builder._requests.extend(requests)
        return builder

    def add(self, request: dict[str, Any]) -> "SlidesRequestBuilder":
        """
        Add a single Slides API `Request` dict to the builder, appended
        after any requests already queued.

        Args:
            request: A Slides API `Request` dict, e.g.
                `{"createSlide": {"objectId": "slide_1"}}`.

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
        Return the queued requests in EXACTLY the order they were added
        or loaded -- no sort, no reordering of any kind.

        This is the one policy this class exists to enforce: preserving
        caller order so a request that references an `objectId` created
        by an earlier request in the same batch keeps that dependency
        intact. See this module's docstring for the full rationale and
        why this is the opposite of `DocsRequestBuilder.build()`.

        Returns:
            The requests, in the exact order supplied.
        """
        return list(self._requests)


def new_object_id(prefix: str = "obj") -> str:
    """
    Generate a caller-safe, collision-resistant Slides `objectId`.

    Slides `objectId`s are caller-assignable opaque strings (see this
    module's docstring) -- verified live against the Slides v1 discovery
    document (revision 20260828), `CreateSlideRequest.objectId`'s own
    field description requires: unique among all pages and page elements
    in the presentation; must START with an alphanumeric character or an
    underscore (`[a-zA-Z0-9_]`); remaining characters may additionally
    include a hyphen or colon (`[a-zA-Z0-9_-:]`); length between 5 and 50
    characters inclusive. `f"{prefix}_{uuid.uuid4().hex}"` satisfies all
    of that: `prefix` is caller-supplied and expected alphanumeric, the
    fixed `uuid4().hex` suffix (32 lowercase hex characters) is itself
    alphanumeric, and the joined length (`len(prefix) + 33`) stays well
    under 50 for any reasonably short prefix.

    Args:
        prefix: A short, human-readable label prepended to the generated
            id (e.g. `"slide"`, `"shape"`, `"box"`), purely for
            readability when debugging a batch -- carries no meaning to
            the Slides API itself.

    Returns:
        A new `objectId` string, unique with overwhelming probability
        across calls.
    """
    return f"{prefix}_{uuid.uuid4().hex}"
