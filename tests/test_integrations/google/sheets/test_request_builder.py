"""
Tests for SheetsRequestBuilder.

Per RULING-408 DESIGN-03: Sheets' policy is ORDER-PRESERVING, not a sort --
see request_builder.py's module docstring for why Docs' descending-index
policy does not generalize to Sheets (partitioned per-(sheetId, dimension)
shift domains; same-batch sheet references resolved by caller-supplied
explicit sheetId, not response-chaining). These tests are written to FAIL
if a future change reintroduces a sort (e.g. by GridRange.startRowIndex),
which is exactly the mutation this module's mutation-test proof exercises.
"""

from zeo_core.integrations.google.sheets.request_builder import SheetsRequestBuilder


class TestSheetsRequestBuilderBasics:
    def test_empty_builder_builds_empty_list(self) -> None:
        builder = SheetsRequestBuilder()
        assert builder.build() == []
        assert len(builder) == 0

    def test_add_returns_self_for_chaining(self) -> None:
        builder = SheetsRequestBuilder()
        result = builder.add({"addSheet": {"properties": {"sheetId": 1}}})
        assert result is builder

    def test_len_reflects_queued_count(self) -> None:
        builder = SheetsRequestBuilder()
        builder.add({"addSheet": {"properties": {"sheetId": 1}}})
        builder.add({"deleteSheet": {"sheetId": 2}})
        assert len(builder) == 2

    def test_from_requests_preloads_builder(self) -> None:
        requests = [{"addSheet": {"properties": {"sheetId": 1}}}]
        builder = SheetsRequestBuilder.from_requests(requests)
        assert len(builder) == 1
        assert builder.build() == requests


class TestSheetsRequestBuilderPreservesCallerOrder:
    """The one policy this builder enforces: caller order survives
    build(), unchanged, regardless of any GridRange/dimension index a
    request happens to carry -- deliberately the OPPOSITE of Docs'
    reverse-sort policy."""

    def test_order_preserved_for_requests_with_ascending_indices(self) -> None:
        r1 = {
            "updateCells": {
                "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1}
            }
        }
        r2 = {
            "updateCells": {
                "range": {"sheetId": 0, "startRowIndex": 5, "endRowIndex": 6}
            }
        }
        r3 = {
            "updateCells": {
                "range": {"sheetId": 0, "startRowIndex": 10, "endRowIndex": 11}
            }
        }
        builder = SheetsRequestBuilder.from_requests([r1, r2, r3])
        assert builder.build() == [r1, r2, r3]

    def test_order_preserved_for_requests_with_descending_indices(self) -> None:
        """If this builder ever sorted ascending (or descending) by a
        GridRange index, this test would catch it: the input is already in
        descending index order, so an ascending sort would reverse it and a
        descending sort would (coincidentally) leave it alone -- paired
        with the ascending-input test above, together they detect ANY
        index-based sort, not just one direction."""
        r1 = {
            "updateCells": {
                "range": {"sheetId": 0, "startRowIndex": 10, "endRowIndex": 11}
            }
        }
        r2 = {
            "updateCells": {
                "range": {"sheetId": 0, "startRowIndex": 5, "endRowIndex": 6}
            }
        }
        r3 = {
            "updateCells": {
                "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1}
            }
        }
        builder = SheetsRequestBuilder.from_requests([r1, r2, r3])
        assert builder.build() == [r1, r2, r3]

    def test_same_batch_add_sheet_then_reference_stays_in_order(self) -> None:
        """The documented real-world idiom this builder must not disturb:
        AddSheetRequest with an explicit sheetId, immediately followed in
        the same batch by a request referencing that sheetId. Any
        reordering that moved the reference before the creation would
        silently break a real caller."""
        add_sheet = {"addSheet": {"properties": {"sheetId": 99, "title": "New Sheet"}}}
        repeat_cell = {
            "repeatCell": {
                "range": {"sheetId": 99, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredValue": {"stringValue": "hi"}},
            }
        }
        builder = SheetsRequestBuilder.from_requests([add_sheet, repeat_cell])
        assert builder.build() == [add_sheet, repeat_cell]

    def test_order_preserved_for_index_free_requests(self) -> None:
        r1 = {"autoResizeDimensions": {"dimensions": {"sheetId": 0}}}
        r2 = {"sortRange": {"range": {"sheetId": 0}}}
        builder = SheetsRequestBuilder.from_requests([r1, r2])
        assert builder.build() == [r1, r2]

    def test_order_preserved_across_multiple_sheets(self) -> None:
        """Requests on different sheets have no shared shift domain at
        all -- order between them is pure caller intent, never a hazard
        this builder could 'fix' by reordering."""
        sheet_a = {
            "insertDimension": {
                "range": {"sheetId": 0, "dimension": "ROWS", "startIndex": 0}
            }
        }
        sheet_b = {
            "insertDimension": {
                "range": {"sheetId": 1, "dimension": "ROWS", "startIndex": 50}
            }
        }
        builder = SheetsRequestBuilder.from_requests([sheet_a, sheet_b])
        assert builder.build() == [sheet_a, sheet_b]


class TestSheetsRequestBuilderBuildReturnsIndependentCopy:
    def test_build_returns_a_new_list_not_the_internal_one(self) -> None:
        builder = SheetsRequestBuilder()
        builder.add({"addSheet": {"properties": {"sheetId": 1}}})
        built = builder.build()
        built.append({"deleteSheet": {"sheetId": 2}})
        # Mutating the returned list must not corrupt the builder's own
        # internal state.
        assert len(builder) == 1
        assert builder.build() == [{"addSheet": {"properties": {"sheetId": 1}}}]
