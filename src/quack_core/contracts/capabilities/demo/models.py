# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/capabilities/demo/models.py
# module: quack_core.contracts.capabilities.demo.models
# role: models
# neighbors: __init__.py, _impl.py
# exports: EchoRequest, VideoRefRequest
# git_branch: refactor/toolkitWorkflow
# git_commit: 5d876e8
# === QV-LLM:END ===

"""
Demo capability models for testing and examples.

These demonstrate the contract patterns without requiring heavy dependencies.
Implementation is optional and only for demonstration purposes.
"""


from pydantic import BaseModel

# --- Request/Response Models ---

class EchoRequest(BaseModel):
    """
    Simple echo request for demonstrating contract patterns.

    Example:
        >>> req = EchoRequest(text="Hello QuackCore")
    """

    text: str
    preset: str | None = None
    override_greeting: str | None = None


class VideoRefRequest(BaseModel):
    """
    Simple URL validation request.

    Demonstrates skip logic (policy-based branching).
    """

    url: str

# NOTE: Actual implementations (echo_text, validate_video_ref functions)
# are OPTIONAL in contracts. They belong in Ring B (tools) if needed.
# We keep them here only as minimal demos.
