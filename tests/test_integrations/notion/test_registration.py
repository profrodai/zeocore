"""Tests that the Notion integration is correctly wired into the plugin
mechanism (entry-points table + loader + registry), per integrations/core's
"real, documented, mature" plugin mechanism (see integrations/core/loader.py,
registry.py) -- the same mechanism github/google.mail/google.drive/pandoc/
llms already use, per this repo's own pyproject.toml
[project.entry-points."zeo_core.integrations"] table.
"""

from importlib.metadata import entry_points

from zeo_core.integrations.core.protocols import IntegrationProtocol
from zeo_core.integrations.core.registry import IntegrationRegistry
from zeo_core.integrations.loader import (
    DEFAULT_ENTRY_GROUP,
    list_available_entry_points,
    load_enabled_entry_points,
)
from zeo_core.integrations.notion import NotionIntegration, create_integration
from zeo_core.integrations.notion.protocols import NotionIntegrationProtocol


class TestEntryPointRegistration:
    """The declarative registration itself (pyproject.toml)."""

    def test_notion_entry_point_is_discoverable(self) -> None:
        eps = entry_points().select(group=DEFAULT_ENTRY_GROUP)
        names = {ep.name for ep in eps}
        assert "notion" in names

    def test_notion_entry_point_resolves_to_create_integration(self) -> None:
        eps = entry_points().select(group=DEFAULT_ENTRY_GROUP)
        notion_ep = next(ep for ep in eps if ep.name == "notion")
        assert notion_ep.value == "zeo_core.integrations.notion:create_integration"

    def test_list_available_entry_points_includes_notion(self) -> None:
        available = list_available_entry_points()
        ids = {item["integration_id"] for item in available}
        assert "notion" in ids


class TestFactoryFunction:
    """create_integration() -- the loader's actual call target."""

    def test_create_integration_returns_notion_integration(self) -> None:
        instance = create_integration()
        assert isinstance(instance, NotionIntegration)

    def test_created_instance_satisfies_integration_protocol(self) -> None:
        instance = create_integration()
        assert isinstance(instance, IntegrationProtocol)

    def test_created_instance_satisfies_notion_protocol(self) -> None:
        instance = create_integration()
        assert isinstance(instance, NotionIntegrationProtocol)

    def test_integration_id_and_name_before_init(self) -> None:
        instance = create_integration()
        assert instance.integration_id == "notion"
        assert instance.name == "Notion"


class TestLoaderIntegration:
    """The explicit loader (integrations/loader.py) actually loading+
    registering `notion` end to end -- this is the real behavioral proof
    that registration works, not just that the entry-point string exists."""

    def test_load_enabled_entry_points_loads_notion_without_initializing(self) -> None:
        registry = IntegrationRegistry()

        report = load_enabled_entry_points(
            registry=registry,
            enabled=["notion"],
            strict=True,
            initialize=False,  # avoid a real network call / token requirement
        )

        assert report.success is True
        assert report.loaded == ["notion"]
        assert report.errors == []
        assert registry.is_registered("notion")

        loaded = registry.get_integration("notion")
        assert isinstance(loaded, NotionIntegration)
