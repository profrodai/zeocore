"""Both Revolut profiles are real, explicit and separate."""

from __future__ import annotations

from zeo_core.integrations.environments.catalog import CATALOG
from zeo_core.integrations.hosted.profile import ExecutionProfile
from zeo_core.integrations.hosted.setup import AuthMethod, SupportStatus
from zeo_core.integrations.hosted.setup_catalog import setup_manifest


def test_revolut_offers_a_local_profile_and_forwards_configuration_only() -> None:
    manifest = setup_manifest("revolut.business")
    assert manifest is not None
    profiles = {item.profile: item for item in manifest.profiles}
    local = profiles[ExecutionProfile.LOCAL]
    assert local.support is SupportStatus.IMPLEMENTED
    assert local.auth_method is AuthMethod.OAUTH
    assert profiles[ExecutionProfile.HOSTED].support is SupportStatus.NOT_ADMITTED
    assert manifest.live_validation == "not_run"
    setup = CATALOG["revolut.business"]
    assert setup.entry_point
    # Configuration only: no variable can carry the key or a token.
    assert setup.variables == (
        "REVOLUT_ENVIRONMENT",
        "REVOLUT_REDIRECT_URI",
        "REVOLUT_CLIENT_ID",
    )
    assert not [name for name in setup.variables if "TOKEN" in name or "KEY" in name]
