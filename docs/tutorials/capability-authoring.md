# Author your first capability

A capability is a typed operation that a runner can inspect and invoke. In this
lesson you will build one, register it, and run it locally.

## Goals

By the end, you will be able to:

- describe input and output with Pydantic models;
- declare identity, effects, and an example with `@capability`;
- supply the runner-owned `ToolContext`;
- register and invoke a `BoundCapability`; and
- inspect the structured `CapabilityResult`.

ZeoCore requires Python 3.13 or newer. From the repository root, install the
project and run the canonical example:

```bash
python3.13 -m pip install -e .
python3.13 examples/capability_authoring.py
```

Expected output:

```text
Hello, World!
```

## The runnable source of truth

The complete program is
[`examples/capability_authoring.py`](../../examples/capability_authoring.py).
Use that file when copying or checking this lesson:

```python
from __future__ import annotations

import logging
from tempfile import TemporaryDirectory

from pydantic import BaseModel

from zeo_core.contracts import CapabilityExample, CapabilityResult, EffectKind
from zeo_core.core.fs import get_service as get_fs_service
from zeo_core.tools import (
    CapabilityRegistry,
    ToolContext,
    bound_capability_of,
    capability,
    invoke_sync,
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
    logger = ctx.require_logger()
    logger.info("greeting %s", request.name)
    return CapabilityResult.ok(data=GreetResponse(message=f"Hello, {request.name}!"))


def main() -> None:
    with TemporaryDirectory(prefix="zeo_capability_") as tmp:
        ctx = ToolContext(
            run_id="greet-001",
            tool_name="greet",
            tool_version="1.0.0",
            logger=logging.getLogger("greet"),
            fs=get_fs_service(),
            work_dir=tmp,
            output_dir=tmp,
        )
        cap = bound_capability_of(greet)
        registry = CapabilityRegistry()
        registry.register(cap)
        result = invoke_sync(cap, GreetRequest(name="World"), ctx)
        print(result.data.message if result.data else result.human_message)


if __name__ == "__main__":
    main()
```

## Step 1: model the contract

`GreetRequest` is the accepted input; `GreetResponse` is the successful
payload. Both are Pydantic models, so ZeoCore can derive JSON Schema and
validate the capability signature. The return annotation must be
`CapabilityResult[ResponseModel]`.

## Step 2: declare the capability

`@capability` turns the typed function into an inspectable capability:

- `id` uses `namespace.name@semantic-version`;
- `description` tells people and adapters what it does;
- `effects` declares observable behavior (`READ` here);
- `examples` contains at least one JSON-safe request and optional response.

Effects are facts for policy and scheduling, not permission grants. The runner
still owns authorization.

The decorated name remains callable as a Python function.
`bound_capability_of(greet)` retrieves the attached `BoundCapability`, which
contains the definition and invocation behavior.

## Step 3: receive context and return a result

The handler receives dependencies through `ToolContext`; it does not create
them. Here it uses the runner-provided logger. The context is immutable and
also carries identity, filesystem access, directories, optional services, and
JSON-safe metadata.

`CapabilityResult.ok(...)` wraps the typed response. Callers can branch on
`result.status` and then read `result.data`. Expected skips and failures also
use `CapabilityResult`; see [Results and errors](results-and-errors.md).

## Step 4: register and invoke

`CapabilityRegistry` is explicit and in-process. Registering makes the
capability discoverable by its canonical ID; duplicate IDs are rejected.
`invoke_sync` validates the request, evaluates guards and requirements, invokes
the handler, and normalizes the outcome.

Use `invoke_async` for an async capability. Do not call an async handler with
`invoke_sync`.

## Exercise

Change the lesson into `demo.shout@1.0.0`:

1. Rename the request and response models to `ShoutRequest` and
   `ShoutResponse`.
2. Return `request.text.upper()` in a `text` response field.
3. Update the description and declared example.
4. Invoke it with `"hello ZeoCore"`.

Your final line should be:

```text
HELLO ZEOCORE
```

Then retrieve it from the registry with
`registry.get("demo.shout@1.0.0")` and confirm that its
`definition.canonical_id()` matches.

## Next steps

- Learn all result paths in [Results and errors](results-and-errors.md).
- Learn runner-provided dependencies in
  [Context, configuration, and files](context-config-files.md).
- For an existing stateful class, use `BaseZeoTool` and
  `tool_to_capability`; compare
  [`examples/minimal_tool.py`](../../examples/minimal_tool.py) and
  [`examples/tool_to_capability.py`](../../examples/tool_to_capability.py).
- Add policy guards with
  [`examples/capability_guards.py`](../../examples/capability_guards.py).
- Project a manifest with
  [`examples/llm_tools_usage.py`](../../examples/llm_tools_usage.py), or bind
  adapters with
  [`examples/http_adapter_usage.py`](../../examples/http_adapter_usage.py) and
  [`examples/mcp_server_usage.py`](../../examples/mcp_server_usage.py).
