"""
Bind a capability into OperationRegistry and exercise the HTTP adapter.

Requires the 'http' extra:

    uv pip install "zeocore[http]"

This example does not start uvicorn. It builds the FastAPI app the same
way a server would, then uses TestClient to hit /health and POST /ops.
To run a real server instead:

    from zeo_core.adapters.http import run
    run(HttpAdapterConfig(host="127.0.0.1", port=8080, auth_token=None))

Run:

    uv run examples/http_adapter_usage.py
"""

from __future__ import annotations

import logging
import sys
from tempfile import TemporaryDirectory

from pydantic import BaseModel

from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.core.fs import get_service as get_fs_service
from zeo_core.core.jobs import InMemoryJobStore, ThreadPoolJobRunner
from zeo_core.core.registry import OperationRegistry
from zeo_core.tools import (
    ToolContext,
    bound_capability_of,
    capability,
    register_capability_operation,
)


class GreetRequest(BaseModel):
    name: str


class GreetResponse(BaseModel):
    message: str


@capability(
    id="demo.greet@1.0.0",
    description="Greet a person by name.",
    effects={EffectKind.READ},
    examples=(
        CapabilityExample(
            request={"name": "World"},
            response={"message": "Hello, World!"},
        ),
    ),
)
def greet(request: GreetRequest, ctx: ToolContext) -> CapabilityResult[GreetResponse]:
    _ = ctx
    return CapabilityResult.ok(data=GreetResponse(message=f"Hello, {request.name}!"))


def main() -> None:
    try:
        from fastapi.testclient import TestClient

        from zeo_core.adapters.http import HttpAdapterConfig, create_app
    except ImportError:
        print(
            "HTTP adapter requires FastAPI. Install with: uv pip install 'zeocore[http]'",
            file=sys.stderr,
        )
        sys.exit(0)

    cap = bound_capability_of(greet)
    ops = OperationRegistry()

    with TemporaryDirectory(prefix="zeo_http_") as tmp:

        def factory(_cap: object) -> ToolContext:
            return ToolContext(
                run_id="http-demo",
                tool_name="greet",
                tool_version="1.0.0",
                logger=logging.getLogger("greet"),
                fs=get_fs_service(),
                work_dir=tmp,
                output_dir=tmp,
            )

        op_name = register_capability_operation(
            cap, registry=ops, context_factory=factory, name="greet"
        )
        cfg = HttpAdapterConfig(auth_token=None, host="127.0.0.1", port=8080)
        store = InMemoryJobStore()
        runner = ThreadPoolJobRunner(
            registry=ops,
            store=store,
            max_workers=cfg.max_workers,
            hmac_secret=cfg.hmac_secret,
        )
        app = create_app(cfg, registry=ops, job_store=store, job_runner=runner)
        client = TestClient(app)
        live = client.get("/health/live")
        listed = client.get("/ops")
        invoked = client.post(f"/ops/{op_name}", json={"name": "World"})
        print("health:", live.status_code, live.json())
        print("ops:", listed.status_code, listed.json())
        print("invoke:", invoked.status_code, invoked.json())


if __name__ == "__main__":
    main()
