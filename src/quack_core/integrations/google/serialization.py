# quack-core/src/quack-core/integrations/google/serialization.py

from typing import Any

from google.oauth2.credentials import Credentials


def serialize_credentials(credentials: Credentials) -> dict[str, Any]:
    """
    Serialize a Google Credentials object into a dictionary.

    Args:
        credentials: Credentials object to serialize.

    Returns:
        A dictionary representation of the credentials.
    """
    return {
        "token": str(credentials.token) if credentials.token else None,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri or "https://oauth2.googleapis.com/token",
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes or [],
        "expiry": (
            credentials.expiry.isoformat() + "Z" if credentials.expiry else None
        ),
    }
