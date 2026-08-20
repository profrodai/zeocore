"""
Tests for zeo_core.integrations.google's top-level re-exports.

Regression coverage for the zeocore-dx-audit-SOW-1 finding: this
package's __init__.py only re-exported GoogleAuthProvider/
GoogleConfigProvider, not GoogleDriveService/GoogleMailService -- so a
plausible first guess (`from zeo_core.integrations.google import
GoogleDriveService`, one level too shallow) failed with an ImportError
that gave no hint the correct path was one level deeper
(zeo_core.integrations.google.drive).
"""

from zeo_core.integrations import google


def test_drive_service_reachable_from_google_package() -> None:
    """GoogleDriveService must be importable one level shallower than before."""
    assert hasattr(google, "GoogleDriveService")
    assert "GoogleDriveService" in google.__all__

    # Must be the exact same class as the (still-supported) deeper import path.
    from zeo_core.integrations.google.drive import GoogleDriveService

    assert google.GoogleDriveService is GoogleDriveService


def test_mail_service_reachable_from_google_package() -> None:
    """GoogleMailService must be importable one level shallower than before."""
    assert hasattr(google, "GoogleMailService")
    assert "GoogleMailService" in google.__all__

    from zeo_core.integrations.google.mail import GoogleMailService

    assert google.GoogleMailService is GoogleMailService


def test_auth_and_config_providers_still_reachable() -> None:
    """Pre-existing exports must not regress."""
    assert hasattr(google, "GoogleAuthProvider")
    assert hasattr(google, "GoogleConfigProvider")


def test_drive_models_reachable() -> None:
    """DriveFile/DriveFolder are re-exported alongside the service class."""
    assert hasattr(google, "DriveFile")
    assert hasattr(google, "DriveFolder")


def test_all_matches_actual_attributes() -> None:
    """Every name in __all__ must actually resolve on the module."""
    for name in google.__all__:
        assert hasattr(google, name)
