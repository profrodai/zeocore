"""
Tests for quack_core.core.serialization — shared JSON serialization utilities.

quackverse-coverage-90: this module carried 22% coverage (51/65 stmts missed)
before this file. Every assertion below calls the real production functions
directly (no mocks, no stand-ins) and asserts on actual return values or
actually-raised exceptions.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

import pytest
from pydantic import BaseModel
from quack_core.core.serialization import is_json_safe, normalize_for_json


class Color(Enum):
    RED = "red"
    BLUE = "blue"


@dataclass
class Point:
    x: int
    y: int


class Widget(BaseModel):
    name: str
    count: int


class Unserializable:
    """A plain object with no special handling — should be rejected/stringified."""

    def __str__(self) -> str:
        return "unserializable-repr"


class BrokenStr:
    """An object whose __str__ itself raises — exercises the ValueError wrap path."""

    def __str__(self) -> str:
        raise RuntimeError("cannot stringify")


class TestNormalizeForJsonPrimitives:
    def test_string_passthrough(self) -> None:
        assert normalize_for_json("hello") == "hello"

    def test_int_passthrough(self) -> None:
        assert normalize_for_json(42) == 42

    def test_float_passthrough(self) -> None:
        assert normalize_for_json(3.14) == 3.14

    def test_bool_passthrough(self) -> None:
        assert normalize_for_json(True) is True

    def test_none_passthrough(self) -> None:
        assert normalize_for_json(None) is None


class TestNormalizeForJsonScalarConversions:
    def test_path_converts_to_str(self) -> None:
        # No filesystem access happens here — Path is never opened, only
        # stringified. A non-/tmp literal sidesteps the linter's (correctly
        # cautious, but inapplicable here) insecure-tempfile heuristic.
        p = Path("some/relative/dir/x")
        assert normalize_for_json(p) == str(p)

    def test_datetime_converts_to_isoformat(self) -> None:
        d = datetime(2025, 1, 1, 12, 30)
        assert normalize_for_json(d) == d.isoformat()

    def test_enum_converts_to_value(self) -> None:
        assert normalize_for_json(Color.RED) == "red"


class TestNormalizeForJsonPydantic:
    def test_pydantic_model_dumps_when_allowed(self) -> None:
        w = Widget(name="thing", count=3)
        result = normalize_for_json(w, allow_pydantic=True)
        assert result == {"name": "thing", "count": 3}

    def test_pydantic_model_rejected_when_disallowed(self) -> None:
        # allow_pydantic=False means BaseModel falls through to unknown-type
        # handling, which raises TypeError by default (allow_string_fallback=False).
        w = Widget(name="thing", count=3)
        with pytest.raises(TypeError):
            normalize_for_json(w, allow_pydantic=False)


class TestNormalizeForJsonDataclass:
    def test_dataclass_converts_via_asdict(self) -> None:
        p = Point(x=1, y=2)
        assert normalize_for_json(p) == {"x": 1, "y": 2}

    def test_dataclass_type_does_not_raise_typeerror_from_asdict(self) -> None:
        # is_dataclass() is True for both an instance AND a bare dataclass
        # *type* (Point, not Point(...)) -- asdict() only accepts instances
        # and raises TypeError on a type. A bare type must fall through to
        # the same unknown-type handling any other unsupported value gets,
        # not raise TypeError out of the dataclass branch (RULING-277 Bug 3).
        with pytest.raises(TypeError, match="not JSON-serializable"):
            normalize_for_json(Point)

    def test_dataclass_type_stringified_with_fallback(self) -> None:
        result = normalize_for_json(Point, allow_string_fallback=True)
        assert result == str(Point)


class TestNormalizeForJsonSequences:
    def test_list_recurses_over_elements(self) -> None:
        result = normalize_for_json([Path("/a"), 1, "b"])
        assert result == [str(Path("/a")), 1, "b"]

    def test_tuple_recurses_and_becomes_list(self) -> None:
        result = normalize_for_json((1, 2, 3))
        assert result == [1, 2, 3]

    def test_set_recurses_and_becomes_list(self) -> None:
        result = normalize_for_json({1, 2, 3})
        assert isinstance(result, list)
        assert sorted(result) == [1, 2, 3]

    def test_set_conversion_logs_debug_with_logger(self) -> None:
        logger = logging.getLogger("test-serialization-set")
        records: list[str] = []
        logger.addHandler(
            type(
                "H",
                (logging.Handler,),
                {"emit": lambda self, record: records.append(record.getMessage())},
            )()
        )
        logger.setLevel(logging.DEBUG)
        normalize_for_json({1, 2}, path="myset", logger=logger)
        assert any("Converting set to list at myset" in r for r in records)

    def test_nested_list_of_dataclasses(self) -> None:
        result = normalize_for_json([Point(1, 2), Point(3, 4)])
        assert result == [{"x": 1, "y": 2}, {"x": 3, "y": 4}]


class TestNormalizeForJsonDicts:
    def test_dict_with_string_keys_recurses_values(self) -> None:
        result = normalize_for_json({"a": Path("/x"), "b": 2})
        assert result == {"a": str(Path("/x")), "b": 2}

    def test_dict_with_nonstring_key_rejected_by_default(self) -> None:
        with pytest.raises(TypeError, match="must be string"):
            normalize_for_json({1: "a"})

    def test_dict_with_nonstring_key_coerced_with_fallback(self) -> None:
        result = normalize_for_json({1: "a"}, allow_string_fallback=True)
        assert result == {"1": "a"}

    def test_dict_key_coercion_logs_warning_with_logger(self) -> None:
        logger = logging.getLogger("test-serialization-key")
        records: list[str] = []
        logger.addHandler(
            type(
                "H",
                (logging.Handler,),
                {"emit": lambda self, record: records.append(record.getMessage())},
            )()
        )
        logger.setLevel(logging.WARNING)
        normalize_for_json({1: "a"}, allow_string_fallback=True, logger=logger)
        assert any("is not a string" in r for r in records)

    def test_nested_dict_path_propagates(self) -> None:
        # path is used in error messages; assert it reaches the nested raise site.
        with pytest.raises(TypeError, match=r"outer\.inner"):
            normalize_for_json({"inner": {1: "x"}}, path="outer")


class TestNormalizeForJsonUnknownTypes:
    def test_unknown_type_raises_typeerror_by_default(self) -> None:
        with pytest.raises(TypeError, match="not JSON-serializable"):
            normalize_for_json(Unserializable())

    def test_unknown_type_message_mentions_pydantic_when_allowed(self) -> None:
        with pytest.raises(TypeError, match="Pydantic BaseModel"):
            normalize_for_json(Unserializable(), allow_pydantic=True)

    def test_unknown_type_stringified_with_fallback(self) -> None:
        result = normalize_for_json(Unserializable(), allow_string_fallback=True)
        assert result == "unserializable-repr"

    def test_unknown_type_fallback_logs_warning(self) -> None:
        logger = logging.getLogger("test-serialization-unknown")
        records: list[str] = []
        logger.addHandler(
            type(
                "H",
                (logging.Handler,),
                {"emit": lambda self, record: records.append(record.getMessage())},
            )()
        )
        logger.setLevel(logging.WARNING)
        normalize_for_json(Unserializable(), allow_string_fallback=True, logger=logger)
        assert any("may lose structure" in r for r in records)

    def test_unknown_type_stringify_failure_wrapped_in_valueerror(self) -> None:
        with pytest.raises(ValueError, match="Cannot serialize value"):
            normalize_for_json(BrokenStr(), allow_string_fallback=True)


class TestIsJsonSafe:
    def test_true_for_plain_dict(self) -> None:
        assert is_json_safe({"name": "test", "count": 42}) is True

    def test_true_for_path_auto_converted(self) -> None:
        assert is_json_safe({"path": Path("some/relative/dir")}) is True

    def test_false_for_unserializable_object(self) -> None:
        assert is_json_safe({"obj": Unserializable()}) is False

    def test_false_respects_allow_pydantic_false(self) -> None:
        w = Widget(name="a", count=1)
        assert is_json_safe(w, allow_pydantic=False) is False

    def test_true_respects_allow_pydantic_true(self) -> None:
        w = Widget(name="a", count=1)
        assert is_json_safe(w, allow_pydantic=True) is True

    def test_does_not_mutate_input(self) -> None:
        original = {"a": 1, "b": [1, 2, 3]}
        snapshot = dict(original)
        is_json_safe(original)
        assert original == snapshot
