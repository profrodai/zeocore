"""
Policy-enforcing request builder for Google Sheets `batchUpdate`.

Per RULING-408 DESIGN-03: one request builder per API, NOT shared with
`docs/request_builder.py` or a future `slides/request_builder.py` -- and the
sort policy is derived from THIS API's own semantics, not copied from Docs.

WHY SHEETS DOES NOT GET DOCS' "DESCENDING INDEX" POLICY
---------------------------------------------------------
Docs' hazard is a SINGLE, GLOBAL, LINEAR offset: the whole document body is
one sequence of UTF-16 code units, so any edit anywhere shifts every index
after it, and "highest index first" is a total order that always avoids the
hazard.

Sheets has no such single axis. Two things make a naive "sort by some
index" policy actively wrong here rather than merely unnecessary:

1. **Index-shifting requests are index-shifting only within a PARTITION,
   not globally.** `InsertDimensionRequest`/`DeleteDimensionRequest` operate
   on a `DimensionRange` scoped to one `(sheetId, dimension)` pair -- a row
   insert on sheet A does not shift row indices on sheet B, and a row
   insert never shifts column indices at all (rows and columns are
   independent axes). A `GridRange`-anchored request on a DIFFERENT sheet,
   or on the same sheet's other dimension, is never affected by that
   insert/delete no matter what order it runs in. Most of the 69 request
   kinds (`RepeatCellRequest`, `UpdateCellsRequest`, `MergeCellsRequest`,
   `SortRangeRequest`, formatting requests, etc.) do not shift anything at
   all -- they read/write a `GridRange` without moving row/column
   boundaries. Sorting the WHOLE batch by e.g. `range.startRowIndex` would
   silently reorder requests that have no ordering hazard between them at
   all, based on a number that means something different on every sheet.

2. **Same-batch sheet creation is resolved by CALLER-SUPPLIED id, not
   response-chaining.** `AddSheetRequest` returns its assigned `sheetId` in
   `BatchUpdateSpreadsheetResponse.replies`, but that reply only reaches the
   caller after the ENTIRE batch completes -- a later request in the SAME
   batch cannot read an earlier request's reply to discover a server-
   assigned id. The documented, working pattern (matching real-world Sheets
   API usage) is for the caller to set `AddSheetRequest.properties.sheetId`
   explicitly to a caller-chosen value, so a later request in the same
   batch can reference that known id directly. This builder does not (and
   structurally cannot) invent or reassign a `sheetId` on the caller's
   behalf -- it is not this class's job to guess intent about which
   `AddSheetRequest` a later `RepeatCellRequest.range.sheetId` is "supposed"
   to refer to.

**Policy adopted: PRESERVE CALLER ORDER.** With no single global ordering
key that is safe to impose (point 1) and no way to safely infer or repair a
missing explicit `sheetId` (point 2), the one thing this builder can do
without silently corrupting a caller's intent is leave `requests` in the
order given -- the same policy DESIGN-03 approach B chose for Slides (where
same-batch `objectId` references make caller order load-bearing), adopted
here for a different, Sheets-specific reason: caller order is the only
ordering information this class actually has that is safe to act on, since
the shift domains are unknowable without simulating full spreadsheet state
across every sheet -- work this curated builder deliberately does not take
on (see DESIGN-03's own "NOT DECIDING HERE" on an op-list compiler, approach
C, rejected as scope creep past the curated surface RULING-406 bounded).

This is a genuine judgment call, not a default: `spreadsheets.batchUpdate`
IS documented to apply requests in the order supplied, exactly like Docs, so
"preserve order" is not merely "do nothing" -- it is the only choice that
respects a caller who deliberately sequences e.g. "insert 3 rows, then
populate them" or "add a sheet with an explicit id, then format it".
"""

from typing import Any


class SheetsRequestBuilder:
    """Order-preserving builder for a Google Sheets `batchUpdate` request
    list.

    Callers add `Request` dicts (each shaped exactly like the real Sheets
    API `Request` union member, e.g. `{"addSheet": {...}}`,
    `{"updateCells": {...}}`) via `add()`, or construct the builder directly
    from an existing list via `from_requests()`. `build()` returns the
    requests in EXACTLY the order they were added -- see this module's
    docstring for why that, not a sort, is the correct policy for Sheets.
    """

    def __init__(self) -> None:
        """Initialize an empty request builder."""
        self._requests: list[dict[str, Any]] = []

    @classmethod
    def from_requests(cls, requests: list[dict[str, Any]]) -> "SheetsRequestBuilder":
        """
        Construct a builder pre-loaded with an existing list of requests.

        Args:
            requests: Sheets API `Request` dicts, in the caller's intended
                execution order.

        Returns:
            A new `SheetsRequestBuilder` containing `requests`.
        """
        builder = cls()
        builder._requests.extend(requests)
        return builder

    def add(self, request: dict[str, Any]) -> "SheetsRequestBuilder":
        """
        Add a single Sheets API `Request` dict to the builder.

        Args:
            request: A Sheets API `Request` dict, e.g.
                `{"addSheet": {"properties": {"sheetId": 1, "title": "x"}}}`.

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
        Return the queued requests in the exact order they were added.

        A new list is returned (not the internal list itself) so a caller
        mutating the returned list can never corrupt this builder's own
        state -- matching `DocsRequestBuilder.build()`'s return-a-copy
        shape, even though the transformation here is identity rather than
        a sort.

        Returns:
            The requests, in caller-supplied order.
        """
        return list(self._requests)
