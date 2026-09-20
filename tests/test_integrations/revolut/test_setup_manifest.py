"""The catalogue must not advertise a local credential path for a bank."""

from __future__ import annotations

from zeo_core.integrations.environments.catalog import CATALOG
from zeo_core.integrations.hosted.profile import ExecutionProfile
from zeo_core.integrations.hosted.setup import AuthMethod, SupportStatus
from zeo_core.integrations.hosted.setup_catalog import setup_manifest


def test_revolut_has_no_local_profile_and_forwards_no_variables() -> None:
    manifest = setup_manifest("revolut.business")
    assert manifest is not None
    profiles = {item.profile: item for item in manifest.profiles}
    local = profiles[ExecutionProfile.LOCAL]
    assert local.support is SupportStatus.UNSUPPORTED
    assert local.auth_method is AuthMethod.UNSUPPORTED
    assert local.actions == ()
    assert profiles[ExecutionProfile.HOSTED].support is SupportStatus.NOT_ADMITTED
    assert manifest.operations == () and manifest.live_validation == "not_run"
    setup = CATALOG["revolut.business"]
    assert not setup.entry_point
    assert setup.variables == () and setup.prefixes == ()
