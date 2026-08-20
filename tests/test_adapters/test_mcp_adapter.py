"""
Test suite for the MCP adapter.

Mirrors test_http_adapter.py's own shape (a single consolidated test file,
test-only request/response models, a fresh OperationRegistry per test) --
MCP-shaped instead of REST-shaped, and additionally covering the
register_tool mechanical-derivation path that has no HTTP-adapter analog.
"""

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from zeo_core.adapters.mcp import create_server, register_tool
from zeo_core.adapters.mcp.tool_adapter import ToolAdapterError, build_tool_context
from zeo_core.contracts import CapabilityResult
from zeo_core.core.registry import OperationRegistry, get_registry, reset_registry
from zeo_core.tools import BaseZeoTool, ToolContext


class EchoRequest(BaseModel):
    """Test request model."""

    text: str


def echo_operation(req: EchoRequest) -> dict[str, Any]:
    """Test operation, registered directly (not via a tool)."""
    return {"echoed": f"Echo: {req.text}"}


class WordCountRequest(BaseModel):
    """Request model for the test tool below."""

    text: str
    upper: bool = False


class WordCountResponse(BaseModel):
    """Response payload for the test tool below."""

    word_count: int
    text_out: str


class WordCountTestTool(BaseZeoTool):
    """
    A real, minimal BaseZeoTool -- the same shape as
    examples/minimal_tool.py's WordCountTool -- used to prove register_tool
    needs zero tool-author changes to become MCP-reachable.
    """

    name = "word_count_test"
    version = "1.0.0"

    def run(
        self, request: WordCountRequest, ctx: ToolContext
    ) -> CapabilityResult[WordCountResponse]:
        text_out = request.text.upper() if request.upper else request.text
        return CapabilityResult.ok(
            data=WordCountResponse(
                word_count=len(request.text.split()), text_out=text_out
            ),
            msg="counted",
        )


class UntypedRequestTool(BaseZeoTool):
    """A tool whose run() has NO annotation at all on 'request' (as opposed
    to an explicit non-BaseModel annotation like `Any` or `dict`) -- should
    be rejected by register_tool with a clear, actionable error naming the
    missing hint specifically."""

    name = "untyped_tool"

    def run(self, request, ctx: ToolContext) -> CapabilityResult[None]:  # type: ignore[no-untyped-def]  # noqa: ANN001 -- deliberately unannotated, this IS the defect register_tool must reject
        return CapabilityResult.ok(data=None)


class NonModelRequestTool(BaseZeoTool):
    """A tool whose run() type-hints 'request' as something that is not a
    pydantic BaseModel -- should also be rejected."""

    name = "non_model_tool"

    def run(self, request: dict, ctx: ToolContext) -> CapabilityResult[None]:
        return CapabilityResult.ok(data=None)


@pytest.fixture
def registry() -> Generator[OperationRegistry]:
    """Provide a clean, isolated registry for each test."""
    reset_registry()
    reg = OperationRegistry()
    yield reg
    reset_registry()


class TestRegisterTool:
    """register_tool: the 'zeotools are MCP-native by default' mechanism."""

    def test_registers_tool_by_its_own_name(self, registry: OperationRegistry) -> None:
        op_name = register_tool(WordCountTestTool(), registry=registry)
        assert op_name == "word_count_test"
        assert registry.has_operation("word_count_test")

    def test_derives_request_model_from_run_type_hint(
        self, registry: OperationRegistry
    ) -> None:
        register_tool(WordCountTestTool(), registry=registry)
        op = registry.get_or_error("word_count_test")
        assert op.request_model is WordCountRequest

    def test_description_defaults_to_class_docstring_first_line(
        self, registry: OperationRegistry
    ) -> None:
        register_tool(WordCountTestTool(), registry=registry)
        op = registry.get_or_error("word_count_test")
        assert op.description == ("A real, minimal BaseZeoTool -- the same shape as")

    def test_description_is_honestly_empty_when_tool_has_no_own_docstring(
        self, registry: OperationRegistry
    ) -> None:
        """
        A tool with no docstring of its own must get an empty description,
        NOT silently inherit BaseZeoTool's own class docstring via MRO
        walk-up -- that would mislabel the tool with unrelated framework
        boilerplate to whatever agent reads it over MCP.
        """

        class UndocumentedTool(BaseZeoTool):
            name = "undocumented_tool"

            def run(
                self, request: WordCountRequest, ctx: ToolContext
            ) -> CapabilityResult[None]:
                return CapabilityResult.ok(data=None)

        register_tool(UndocumentedTool(), registry=registry)
        op = registry.get_or_error("undocumented_tool")
        assert op.description == ""

    def test_explicit_name_and_description_override_defaults(
        self, registry: OperationRegistry
    ) -> None:
        op_name = register_tool(
            WordCountTestTool(),
            registry=registry,
            name="custom.word_count",
            description="custom description",
        )
        assert op_name == "custom.word_count"
        op = registry.get_or_error("custom.word_count")
        assert op.description == "custom description"

    def test_defaults_to_global_registry_when_none_given(self) -> None:
        reset_registry()
        try:
            register_tool(WordCountTestTool())
            assert get_registry().has_operation("word_count_test")
        finally:
            reset_registry()

    def test_rejects_tool_with_no_request_type_hint(
        self, registry: OperationRegistry
    ) -> None:
        with pytest.raises(ToolAdapterError, match="no type hint"):
            register_tool(UntypedRequestTool(), registry=registry)

    def test_rejects_tool_whose_request_hint_is_not_a_basemodel(
        self, registry: OperationRegistry
    ) -> None:
        with pytest.raises(ToolAdapterError, match="not a pydantic.BaseModel"):
            register_tool(NonModelRequestTool(), registry=registry)

    def test_duplicate_registration_raises(self, registry: OperationRegistry) -> None:
        register_tool(WordCountTestTool(), registry=registry)
        with pytest.raises(ValueError, match="already registered"):
            register_tool(WordCountTestTool(), registry=registry)

    @pytest.mark.asyncio
    async def test_registered_tool_invocation_round_trips_through_registry(
        self, registry: OperationRegistry
    ) -> None:
        """
        The callable registered by register_tool must satisfy
        OperationRegistry's own invoke_operation() contract -- this is what
        BOTH adapters/http and adapters/mcp actually call at request time.
        """
        from zeo_core.core.registry import invoke_operation

        register_tool(WordCountTestTool(), registry=registry)
        op = registry.get_or_error("word_count_test")
        result = await invoke_operation(op, {"text": "hello world", "upper": True})
        # invoke_operation() returns the operation callable's own dict
        # verbatim (no response_model was registered, so nothing re-wraps
        # it) -- that dict IS CapabilityResult.model_dump(mode="json"), the
        # same shape the HTTP route and MCP tool_fn each wrap one layer up
        # into their own {"success": ..., "data": ...} envelope.
        assert result["status"] == "success"
        assert result["data"]["word_count"] == 2
        assert result["data"]["text_out"] == "HELLO WORLD"

    def test_pre_run_failure_short_circuits_run(
        self, registry: OperationRegistry
    ) -> None:
        """A tool whose pre_run() fails must never reach run() -- same
        lifecycle contract LifecycleMixin documents for a real runner."""
        from zeo_core.tools import LifecycleMixin

        class FailingPreRunTool(LifecycleMixin, BaseZeoTool):
            name = "failing_pre_run"
            ran = False

            def pre_run(
                self, request: WordCountRequest, ctx: ToolContext
            ) -> CapabilityResult[None]:
                return CapabilityResult.fail(msg="nope", code="ZEO_VAL_REJECTED")

            def run(
                self, request: WordCountRequest, ctx: ToolContext
            ) -> CapabilityResult[None]:
                FailingPreRunTool.ran = True
                return CapabilityResult.ok(data=None)

        register_tool(FailingPreRunTool(), registry=registry)
        op = registry.get_or_error("failing_pre_run")
        result = op.callable(WordCountRequest(text="x"))
        assert result["status"] == "error"
        assert FailingPreRunTool.ran is False


class TestBuildToolContext:
    """build_tool_context: the ToolContext construction helper."""

    def test_builds_real_tool_context(self, tmp_path: Path) -> None:
        tool = WordCountTestTool()
        work_dir = str(tmp_path / "work")
        output_dir = str(tmp_path / "out")
        ctx = build_tool_context(tool, work_dir=work_dir, output_dir=output_dir)
        assert isinstance(ctx, ToolContext)
        assert ctx.tool_name == "word_count_test"
        assert ctx.tool_version == "1.0.0"
        assert ctx.work_dir == work_dir
        assert ctx.output_dir == output_dir

    def test_generates_fresh_run_id_when_not_given(self) -> None:
        tool = WordCountTestTool()
        ctx_a = build_tool_context(tool, work_dir=".", output_dir=".")
        ctx_b = build_tool_context(tool, work_dir=".", output_dir=".")
        assert ctx_a.run_id != ctx_b.run_id

    def test_forwards_services(self) -> None:
        tool = WordCountTestTool()
        ctx = build_tool_context(
            tool, work_dir=".", output_dir=".", services={"foo": "bar"}
        )
        assert ctx.get_service("foo") == "bar"


class TestCreateServer:
    """create_server: the MCP server that walks OperationRegistry."""

    def test_creates_server_with_no_operations(
        self, registry: OperationRegistry
    ) -> None:
        server = create_server(registry, name="empty-test")
        assert server.name == "empty-test"

    @pytest.mark.asyncio
    async def test_lists_registered_operations_as_mcp_tools(
        self, registry: OperationRegistry
    ) -> None:
        register_tool(WordCountTestTool(), registry=registry)
        server = create_server(registry, name="listing-test")
        tools = await server.list_tools()
        names = [t.name for t in tools]
        assert "word_count_test" in names

    @pytest.mark.asyncio
    async def test_tool_input_schema_matches_request_model_fields(
        self, registry: OperationRegistry
    ) -> None:
        register_tool(WordCountTestTool(), registry=registry)
        server = create_server(registry, name="schema-test")
        tools = await server.list_tools()
        tool = next(t for t in tools if t.name == "word_count_test")
        props = tool.input_schema["properties"]
        assert "text" in props
        assert "upper" in props
        assert tool.input_schema["required"] == ["text"]

    @pytest.mark.asyncio
    async def test_call_tool_round_trips_a_real_registered_tool(
        self, registry: OperationRegistry
    ) -> None:
        """
        Full behavioral round trip: a real BaseZeoTool, registered
        mechanically, exposed by the real MCP server, invoked through the
        real mcp.Client in-memory transport.
        """
        from mcp import Client

        register_tool(WordCountTestTool(), registry=registry)
        server = create_server(registry, name="round-trip-test")

        async with Client(server) as client:
            result = await client.call_tool(
                "word_count_test", {"text": "one two three", "upper": True}
            )
            assert result.is_error is False
            payload = result.structured_content or result.content
            assert payload is not None

    @pytest.mark.asyncio
    async def test_call_tool_surfaces_validation_error_not_crash(
        self, registry: OperationRegistry
    ) -> None:
        from mcp import Client

        register_tool(WordCountTestTool(), registry=registry)
        server = create_server(registry, name="validation-test")

        async with Client(server) as client:
            result = await client.call_tool("word_count_test", {})
            assert result.is_error is True

    @pytest.mark.asyncio
    async def test_directly_registered_operation_also_reachable(
        self, registry: OperationRegistry
    ) -> None:
        """
        Non-tool operations (registered by hand, the way the HTTP adapter's
        own tests do it) are equally reachable -- create_server walks
        OperationRegistry generically, not a tool-specific registry.
        """
        from mcp import Client

        registry.register(
            name="test.echo",
            callable_=echo_operation,
            request_model=EchoRequest,
            description="Echo test operation",
        )
        server = create_server(registry, name="echo-test")

        async with Client(server) as client:
            result = await client.call_tool("test_echo", {"text": "hi"})
            assert result.is_error is False


class TestSameRegistryServesBothAdapters:
    """
    The operator's own directive: "follow the existing OperationRegistry
    pattern... rather than inventing a parallel registration mechanism."
    Proven behaviorally, not just architecturally: one registration, two
    adapters, matching results.
    """

    @pytest.mark.asyncio
    async def test_http_and_mcp_agree_on_the_same_registered_tool(
        self, registry: OperationRegistry
    ) -> None:
        from fastapi.testclient import TestClient
        from mcp import Client

        from zeo_core.adapters.http.app import create_app

        register_tool(WordCountTestTool(), registry=registry)

        http_app = create_app(registry=registry)
        http_client = TestClient(http_app)
        http_resp = http_client.post(
            "/ops/word_count_test", json={"text": "a b c", "upper": False}
        )
        assert http_resp.status_code == 200
        http_data = http_resp.json()["data"]["data"]

        server = create_server(registry, name="dual-test")
        async with Client(server) as mcp_client:
            mcp_result = await mcp_client.call_tool(
                "word_count_test", {"text": "a b c", "upper": False}
            )
            assert mcp_result.is_error is False

        assert http_data["word_count"] == 3
        assert http_data["text_out"] == "a b c"
