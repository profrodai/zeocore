"""
Connections domain adapters (Ring B), ZC0-KERNEL-SEAM-01 step 3+.

Distinct from `zeo_core.contracts.connections` (Ring A / Kernel, steps 1-2):
that package is frozen pure contracts and protocols with NO adapter imports.
This package is the reverse -- concrete adapters that implement those
protocols against a real external system (macOS Keychain, step 3; SQLite,
step 4; connector admission and the fake provider adapter, step 5;
orchestration, step 6). The one-way dependency direction is enforced by
`tests/connections/test_no_adapter_imports.py`'s FORBIDDEN_IMPORT_ROOTS,
which names `zeo_core.connections.adapters` as forbidden for the contracts
package to import -- adapters depend on contracts, never the reverse.

Step 3 (this step) adds `zeo_core.connections.adapters.macos_keychain`:
a `SecretStore` implementation backed by the macOS Keychain via an
injected subprocess runner over the `security` CLI, per the packet's
binding order item 3 ("macOS Keychain custody, injected subprocess
runner, synthetic canary tests; public values carry only SecretRef") and
SOW-01 section 3a's new-dependency ruling ("`keyring`, if proposed, is a
new dependency and returns for a ruling; the packet specifies an injected
subprocess runner") -- so this package adds no new PyPI dependency; it
shells out to the `security` binary that ships with macOS.
"""

from __future__ import annotations
