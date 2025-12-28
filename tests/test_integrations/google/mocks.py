# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/mocks.py
# role: tests
# neighbors: __init__.py, test_auth_provider.py, test_config_provider.py, test_serialization.py
# exports: mock_credentials
# git_branch: refactor/newHeaders
# git_commit: 175956c
# === QV-LLM:END ===

import json
from unittest.mock import MagicMock


def mock_credentials(
    token="mock_token",
    refresh_token="mock_refresh_token",
    client_id="mock_client_id",
    client_secret="mock_client_secret",
    token_uri="https://oauth2.googleapis.com/token",
    scopes=None,
    expired=False,
    valid=True,
    expiry_timestamp=1893456000,  # 2030-01-01
    **kwargs,
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
