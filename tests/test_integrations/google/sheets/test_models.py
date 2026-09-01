"""
Tests for the four leaf models in sheets/models.py (Color, GridRange,
TextFormat, NumberFormat), per RULING-408 DESIGN-02 approach B. Mirrors
tests/test_integrations/google/docs/test_models.py's round-trip pattern:
construct -> to_api_dict() -> from_api_dict() -> equals the original.
"""

from zeo_core.integrations.google.sheets.models import (
    Color,
    GridRange,
    NumberFormat,
    TextFormat,
)


class TestColor:
    def test_defaults(self) -> None:
        color = Color()
        assert color.red == 0.0
        assert color.green == 0.0
        assert color.blue == 0.0
        assert color.alpha is None

    def test_to_api_dict_omits_alpha_when_unset(self) -> None:
        color = Color(red=1.0, green=0.5, blue=0.0)
        assert color.to_api_dict() == {"red": 1.0, "green": 0.5, "blue": 0.0}

    def test_to_api_dict_includes_alpha_when_set(self) -> None:
        color = Color(red=1.0, green=0.5, blue=0.0, alpha=0.5)
        assert color.to_api_dict() == {
            "red": 1.0,
            "green": 0.5,
            "blue": 0.0,
            "alpha": 0.5,
        }

    def test_wire_shape_is_flat_not_wrapped(self) -> None:
        """Sheets' Color, unlike Docs' OptionalColor, is a flat dict with
        no {"color": {"rgbColor": ...}} nesting."""
        color = Color(red=0.2, green=0.4, blue=0.6)
        wire = color.to_api_dict()
        assert "color" not in wire
        assert "rgbColor" not in wire
        assert wire["red"] == 0.2

    def test_from_api_dict_round_trip(self) -> None:
        original = Color(red=0.1, green=0.2, blue=0.3, alpha=0.9)
        restored = Color.from_api_dict(original.to_api_dict())
        assert restored == original

    def test_from_api_dict_round_trip_no_alpha(self) -> None:
        original = Color(red=0.1, green=0.2, blue=0.3)
        restored = Color.from_api_dict(original.to_api_dict())
        assert restored == original

    def test_from_api_dict_defaults_on_missing_keys(self) -> None:
        color = Color.from_api_dict({})
        assert color == Color(red=0.0, green=0.0, blue=0.0, alpha=None)

    def test_from_api_dict_ignores_non_numeric_junk(self) -> None:
        color = Color.from_api_dict(
            {"red": "not-a-number", "green": 0.5, "blue": None, "alpha": []}
        )
        assert color.red == 0.0
        assert color.green == 0.5
        assert color.blue == 0.0
        assert color.alpha is None

    def test_bounds_validated(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Color(red=1.5, green=0.0, blue=0.0)


class TestGridRange:
    def test_requires_sheet_id(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            GridRange()  # type: ignore[call-arg]

    def test_to_api_dict_sheet_id_only(self) -> None:
        grid_range = GridRange(sheet_id=0)
        assert grid_range.to_api_dict() == {"sheetId": 0}

    def test_to_api_dict_full_bounds(self) -> None:
        grid_range = GridRange(
            sheet_id=42,
            start_row_index=1,
            end_row_index=10,
            start_column_index=0,
            end_column_index=5,
        )
        assert grid_range.to_api_dict() == {
            "sheetId": 42,
            "startRowIndex": 1,
            "endRowIndex": 10,
            "startColumnIndex": 0,
            "endColumnIndex": 5,
        }

    def test_to_api_dict_omits_unset_bounds_rather_than_pinning_zero(self) -> None:
        """A caller who wants 'entire column A on sheet 0' passes only
        start_column_index=0, end_column_index=1, leaving rows unbounded --
        the omitted row keys must NOT appear as an implicit 0."""
        grid_range = GridRange(sheet_id=0, start_column_index=0, end_column_index=1)
        wire = grid_range.to_api_dict()
        assert "startRowIndex" not in wire
        assert "endRowIndex" not in wire
        assert wire["startColumnIndex"] == 0
        assert wire["endColumnIndex"] == 1

    def test_from_api_dict_round_trip(self) -> None:
        original = GridRange(
            sheet_id=7,
            start_row_index=0,
            end_row_index=100,
            start_column_index=0,
            end_column_index=26,
        )
        restored = GridRange.from_api_dict(original.to_api_dict())
        assert restored == original

    def test_from_api_dict_round_trip_sheet_id_only(self) -> None:
        original = GridRange(sheet_id=3)
        restored = GridRange.from_api_dict(original.to_api_dict())
        assert restored == original

    def test_from_api_dict_defaults_on_missing_keys(self) -> None:
        grid_range = GridRange.from_api_dict({})
        assert grid_range == GridRange(sheet_id=0)

    def test_from_api_dict_ignores_non_int_junk(self) -> None:
        grid_range = GridRange.from_api_dict(
            {
                "sheetId": "not-an-int",
                "startRowIndex": "also-not-an-int",
                "endRowIndex": 5,
            }
        )
        assert grid_range.sheet_id == 0
        assert grid_range.start_row_index is None
        assert grid_range.end_row_index == 5


class TestNumberFormat:
    def test_requires_type(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            NumberFormat()  # type: ignore[call-arg]

    def test_to_api_dict_type_only(self) -> None:
        fmt = NumberFormat(type="PERCENT")
        assert fmt.to_api_dict() == {"type": "PERCENT"}

    def test_to_api_dict_with_pattern(self) -> None:
        fmt = NumberFormat(type="CURRENCY", pattern="$#,##0.00")
        assert fmt.to_api_dict() == {"type": "CURRENCY", "pattern": "$#,##0.00"}

    def test_from_api_dict_round_trip(self) -> None:
        original = NumberFormat(type="DATE", pattern="yyyy-mm-dd")
        restored = NumberFormat.from_api_dict(original.to_api_dict())
        assert restored == original

    def test_from_api_dict_defaults_on_missing_keys(self) -> None:
        fmt = NumberFormat.from_api_dict({})
        assert fmt.type == ""
        assert fmt.pattern is None

    def test_from_api_dict_ignores_non_str_junk(self) -> None:
        fmt = NumberFormat.from_api_dict({"type": 123, "pattern": []})
        assert fmt.type == ""
        assert fmt.pattern is None


class TestTextFormat:
    def test_all_fields_optional(self) -> None:
        fmt = TextFormat()
        assert fmt.to_api_dict() == {}

    def test_to_api_dict_full(self) -> None:
        fmt = TextFormat(
            foreground_color=Color(red=1.0, green=0.0, blue=0.0),
            font_family="Arial",
            font_size=12,
            bold=True,
            italic=False,
            strikethrough=False,
            underline=True,
            link_uri="https://example.com",
            foreground_color_style=Color(red=0.0, green=1.0, blue=0.0),
        )
        wire = fmt.to_api_dict()
        assert wire["foregroundColor"] == {"red": 1.0, "green": 0.0, "blue": 0.0}
        assert wire["fontFamily"] == "Arial"
        assert wire["fontSize"] == 12
        assert wire["bold"] is True
        assert wire["italic"] is False
        assert wire["strikethrough"] is False
        assert wire["underline"] is True
        assert wire["link"] == {"uri": "https://example.com"}
        assert wire["foregroundColorStyle"] == {
            "rgbColor": {"red": 0.0, "green": 1.0, "blue": 0.0}
        }

    def test_to_api_dict_omits_unset_fields(self) -> None:
        fmt = TextFormat(bold=True)
        assert fmt.to_api_dict() == {"bold": True}

    def test_from_api_dict_round_trip_full(self) -> None:
        original = TextFormat(
            foreground_color=Color(red=1.0, green=0.0, blue=0.0),
            font_family="Arial",
            font_size=12,
            bold=True,
            italic=False,
            strikethrough=False,
            underline=True,
            link_uri="https://example.com",
            foreground_color_style=Color(red=0.0, green=1.0, blue=0.0),
        )
        restored = TextFormat.from_api_dict(original.to_api_dict())
        assert restored == original

    def test_from_api_dict_round_trip_empty(self) -> None:
        original = TextFormat()
        restored = TextFormat.from_api_dict(original.to_api_dict())
        assert restored == original

    def test_from_api_dict_defaults_on_missing_keys(self) -> None:
        fmt = TextFormat.from_api_dict({})
        assert fmt == TextFormat()

    def test_from_api_dict_ignores_non_matching_types(self) -> None:
        fmt = TextFormat.from_api_dict(
            {
                "fontFamily": 123,
                "fontSize": "not-an-int",
                "bold": "not-a-bool",
                "link": "not-a-dict",
                "foregroundColorStyle": "not-a-dict",
            }
        )
        assert fmt.font_family is None
        assert fmt.font_size is None
        assert fmt.bold is None
        assert fmt.link_uri is None
        assert fmt.foreground_color_style is None
