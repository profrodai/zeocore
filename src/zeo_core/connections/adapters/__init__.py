"""
Concrete custody and persistence adapters for the connections domain.

`macos_keychain` (step 3) is the custody adapter; `sqlite` (step 4) provides
durable organization-scoped storage. Adapters implement the protocols declared in
`zeo_core.contracts.connections.protocols` -- this package depends on
`zeo_core.contracts.connections`, never the reverse.
"""

from __future__ import annotations

from zeo_core.connections.adapters.macos_keychain import (
    KeychainEffectDispatcher,
    KeychainSecretStore,
)
from zeo_core.connections.adapters.sqlite import (
    ConnectionStoreError,
    SQLiteConnectionStore,
)

__all__ = [
    "ConfirmationEvidence",
    "ConnectionStoreError",
    "KeychainEffectDispatcher",
    "KeychainSecretStore",
    "SQLiteConnectionStore",
]
