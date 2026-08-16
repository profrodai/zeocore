# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_core/test_registry.py
# === QV-LLM:END ===

"""
Tests for quack_core.core.registry — the operation registry (Operation,
OperationRegistry, get_registry/reset_registry, invoke_operation).

quackverse-coverage-90: this module carried 78% coverage (18/81 stmts missed)
before this file, indirectly exercised by other suites but with no dedicated
test file of its own. Every assertion below calls the real production classes
and functions directly (no mocks, no stand-ins) and asserts on actual return
values or actually-raised exceptions.
"""

import asyncio

import pytest
from pydantic import BaseModel, ValidationError
from quack_core.core.registry import (
    Operation,
    OperationRegistry,
    get_registry,
    invoke_operation,
    reset_registry,
)


class Req(BaseModel):
    value: int


class Resp(BaseModel):
    doubled: int


def _double(req: Req) -> dict:
    return {"doubled": req.value * 2}


async def _double_async(req: Req) -> dict:
    return {"doubled": req.value * 2}


class TestOperationPostInit:
    def test_valid_operation_constructs(self) -> None:
        op = Operation(name="op.double", callable=_double, request_model=Req)
        assert op.name == "op.double"
        assert op.tags == []

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="name is required"):
            Operation(name="", callable=_double, request_model=Req)

    def test_noncallable_raises(self) -> None:
        with pytest.raises(ValueError, match="is not callable"):
            Operation(name="op.bad", callable="not-a-function", request_model=Req)  # type: ignore[arg-type]

    def test_tags_default_factory_is_independent_per_instance(self) -> None:
        op1 = Operation(name="a", callable=_double, request_model=Req)
        op2 = Operation(name="b", callable=_double, request_model=Req)
        op1.tags.append("x")
        assert op2.tags == []


class TestOperationRegistryRegisterAndGet:
    def test_register_then_get(self) -> None:
        reg = OperationRegistry()
        reg.register("op.double", _double, Req)
        op = reg.get("op.double")
        assert op is not None
        assert op.name == "op.double"

    def test_get_missing_returns_none(self) -> None:
        reg = OperationRegistry()
        assert reg.get("nope") is None

    def test_register_duplicate_name_raises(self) -> None:
        reg = OperationRegistry()
        reg.register("op.double", _double, Req)
        with pytest.raises(ValueError, match="already registered"):
            reg.register("op.double", _double, Req)

    def test_register_with_full_metadata(self) -> None:
        reg = OperationRegistry()
        reg.register(
            "op.double",
            _double,
            Req,
            response_model=Resp,
            description="doubles a value",
            tags=["math", "demo"],
        )
        op = reg.get_or_error("op.double")
        assert op.description == "doubles a value"
        assert op.tags == ["math", "demo"]
        assert op.response_model is Resp


class TestOperationRegistryGetOrError:
    def test_get_or_error_returns_op_when_present(self) -> None:
        reg = OperationRegistry()
        reg.register("op.double", _double, Req)
        assert reg.get_or_error("op.double").name == "op.double"

    def test_get_or_error_raises_when_absent(self) -> None:
        reg = OperationRegistry()
        with pytest.raises(ValueError, match="Operation not found: nope"):
            reg.get_or_error("nope")


class TestOperationRegistryListOperations:
    def test_list_operations_no_filter(self) -> None:
        reg = OperationRegistry()
        reg.register("op.a", _double, Req, tags=["x"])
        reg.register("op.b", _double, Req, tags=["y"])
        assert sorted(reg.list_operations()) == ["op.a", "op.b"]

    def test_list_operations_filtered_by_tag(self) -> None:
        reg = OperationRegistry()
        reg.register("op.a", _double, Req, tags=["x"])
        reg.register("op.b", _double, Req, tags=["y"])
        reg.register("op.c", _double, Req, tags=["x", "y"])
        assert sorted(reg.list_operations(tags=["x"])) == ["op.a", "op.c"]

    def test_list_operations_filtered_by_tag_no_match(self) -> None:
        reg = OperationRegistry()
        reg.register("op.a", _double, Req, tags=["x"])
        assert reg.list_operations(tags=["z"]) == []

    def test_list_operations_empty_registry(self) -> None:
        reg = OperationRegistry()
        assert reg.list_operations() == []


class TestOperationRegistryHasUnregisterClear:
    def test_has_operation_true_false(self) -> None:
        reg = OperationRegistry()
        reg.register("op.a", _double, Req)
        assert reg.has_operation("op.a") is True
        assert reg.has_operation("op.b") is False

    def test_unregister_existing_returns_true_and_removes(self) -> None:
        reg = OperationRegistry()
        reg.register("op.a", _double, Req)
        assert reg.unregister("op.a") is True
        assert reg.has_operation("op.a") is False

    def test_unregister_missing_returns_false(self) -> None:
        reg = OperationRegistry()
        assert reg.unregister("nope") is False

    def test_clear_removes_all(self) -> None:
        reg = OperationRegistry()
        reg.register("op.a", _double, Req)
        reg.register("op.b", _double, Req)
        reg.clear()
        assert reg.list_operations() == []


class TestGlobalRegistrySingleton:
    def test_get_registry_returns_same_instance(self) -> None:
        reset_registry()
        try:
            r1 = get_registry()
            r2 = get_registry()
            assert r1 is r2
        finally:
            reset_registry()

    def test_reset_registry_gives_fresh_instance(self) -> None:
        reset_registry()
        try:
            r1 = get_registry()
            r1.register("op.marker", _double, Req)
            reset_registry()
            r2 = get_registry()
            assert r2.has_operation("op.marker") is False
            assert r1 is not r2
        finally:
            reset_registry()


class TestInvokeOperationSync:
    def test_sync_callable_no_response_model(self) -> None:
        op = Operation(name="op.double", callable=_double, request_model=Req)
        result = asyncio.run(invoke_operation(op, {"value": 5}))
        assert result == {"doubled": 10}

    def test_sync_callable_with_response_model_dict_result(self) -> None:
        op = Operation(
            name="op.double", callable=_double, request_model=Req, response_model=Resp
        )
        result = asyncio.run(invoke_operation(op, {"value": 5}))
        assert result == {"doubled": 10}

    def test_invalid_params_raise_validation_error(self) -> None:
        op = Operation(name="op.double", callable=_double, request_model=Req)
        with pytest.raises(ValidationError):
            asyncio.run(
                invoke_operation(op, {"value": "not-an-int-and-not-coercible"})
            )


class TestInvokeOperationAsync:
    def test_async_callable_is_awaited(self) -> None:
        op = Operation(
            name="op.double.async", callable=_double_async, request_model=Req
        )
        result = asyncio.run(invoke_operation(op, {"value": 7}))
        assert result == {"doubled": 14}


class TestInvokeOperationResultShapes:
    def test_non_dict_result_wrapped_in_value_key(self) -> None:
        def _returns_int(req: Req) -> int:
            return req.value * 3

        op = Operation(name="op.triple", callable=_returns_int, request_model=Req)
        result = asyncio.run(invoke_operation(op, {"value": 4}))
        assert result == {"value": 12}

    def test_none_result_with_response_model_skips_validation(self) -> None:
        def _returns_none(req: Req) -> None:
            return None

        op = Operation(
            name="op.none",
            callable=_returns_none,
            request_model=Req,
            response_model=Resp,
        )
        result = asyncio.run(invoke_operation(op, {"value": 1}))
        assert result == {"value": None}

    def test_non_json_serializable_result_raises_value_error(self) -> None:
        class NotSerializable:
            pass

        def _returns_object(req: Req) -> dict:
            return {"obj": NotSerializable()}

        op = Operation(name="op.bad", callable=_returns_object, request_model=Req)
        with pytest.raises(ValueError, match="non-JSON-serializable"):
            asyncio.run(invoke_operation(op, {"value": 1}))

    def test_non_dict_scalar_result_with_response_model_raises_typeerror(
        self,
    ) -> None:
        # Real behavior, not assumed: registry.py's non-dict/non-instance branch
        # calls `op.response_model(result)` POSITIONALLY (registry.py:254). A
        # pydantic BaseModel subclass takes no positional args, so a scalar
        # result with a response_model set genuinely raises TypeError here —
        # this test asserts what the code actually does, not a guessed happy path.
        def _returns_scalar(req: Req) -> int:
            return req.value

        class SingleValue(BaseModel):
            value: int

        op = Operation(
            name="op.wrap",
            callable=_returns_scalar,
            request_model=Req,
            response_model=SingleValue,
        )
        with pytest.raises(TypeError):
            asyncio.run(invoke_operation(op, {"value": 9}))

    def test_non_dict_result_already_instance_of_response_model_passthrough(
        self,
    ) -> None:
        # The `else result` branch of the ternary at registry.py:253-257: when
        # the callable's result IS already an instance of response_model, it is
        # used as-is (no re-construction) and then .model_dump()'d.
        class SingleValue(BaseModel):
            value: int

        def _returns_model_instance(req: Req) -> SingleValue:
            return SingleValue(value=req.value)

        op = Operation(
            name="op.passthrough",
            callable=_returns_model_instance,
            request_model=Req,
            response_model=SingleValue,
        )
        result = asyncio.run(invoke_operation(op, {"value": 9}))
        assert result == {"value": 9}
