# === QV-LLM:BEGIN ===
# path: quack-core/examples/tools/run_echo_on_file.py
# role: module
# neighbors: echo_tool.py, minimal_runner.py
# exports: main
# git_branch: refactor/toolkitWorkflow
# git_commit: 82e6d2b
# === QV-LLM:END ===



"""
File-based tool execution example.

This example demonstrates how to use ToolRunner to execute a tool
with file inputs and outputs. This is closer to production usage
than the minimal_runner example.

Key concepts:
- ToolRunner handles file I/O
- Tool receives typed request and returns CapabilityResult
- Runner builds RunManifest from result
- Artifacts are created and written by runner, not tool
"""

import sys
from pathlib import Path

# Add parent to path for imports (example only - not needed in real code)
sys.path.insert(0, str(Path(__file__).parent))

from quack_core.contracts import EchoRequest, CapabilityStatus

# Import the example tool
from echo_tool import EchoTool


def main():
    """
    Demonstrate file-based tool execution.

    This shows the pattern that QuackRunner uses internally.
    """
    print("=" * 60)
    print("File-Based Tool Execution Example")
    print("=" * 60)
    print()

    # Setup paths
    work_dir = Path("/tmp/quack_example")
    work_dir.mkdir(exist_ok=True)

    input_file = work_dir / "input.txt"
    output_dir = work_dir / "output"
    output_dir.mkdir(exist_ok=True)

    # Create input file
    input_text = "QuackCore ecosystem"
    input_file.write_text(input_text)
    print(f"📄 Created input file: {input_file}")
    print(f"   Content: {input_text}")
    print()

    # Import ToolRunner (this would normally be in quack_runner)
    # For this example, we'll create a simplified version inline

    from quack_core.tools import ToolContext
    from quack_core.lib.fs.service import standalone as fs
    from quack_core.contracts import generate_run_id, RunManifest, ToolInfo, utcnow

    # Initialize tool
    tool = EchoTool()
    print(f"🔧 Initialized tool: {tool.name} v{tool.version}")
    print()

    # Build context (runner responsibility)
    ctx = ToolContext(
        run_id=generate_run_id(),
        tool_name=tool.name,
        tool_version=tool.version,
        fs=fs,
        work_dir=str(work_dir),
        output_dir=str(output_dir),
        metadata={"example": "file_based_execution"}
    )

    print(f"🎯 Built ToolContext:")
    print(f"   run_id: {ctx.run_id}")
    print(f"   work_dir: {ctx.work_dir}")
    print(f"   output_dir: {ctx.output_dir}")
    print()

    # Initialize tool
    init_result = tool.initialize(ctx)
    if init_result.status != CapabilityStatus.success:
        print(f"❌ Initialization failed: {init_result.human_message}")
        return

    print("✅ Tool initialized successfully")
    print()

    # Read input file (runner responsibility)
    content = input_file.read_text()

    # Build request from file content (runner responsibility)
    request = EchoRequest(
        text=content,
        preset="professional"
    )

    print(f"📋 Built request:")
    print(request.model_dump_json(indent=2))
    print()

    # Run tool (this is the only part the tool does)
    started_at = utcnow()
    result = tool.run(request, ctx)
    finished_at = utcnow()

    print(f"⚙️  Tool execution completed:")
    print(f"   Status: {result.status}")
    print(f"   Message: {result.human_message}")
    print()

    if result.status == CapabilityStatus.success:
        print(f"✅ Result data:")
        print(f"   {result.data}")
        print()

        # Write output (runner responsibility)
        output_file = output_dir / "echo_output.json"
        fs.write_json(
            str(output_file),
            {"output": result.data, "metadata": result.metadata},
            indent=2
        )
        print(f"💾 Wrote output to: {output_file}")
        print()

        # Build manifest (runner responsibility)
        from quack_core.contracts import (
            ManifestInput,
            ArtifactRef,
            ArtifactKind,
            StorageRef,
            StorageScheme
        )

        input_artifact = ArtifactRef(
            role="demo.echo.input",
            kind=ArtifactKind.intermediate,
            content_type="text/plain",
            storage=StorageRef(
                scheme=StorageScheme.local,
                uri=f"file://{input_file.absolute()}"
            )
        )

        output_artifact = ArtifactRef(
            role="demo.echo.output",
            kind=ArtifactKind.final,
            content_type="application/json",
            storage=StorageRef(
                scheme=StorageScheme.local,
                uri=f"file://{output_file.absolute()}"
            )
        )

        manifest = RunManifest(
            run_id=ctx.run_id,
            tool=ToolInfo(
                name=tool.name,
                version=tool.version,
                metadata=result.metadata
            ),
            started_at=started_at,
            finished_at=finished_at,
            duration_sec=(finished_at - started_at).total_seconds(),
            status=result.status,
            inputs=[
                ManifestInput(
                    name="source",
                    artifact=input_artifact,
                    required=True
                )
            ],
            outputs=[output_artifact],
            logs=result.logs,
            metadata=result.metadata
        )

        # Write manifest (runner responsibility)
        manifest_file = output_dir / "manifest.json"
        fs.write_json(str(manifest_file), manifest.model_dump(), indent=2)
        print(f"📋 Wrote manifest to: {manifest_file}")
        print()

        print("=" * 60)
        print("Summary:")
        print("=" * 60)
        print()
        print("Tool responsibilities (what the tool did):")
        print("  ✅ Received EchoRequest")
        print("  ✅ Processed the request")
        print("  ✅ Returned CapabilityResult")
        print()
        print("Runner responsibilities (what this script did):")
        print("  ✅ Built ToolContext")
        print("  ✅ Read input file")
        print("  ✅ Built request model")
        print("  ✅ Called tool.run()")
        print("  ✅ Wrote output file")
        print("  ✅ Built RunManifest")
        print("  ✅ Wrote manifest file")
        print()
        print("This separation keeps tools pure and runners responsible for I/O!")

    else:
        print(f"❌ Tool execution failed or was skipped:")
        print(f"   Status: {result.status}")
        print(f"   Message: {result.human_message}")
        if result.error:
            print(f"   Error code: {result.error.code}")


if __name__ == "__main__":
    main()