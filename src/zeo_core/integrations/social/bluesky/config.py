"""Configuration provider for the Bluesky integration.

Bluesky authenticates with a pasted **app password** (RULING-409 s6c): no
OAuth2 flow, no developer app, no approval. The only configuration this
provider needs is the PDS (Personal Data Server) host to talk to -- almost
always `https://bsky.social` for a normal account -- plus where the
resulting session credential should be written on disk.

Follows `NotionConfigProvider`'s shape (integrations/notion/config.py): a
static-credential integration, not an OAuth one, so this mirrors that
config provider's structure rather than Google's OAuth-flow-based one.
"""

import os
from typing import Any

from zeo_core.core.logging import get_logger
from zeo_core.integrations.core import BaseConfigProvider, ConfigResult
from zeo_core.integrations.social.bluesky.credential_paths import (
    default_credentials_path,
)

logger = get_logger(__name__)

DEFAULT_SERVICE_URL = "https://bsky.social"


class BlueskyConfigProvider(BaseConfigProvider):
    """Configuration provider for the Bluesky integration."""

    def __init__(self, log_level: int = 20) -> None:
        """Initialize the Bluesky configuration provider.

        Args:
            log_level: Logging level.
        """
        super().__init__(log_level=log_level)

    @property
    def name(self) -> str:
        """Name of the configuration provider."""
        return "Bluesky"

    def get_default_config(self) -> dict[str, Any]:
        """Get default Bluesky configuration.

        `credentials_file` resolves through `default_credentials_path()`
        (platformdirs-based, per-user, never CWD-relative) -- the same
        defect class RULING-407/408 fixed for Google is avoided here by
        construction rather than by a later migration, since this
        integration is greenfield.
        """
        return {
            "service_url": os.environ.get("BLUESKY_SERVICE_URL", DEFAULT_SERVICE_URL),
            "identifier": os.environ.get("BLUESKY_IDENTIFIER", ""),
            "app_password": os.environ.get("BLUESKY_APP_PASSWORD", ""),
            "credentials_file": default_credentials_path(),
        }

    def load_config(self, config_path: str | None = None) -> ConfigResult:
        """Load configuration from a file, falling back to
        `get_default_config()` when no YAML config file exists anywhere in
        the default search locations.

        `BaseConfigProvider.load_config()` (integrations/core/base.py)
        raises `ZeoConfigurationError` uncaught whenever no config file is
        found -- a real, pre-existing defect the Google fresh-directory
        walkthrough test's own docstring names and explicitly declines to
        fix (out of that charter's scope). It is squarely IN this SOW's
        scope: RULING-409 s6c/SOW-02 name fresh-directory construction as
        an acceptance criterion, and a fresh directory has no config file by
        construction. Mirrors `NotionConfigProvider.load_config`'s own
        identical fallback shape (integrations/notion/config.py) rather than
        inventing a new one.
        """
        try:
            result = super().load_config(config_path)
        except Exception as e:
            logger.debug(f"No Bluesky config file found, using defaults: {e}")
            return ConfigResult.success_result(
                message="Using default Bluesky configuration",
                content=self.get_default_config(),
                config_path=config_path,
            )

        if not result.success or not result.content:
            logger.warning(
                f"Couldn't load Bluesky config from {config_path}: {result.error}"
            )
            return ConfigResult.success_result(
                message="Using default Bluesky configuration",
                content=self.get_default_config(),
                config_path=config_path,
            )

        # A config section that omits a key (e.g. a YAML file that only
        # sets service_url) still needs the env/default fallback for the
        # keys it left out -- merge defaults under, not over, whatever the
        # file actually provided.
        merged = self.get_default_config()
        merged.update(result.content)
        return ConfigResult.success_result(
            content=merged,
            message=result.message,
            config_path=result.config_path,
        )

    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate Bluesky configuration.

        A `service_url` is always required (it has a sane default, so this
        only fails on an explicit empty override). `identifier`/
        `app_password` are NOT required here: they may be supplied later,
        directly to `authenticate()`, or already sitting in the credentials
        file from a prior session -- exactly like `NotionConfigProvider`
        does not require a token be present in config either, deferring
        that check to auth time.
        """
        service_url = config.get("service_url")
        if not service_url or not str(service_url).strip():
            self.logger.error("Bluesky service_url must not be empty")
            return False
        return True
