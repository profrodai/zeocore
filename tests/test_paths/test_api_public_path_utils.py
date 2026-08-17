"""
Tests for zeo_core.core.paths.api.public.path_utils (0% covered before
this file). Pure functions, no external boundary, no mocking needed.
"""

from pathlib import Path

from zeo_core.core.fs import DataResult, PathResult
from zeo_core.core.paths.api.public.path_utils import (
    ensure_clean_path,
    extract_path_from_path_result_string,
    is_likely_drive_id,
)


class TestEnsureCleanPath:
    def test_plain_string(self) -> None:
        assert ensure_clean_path("some/path.txt") == "some/path.txt"

    def test_plain_path_object(self) -> None:
        assert ensure_clean_path(Path("some/path.txt")) == "some/path.txt"

    def test_path_result_with_path_attr(self) -> None:
        result = PathResult(ok=True, path=Path("/resolved/path.txt"))
        assert ensure_clean_path(result) == "/resolved/path.txt"

    def test_data_result_with_data_attr(self) -> None:
        result: DataResult[str] = DataResult(ok=True, data="/data/path.txt")
        assert ensure_clean_path(result) == "/data/path.txt"

    def test_path_result_with_none_path_falls_through_to_str(self) -> None:
        # path is None -> the `path_or_result.path is not None` guard fails,
        # falls through to the data check, then the bare str() branch.
        result = PathResult(ok=False, path=None)
        # No `.data` attribute on PathResult, so this hits the final
        # `str(path_or_result)` branch -- exercising it, not asserting a
        # specific repr format (that's pydantic's business, not this
        # function's contract).
        assert isinstance(ensure_clean_path(result), str)

    def test_data_result_with_none_data_falls_through_to_str(self) -> None:
        result: DataResult[str | None] = DataResult(ok=False, data=None)
        assert isinstance(ensure_clean_path(result), str)


class TestIsLikelyDriveId:
    def test_typical_drive_id_length_returns_true(self) -> None:
        # 33 chars, no separators or dots -- squarely in the 25-45 range.
        candidate = "1a2B3c4D5e6F7g8H9i0J1k2L3m4N5o6"
        assert len(candidate) == 31
        assert is_likely_drive_id(candidate) is True

    def test_too_short_returns_false(self) -> None:
        assert is_likely_drive_id("short_id") is False

    def test_too_long_returns_false(self) -> None:
        assert is_likely_drive_id("a" * 46) is False

    def test_exactly_25_chars_is_boundary_true(self) -> None:
        assert is_likely_drive_id("a" * 25) is True

    def test_exactly_45_chars_is_boundary_true(self) -> None:
        assert is_likely_drive_id("a" * 45) is True

    def test_24_chars_is_just_below_boundary_false(self) -> None:
        assert is_likely_drive_id("a" * 24) is False

    def test_46_chars_is_just_above_boundary_false(self) -> None:
        assert is_likely_drive_id("a" * 46) is False

    def test_contains_forward_slash_returns_false(self) -> None:
        assert is_likely_drive_id("a" * 20 + "/" + "a" * 10) is False

    def test_contains_backslash_returns_false(self) -> None:
        assert is_likely_drive_id("a" * 20 + "\\" + "a" * 10) is False

    def test_contains_dot_returns_false(self) -> None:
        assert is_likely_drive_id("a" * 20 + "." + "a" * 10) is False

    def test_non_string_input_returns_false(self) -> None:
        assert is_likely_drive_id(12345) is False  # type: ignore[arg-type]
        assert is_likely_drive_id(None) is False  # type: ignore[arg-type]


class TestExtractPathFromPathResultString:
    def test_extracts_path_from_success_prefixed_string(self) -> None:
        raw = "success=True path=PosixPath('/some/real/path.txt') message=None"
        assert extract_path_from_path_result_string(raw) == "/some/real/path.txt"

    def test_success_prefixed_string_without_path_pattern_returns_original(
        self,
    ) -> None:
        raw = "success=True message='no path field here'"
        assert extract_path_from_path_result_string(raw) == raw

    def test_non_success_prefixed_string_returned_unchanged(self) -> None:
        raw = "/plain/ordinary/path.txt"
        assert extract_path_from_path_result_string(raw) == raw

    def test_empty_string_returned_unchanged(self) -> None:
        assert extract_path_from_path_result_string("") == ""
