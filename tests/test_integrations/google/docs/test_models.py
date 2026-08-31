"""Tests for Google Docs data models (`Color`, the one leaf type modeled
per RULING-408 DESIGN-02)."""

from typing import cast

import pytest
from pydantic import ValidationError

from zeo_core.integrations.google.docs.models import Color


class TestColorConstruction:
    def test_defaults_to_black_opaque(self) -> None:
        color = Color()
        assert color.red == 0.0
        assert color.green == 0.0
        assert color.blue == 0.0
        assert color.alpha is None

    def test_explicit_fields(self) -> None:
        color = Color(red=0.5, green=0.25, blue=1.0, alpha=0.8)
        assert color.red == 0.5
        assert color.green == 0.25
        assert color.blue == 1.0
        assert color.alpha == 0.8

    @pytest.mark.parametrize("field", ["red", "green", "blue", "alpha"])
    def test_out_of_range_rejected(self, field: str) -> None:
        with pytest.raises(ValidationError):
            Color(**{field: 1.5})
        with pytest.raises(ValidationError):
            Color(**{field: -0.1})


class TestColorApiRoundTrip:
    def test_to_api_dict_without_alpha(self) -> None:
        color = Color(red=1.0, green=0.5, blue=0.0)
        api_dict = color.to_api_dict()
        assert api_dict == {
            "color": {"rgbColor": {"red": 1.0, "green": 0.5, "blue": 0.0}}
        }

    def test_to_api_dict_with_alpha(self) -> None:
        color = Color(red=1.0, green=0.5, blue=0.0, alpha=0.5)
        api_dict = color.to_api_dict()
        # to_api_dict() returns dict[str, object] (the public-API-boundary
        # hybrid rule, RULING-406 decision 1) -- api_dict["color"] is
        # typed `object`, not indexable, without narrowing it back to
        # dict[str, object] first.
        inner = cast(dict[str, object], api_dict["color"])
        assert inner["rgbColor"] == {"red": 1.0, "green": 0.5, "blue": 0.0}
        assert inner["alpha"] == 0.5

    def test_from_api_dict_wrapped_shape(self) -> None:
        data: dict[str, object] = {
            "color": {
                "rgbColor": {"red": 0.2, "green": 0.4, "blue": 0.6},
                "alpha": 0.9,
            }
        }
        color = Color.from_api_dict(data)
        assert color.red == 0.2
        assert color.green == 0.4
        assert color.blue == 0.6
        assert color.alpha == 0.9

    def test_from_api_dict_unwrapped_shape(self) -> None:
        data: dict[str, object] = {"rgbColor": {"red": 0.1, "green": 0.2, "blue": 0.3}}
        color = Color.from_api_dict(data)
        assert color.red == 0.1
        assert color.green == 0.2
        assert color.blue == 0.3
        assert color.alpha is None

    def test_from_api_dict_missing_rgb_defaults_to_zero(self) -> None:
        color = Color.from_api_dict({})
        assert color.red == 0.0
        assert color.green == 0.0
        assert color.blue == 0.0
        assert color.alpha is None

    def test_round_trip_to_api_dict_and_back(self) -> None:
        original = Color(red=0.33, green=0.66, blue=0.99, alpha=0.5)
        restored = Color.from_api_dict(original.to_api_dict())
        assert restored == original
