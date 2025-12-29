# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/capabilities/demo/_impl.py
# module: quack_core.contracts.capabilities.demo._impl
# role: module
# neighbors: __init__.py, models.py
# exports: echo_text, validate_video_ref
# git_branch: refactor/toolkitWorkflow
# git_commit: de0fa70
# === QV-LLM:END ===

"""
Demo capability implementations (INTERNAL EXAMPLES ONLY).

⚠️ NOT FOR PRODUCTION USE ⚠️

These implementations are kept in Ring A only as minimal reference examples
to demonstrate contract usage patterns. They have no external dependencies
beyond contracts themselves.

In a real system, capability implementations belong in Ring B (quack_core.tools).

The underscore prefix (_impl.py) marks this module as internal/private.
Do not import these functions in production code.
"""

from quack_core.contracts.envelopes import CapabilityResult
from quack_core.contracts.capabilities.demo.models import EchoRequest, VideoRefRequest


def echo_text(req: EchoRequest) -> CapabilityResult[str]:
    """
    Simple echo capability that returns formatted text.

    ⚠️ EXAMPLE ONLY - NOT FOR PRODUCTION USE

    Demonstrates:
    - Basic CapabilityResult.ok() usage
    - Metadata population
    - No external dependencies

    Args:
        req: Echo request with text and optional greeting

    Returns:
        CapabilityResult with formatted text

    Example:
        >>> result = echo_text(EchoRequest(text="World"))
        >>> result.status
        <CapabilityStatus.success: 'success'>
        >>> result.data
        'Hello World'
    """
    greeting = req.override_greeting or "Hello"
    final_text = f"{greeting} {req.text}"

    return CapabilityResult.ok(
        data=final_text,
        msg="Echo successful",
        metadata={
            "used_preset": req.preset,
            "greeting": greeting
        }
    )


def validate_video_ref(req: VideoRefRequest) -> CapabilityResult[bool]:
    """
    Validate video URL against supported providers.

    ⚠️ EXAMPLE ONLY - NOT FOR PRODUCTION USE

    Demonstrates:
    - CapabilityResult.skip() for policy decisions
    - CapabilityResult.ok() for validation success
    - Machine branching via skip codes

    Args:
        req: Video URL validation request

    Returns:
        CapabilityResult indicating validation outcome

    Example:
        >>> # Valid provider
        >>> result = validate_video_ref(VideoRefRequest(url="https://youtube.com/watch?v=abc"))
        >>> result.status
        <CapabilityStatus.success: 'success'>

        >>> # Unsupported provider
        >>> result = validate_video_ref(VideoRefRequest(url="https://example.com/video.mp4"))
        >>> result.status
        <CapabilityStatus.skipped: 'skipped'>
        >>> result.machine_message
        'QC_VAL_UNSUPPORTED_PROVIDER'
    """
    supported_providers = ["youtube.com", "drive.google.com", "vimeo.com"]

    # Check if URL contains any supported provider
    if not any(provider in req.url for provider in supported_providers):
        return CapabilityResult.skip(
            reason=f"URL is not from a supported provider. Supported: {', '.join(supported_providers)}",
            code="QC_VAL_UNSUPPORTED_PROVIDER"
        )

    return CapabilityResult.ok(
        data=True,
        msg="Video reference is valid",
        metadata={"url": req.url}
    )