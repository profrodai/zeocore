

"""
Minimal local runner example.

This example shows how to run a tool locally without using the full
QuackRunner infrastructure. It's useful for:
- Testing tools during development
- Understanding the tool execution model
- Running tools in custom environments

This is NOT production code - it's a teaching example.
Production code should use ToolRunner from quack_runner.workflow.
"""

from quack_core.contracts import (
    CapabilityResult,
    EchoRequest,
)
from quack_core.tools import ToolContext

# Import the example tool
from echo_tool import EchoTool


def run_tool_locally(tool_class, request):
    """
    Run a tool locally with minimal setup.

    This demonstrates the core execution pattern:
    1. Instantiate tool
    2. Build ToolContext
    3. Initialize tool
    4. Call tool.run(request, ctx)
    5. Handle result

    Args:
        tool_class: The tool class to run
        request: The request model

    Returns:
        CapabilityResult from the tool
    """
    # 1. Instantiate tool
    tool = tool_class()

    # 2. Build ToolContext (minimal - no filesystem, no dirs)
    ctx = ToolContext(
        tool_name=tool.name,
        tool_version=tool.version,
        metadata={"environment": "local_dev"}
    )

    # 3. Initialize tool
    init_result = tool.initialize(ctx)
    if init_result.status != "success":
        print(f"❌ Tool initialization failed: {init_result.human_message}")
        return init_result

    print(f"✅ Tool initialized: {tool.name} v{tool.version}")

    # 4. Call tool.run()
    result = tool.run(request, ctx)

    # 5. Handle result
    return result


def main():
    """
    Main entry point - demonstrates running the echo tool.
    """
    print("=" * 60)
    print("Minimal Local Tool Runner")
    print("=" * 60)
    print()

    # Create request
    request = EchoRequest(
        text="QuackCore",
        preset="friendly",
        override_greeting="Greetings"
    )

    print(f"Request: {request.model_dump_json(indent=2)}")
    print()

    # Run tool
    result = run_tool_locally(EchoTool, request)

    # Display result
    print(f"Status: {result.status}")
    print(f"Message: {result.human_message}")
    print()

    if result.data:
        print(f"Output: {result.data}")
        print()

    print("Metadata:")
    print(result.model_dump_json(indent=2))
    print()

    # Show what a runner would do next:
    print("=" * 60)
    print("What a runner would do next:")
    print("=" * 60)
    print()
    print("1. Write output artifact:")
    print(f"   - Data: {result.data}")
    print(f"   - Format: determined by runner config")
    print()
    print("2. Build RunManifest:")
    print(f"   - run_id: {result.run_id}")
    print(f"   - status: {result.status}")
    print(f"   - outputs: [ArtifactRef(...)]")
    print()
    print("3. Persist manifest:")
    print("   - Write to manifest.json")
    print("   - Upload to storage (optional)")
    print()
    print("Note: Tools do NONE of this - it's all runner responsibility!")


if __name__ == "__main__":
    main()