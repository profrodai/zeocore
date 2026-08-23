"""
Explicit plugin loading: discover without instantiating, then load by id.

Importing ``zeo_core.modules`` has no side effects. Call
``list_available_entry_points`` / ``load_enabled_entry_points`` yourself.

Run:

    python examples/explicit_plugin_loading_example.py
"""

from __future__ import annotations

from zeo_core.modules import (
    list_available_entry_points,
    load_enabled_entry_points,
    registry,
)


def main() -> None:
    registry.clear()
    print("registry before discovery:", len(registry.list_ids()))

    available = list_available_entry_points()
    print(f"discovered {len(available)} entry points:")
    for ep in available[:8]:
        print(f"  - {ep.plugin_id} ({ep.value})")
    if len(available) > 8:
        print(f"  ... {len(available) - 8} more")
    print("registry after discovery:", len(registry.list_ids()))

    enabled = ["fs", "paths", "config"]
    print("\nloading:", enabled)
    result = load_enabled_entry_points(
        enabled=enabled, strict=True, auto_register=True
    )
    if result.success:
        print("loaded:", result.loaded)
        for plugin_id in result.loaded:
            plugin = registry.get_plugin(plugin_id)
            if plugin is None:
                print(f"  - {plugin_id}: lookup returned None")
                continue
            name = getattr(plugin, "name", type(plugin).__name__)
            print(f"  - {plugin_id}: {name}")
    else:
        print("errors:", result.errors)

    print("\nstrict mode with a typo:")
    registry.clear()
    typo = load_enabled_entry_points(
        enabled=["fs", "patsss"],
        strict=True,
        auto_register=True,
    )
    print("success:", typo.success, "errors:", typo.errors, "loaded:", typo.loaded)

    print("\nnon-strict mode with a typo:")
    registry.clear()
    relaxed = load_enabled_entry_points(
        enabled=["fs", "patsss"],
        strict=False,
        auto_register=True,
    )
    print(
        "success:",
        relaxed.success,
        "warnings:",
        relaxed.warnings,
        "loaded:",
        relaxed.loaded,
    )


if __name__ == "__main__":
    main()
