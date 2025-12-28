# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/capabilities/demo/impl.py
# module: quack_core.contracts.capabilities.demo.impl
# role: module
# neighbors: __init__.py, models.py
# exports: echo_text, validate_video_ref
# git_branch: refactor/newHeaders
# git_commit: 98b2a5c
# === QV-LLM:END ===

"""
Demo capability implementations.

OPTIONAL: These implementations are only included as examples.
In production, implementations belong in Ring B (quack_core.toolkit).

These demos show how to use CapabilityResult without external dependencies.
"""

from quack_core.contracts.envelopes import CapabilityResult
from quack_core.contracts.capabilities.demo.models import EchoRequest, VideoRefRequest


def echo_text(req: EchoRequest) -> CapabilityResult[str]:
    """
    Simple echo capability that returns formatted text.

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