"""
Concrete custody and persistence adapters for the connections domain.

`macos_keychain` (step 3) is the first adapter; `sqlite` (step 4) is not
yet built. Adapters implement the protocols declared in
`zeo_core.contracts.connections.protocols` -- this package depends on
`zeo_core.contracts.connections`, never the reverse.
"""

from __future__ import annotations
