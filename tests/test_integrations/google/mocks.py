# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/mocks.py
# === QV-LLM:END ===

import json
from typing import Any
from unittest.mock import MagicMock


def mock_credentials(
    token="mock_token",  # noqa: S107 -- mock class default, fake credential value, not a real secret
    refresh_token="mock_refresh_token",  # noqa: S107 -- mock class default, fake credential value, not a real secret
    client_id="mock_client_id",
    client_secret="mock_client_secret",  # noqa: S107 -- mock class default, fake credential value, not a real secret
    token_uri="https://oauth2.googleapis.com/token",  # noqa: S107 -- mock class default, fake credential value, not a real secret
    scopes=None,
    expired=False,
    valid=True,
    expiry_timestamp=1893456000,  # 2030-01-01
    **kwargs: Any,
):
    creds = MagicMock()

    # Required auth fields
    creds.token = token
    creds.refresh_token = refresh_token
    creds.client_id = client_id
    creds.client_secret = client_secret
    creds.token_uri = token_uri
    creds.scopes = scopes or ["https://www.googleapis.com/auth/drive.file"]
    creds.expired = expired
    creds.valid = valid

    # Expiry mock
    expiry = MagicMock()
    expiry.timestamp.return_value = expiry_timestamp
    creds.expiry = expiry

    # to_json return value should resemble a real Credentials JSON string
    creds.to_json.return_value = json.dumps(
        {
            "token": token,
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "token_uri": token_uri,
            "scopes": creds.scopes,
            "expiry": expiry_timestamp,
        }
    )

    return creds
