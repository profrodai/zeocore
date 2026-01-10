# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/test_serialization.py
# role: tests
# neighbors: __init__.py, mocks.py, test_auth_provider.py, test_config_provider.py
# exports: mock_credentials
# git_branch: feat/9-make-setup-work
# git_commit: 8bfe1405
# === QV-LLM:END ===

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
    creds.token = token
    creds.refresh_token = refresh_token
    creds.client_id = client_id
    creds.client_secret = client_secret
    creds.token_uri = token_uri
    creds.scopes = scopes or ["https://www.googleapis.com/auth/drive.file"]
    creds.expired = expired
    creds.valid = valid

    if expiry_timestamp is not None:
        expiry = MagicMock()
        expiry.timestamp.return_value = expiry_timestamp
        expiry.isoformat.return_value = "2030-01-01T00:00:00"  # Important for test
        creds.expiry = expiry
    else:
        creds.expiry = None

    creds.to_json.return_value = '{"token": "%s"}' % token

    return creds
