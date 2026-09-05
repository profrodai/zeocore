"""Notion transport policy is explicit rather than inherited accidentally."""

from unittest.mock import patch

import pytest

from zeo_core.integrations.notion.transport import build_notion_http_client


def test_default_transport_disables_ambient_proxy_inheritance() -> None:
    with patch("httpx.Client") as factory:
        build_notion_http_client()

    factory.assert_called_once_with(trust_env=False)


@pytest.mark.integration
def test_explicit_proxy_profile_opts_into_ambient_configuration() -> None:
    with patch("httpx.Client") as factory:
        build_notion_http_client(trust_env=True)

    factory.assert_called_once_with(trust_env=True)
