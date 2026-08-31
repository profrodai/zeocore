"""Social-platform integrations for zeo_core.

Greenfield package (RULING-409 s6c: "integrations/ has no social package --
GREENFIELD"), established by the first connector, `social.bluesky`. Each
platform's connector lives in its own subpackage (`social/bluesky/`,
future `social/linkedin/`, etc.) rather than being flattened here, matching
how `integrations.google` groups `mail`/`drive`/`calendar` as siblings
under one namespace.
"""
