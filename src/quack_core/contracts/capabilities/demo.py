# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/contracts/capabilities/demo.py
# module: quack_core.contracts.capabilities.demo
# role: module
# neighbors: __init__.py, contract.py
# exports: EchoRequest, EchoPolicy, VideoRefRequest, echo_text, validate_video_ref
# git_branch: refactor/newHeaders
# git_commit: 7d82586
# === QV-LLM:END ===

from typing import Optional
from pydantic import BaseModel
from quack_core.contracts.capabilities.contract import CapabilityResult
from quack_core.config_base import BasePolicy, ConfigResolver


# --- 1. Define Request & Policy ---

class EchoRequest(BaseModel):
    """Input from n8n or CLI."""
    text: str
    preset: Optional[str] = None
    override_greeting: Optional[str] = None


class EchoPolicy(BasePolicy):
    """Configuration defaults."""
    default_greeting: str = "Hello"
    safety_check_enabled: bool = True


# --- 2. The Capability Function ---

def echo_text(req: EchoRequest) -> CapabilityResult[str]:
    """
    A simple capability that returns text.
    Demonstrates: Config resolution, Rich Results.
    """
    try:
        # Resolve Config
        config = ConfigResolver.resolve(req, EchoPolicy, "demo")
    except Exception as e:
        return CapabilityResult.fail_from_exc("Config resolution failed",
                                              "QC_CFG_ERROR", e)

    # Business Logic
    final_text = f"{config.default_greeting} {req.text}"

    # Return Rich Result
    return CapabilityResult.ok(
        data=final_text,
        msg="Echo successful",
        metadata={
            "used_preset": req.preset,
            "safety_checked": config.safety_check_enabled
        }
    )


class VideoRefRequest(BaseModel):
    url: str


def validate_video_ref(req: VideoRefRequest) -> CapabilityResult[bool]:
    """
    Dummy validator. Returns SKIPPED if URL is not a valid video provider.
    Demonstrates: Branching logic for n8n.
    """
    if "youtube.com" not in req.url and "drive.google.com" not in req.url:
        return CapabilityResult.skip(
            reason="URL is not from a supported provider",
            code="QC_VAL_UNSUPPORTED_PROVIDER"
        )

    return CapabilityResult.ok(data=True, msg="Video reference is valid")