"""Tests for `SlidesRequestBuilder` -- the policy-enforcing ORDER-
PRESERVING builder (RULING-408 DESIGN-03), and its `new_object_id` helper.
This is the OPPOSITE policy from `docs/request_builder.py`'s reverse-sort:
see that module's and this package's `request_builder.py` docstrings for
the full rationale (Slides addresses objects by a stable, caller-
assignable `objectId`, not by a shifting index, so preserving caller order
is what protects a create-then-reference dependency chain).

This is the required specific test named in the spawn brief: build a
batch where request N+1 references an objectId created by request N,
assert the emitted order is unchanged, then MUTATION-TEST it -- add a
sort, confirm a test goes red for a REAL reason (not a crash), remove it.
See `TestOrderPreservationMutationGuard` below for the live mutation
record.
"""

import re
from typing import Any

from zeo_core.integrations.google.slides.request_builder import (
    SlidesRequestBuilder,
    new_object_id,
)


class TestSlidesRequestBuilderAddAndLen:
    def test_add_returns_self_for_chaining(self) -> None:
        builder = SlidesRequestBuilder()
        result = builder.add({"createSlide": {"objectId": "slide_1"}})
        assert result is builder

    def test_len_tracks_queued_requests(self) -> None:
        builder = SlidesRequestBuilder()
        assert len(builder) == 0
        builder.add({"createSlide": {"objectId": "slide_1"}})
        assert len(builder) == 1
        builder.add({"deleteObject": {"objectId": "slide_1"}})
        assert len(builder) == 2

    def test_from_requests_preloads_in_order(self) -> None:
        requests: list[dict[str, Any]] = [
            {"createSlide": {"objectId": "slide_1"}},
            {"createSlide": {"objectId": "slide_2"}},
        ]
        builder = SlidesRequestBuilder.from_requests(requests)
        assert len(builder) == 2


class TestSlidesRequestBuilderPreservesCallerOrder:
    """The core policy this class exists to enforce: build() returns
    requests in EXACTLY the order they were added -- no reordering by any
    key, unlike DocsRequestBuilder's reverse-sort-by-index."""

    def test_build_preserves_add_order_for_arbitrary_requests(self) -> None:
        # Requests deliberately NOT sorted by any obvious key (not
        # alphabetical by request kind, not by any numeric field) to prove
        # build() is not silently reordering by some other criterion.
        requests: list[dict[str, Any]] = [
            {"deleteObject": {"objectId": "z_last"}},
            {"createSlide": {"objectId": "a_first"}},
            {"insertText": {"objectId": "m_middle", "text": "hi"}},
        ]
        ordered = SlidesRequestBuilder.from_requests(requests).build()
        assert ordered == requests

    def test_build_on_empty_builder_returns_empty_list(self) -> None:
        assert SlidesRequestBuilder().build() == []

    def test_build_returns_a_new_list_not_the_internal_reference(self) -> None:
        builder = SlidesRequestBuilder()
        builder.add({"createSlide": {"objectId": "slide_1"}})
        built = builder.build()
        built.append({"createSlide": {"objectId": "injected"}})
        # Mutating the returned list must not affect the builder's own
        # internal state -- build() must return a copy.
        assert len(builder) == 1

    def test_create_then_reference_chain_order_is_unchanged(self) -> None:
        """THE required specific test: a batch where request N+1
        references an objectId created by request N. Assert the emitted
        order is unchanged -- i.e. the create request still comes before
        the request that references its objectId."""
        slide_id = "slide_1"
        shape_id = "shape_1"
        requests: list[dict[str, Any]] = [
            {"createSlide": {"objectId": slide_id}},
            {
                "createShape": {
                    "objectId": shape_id,
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {"pageObjectId": slide_id},
                }
            },
            {
                "insertText": {
                    "objectId": shape_id,
                    "text": "Q3 review",
                }
            },
        ]

        ordered = SlidesRequestBuilder.from_requests(requests).build()

        assert ordered == requests
        # Explicitly re-derive the dependency-chain property from the
        # OUTPUT rather than trusting list equality alone: the create of
        # each objectId must appear at a lower index than every request
        # that references it.
        create_slide_pos = next(i for i, r in enumerate(ordered) if "createSlide" in r)
        create_shape_pos = next(i for i, r in enumerate(ordered) if "createShape" in r)
        insert_text_pos = next(i for i, r in enumerate(ordered) if "insertText" in r)
        assert create_slide_pos < create_shape_pos < insert_text_pos


class TestOrderPreservationMutationGuard:
    """Mutation-testing record for the order-preservation guard.

    LIVE MUTATION PERFORMED THIS SESSION (not merely described): the
    module's `build()` was temporarily changed from `return
    list(self._requests)` to `return sorted(self._requests, key=lambda r:
    next(iter(r)))` (sorting alphabetically by request kind, one plausible
    "helpful" reordering a future maintainer might add by analogy with
    Docs). `test_create_then_reference_chain_order_is_unchanged` above
    went RED with a real assertion failure (`assert ordered == requests`
    failed because "createShape" < "createSlide" < "insertText"
    alphabetically, producing an order where the createShape request that
    references slide_1 ran before createSlide created it) -- not a crash,
    a genuine wrong-order signal, matching the docs precedent's own bar
    for what counts as a real mutation ("wrong element at wrong position,
    not a crash"). The sort was then removed, restoring `return
    list(self._requests)`, and the same test was re-run and confirmed
    green again. Both the break and the restore were executed against the
    real module, exactly as the docs precedent (SOW-03) did for its own
    reverse-sort guard, and to the same standard: does the defect
    reappear? It did, and reverting made it disappear again.

    This test class exists so the guard has a permanent, named home in
    the suite (not just a session-transient manual edit) -- it re-asserts
    the invariant a re-introduced sort would violate, independent of the
    test above, using a distinguishable input shape.
    """

    def test_no_reordering_survives_a_kind_name_that_would_sort_earlier(self) -> None:
        # "aCreateSlide" is not a real Slides request kind, but it is a
        # legal dict key for this builder's purposes (it treats requests
        # opaquely) and deliberately sorts alphabetically BEFORE
        # "createShape"/"insertText" while being added LAST -- if any
        # alphabetical-by-key sort were reintroduced, this key would
        # jump to the front and the assertion below would fail.
        requests: list[dict[str, Any]] = [
            {"createShape": {"objectId": "shape_1"}},
            {"insertText": {"objectId": "shape_1", "text": "x"}},
            {"aCreateSlide": {"objectId": "slide_1"}},
        ]
        ordered = SlidesRequestBuilder.from_requests(requests).build()
        assert [next(iter(r)) for r in ordered] == [
            "createShape",
            "insertText",
            "aCreateSlide",
        ]


class TestNewObjectId:
    """Tests for the `objectId`-generation helper, verified against the
    Slides v1 discovery document's own live field description for
    `CreateSlideRequest.objectId` (revision 20260828): must start with an
    alphanumeric character or underscore, remaining characters
    alphanumeric/hyphen/colon/underscore, length 5-50 inclusive."""

    _VALID_OBJECT_ID = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_:-]*$")

    def test_default_prefix(self) -> None:
        object_id = new_object_id()
        assert object_id.startswith("obj_")

    def test_custom_prefix(self) -> None:
        object_id = new_object_id("slide")
        assert object_id.startswith("slide_")

    def test_generated_id_matches_slides_api_charset_and_length(self) -> None:
        object_id = new_object_id("shape")
        assert self._VALID_OBJECT_ID.match(object_id)
        assert 5 <= len(object_id) <= 50

    def test_generated_ids_are_unique(self) -> None:
        ids = {new_object_id("box") for _ in range(1000)}
        assert len(ids) == 1000
