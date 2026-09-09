"""Regressions for the four observed legacy registration failures."""

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from zeo_core.modules import discovery
from zeo_core.modules.protocols import CommandPluginProtocol, ZeoPluginMetadata
from zeo_core.modules.registry import PluginRegistry


class Commands(CommandPluginProtocol):
    def __init__(self, identity: str) -> None:
        self.identity = identity
        self.broken = False
        self.enumerations = 0

    @property
    def plugin_id(self) -> str:
        return self.identity

    @property
    def name(self) -> str:
        return self.identity

    def get_metadata(self) -> ZeoPluginMetadata:
        return ZeoPluginMetadata(
            plugin_id=self.identity,
            name=self.identity,
            version="1.0.0",
            description="Registration regression fixture",
        )

    def list_commands(self) -> list[str]:
        self.enumerations += 1
        if self.broken:
            raise ValueError("command enumeration failed")
        return ["shared"]

    def get_command(self, name: str) -> Callable[..., str]:
        return lambda: self.identity

    def execute_command(self, name: str, *args: object, **kwargs: object) -> str:
        return self.identity


@dataclass
class Entry:
    name: str
    factory: Callable[[], Commands]
    value: str = "owned.fixture:factory"

    def load(self) -> Callable[[], Commands]:
        return self.factory


def test_failed_enumeration_leaves_no_partial_registration() -> None:
    registry = PluginRegistry()
    good, bad = Commands("good"), Commands("bad")
    registry.register(good)
    bad.broken = True
    with pytest.raises(ValueError):
        registry.register(bad)
    assert registry.list_ids() == ["good"]
    assert registry.list_command_plugins() == ["good"]
    assert registry.execute_command("shared") == "good"


@pytest.mark.parametrize("order", [("a", "b", "c"), ("c", "a", "b"), ("b", "c", "a")])
def test_arbitrary_unload_order_restores_surviving_owner(
    order: tuple[str, ...],
) -> None:
    registry = PluginRegistry()
    plugins = {name: Commands(name) for name in ("a", "b", "c")}
    for plugin in plugins.values():
        registry.register(plugin)
        plugin.broken = True  # unload must use the registered snapshot
    survivors = list(plugins)
    for name in order:
        registry.unregister(name)
        survivors.remove(name)
        if survivors:
            assert registry.execute_command("shared") == survivors[-1]
        else:
            assert registry.list_commands() == []
    assert all(plugin.enumerations == 1 for plugin in plugins.values())


def test_strict_load_failure_restores_preexisting_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from importlib import import_module

    registry_module = import_module("zeo_core.modules.registry")

    registry = PluginRegistry()
    old, good, bad = Commands("old"), Commands("good"), Commands("bad")
    registry.register(old)
    bad.broken = True
    monkeypatch.setattr(registry_module, "registry", registry)
    monkeypatch.setattr(
        discovery,
        "entry_points",
        lambda **_: [Entry("good", lambda: good), Entry("bad", lambda: bad)],
    )
    result = discovery.PluginLoader().load_enabled_entry_points(
        ["good", "bad"], strict=True
    )
    assert not result.success
    assert not result.loaded
    assert result.errors
    assert registry.list_ids() == ["old"]
    assert registry.execute_command("shared") == "old"


@pytest.mark.parametrize("strict", [True, False])
def test_duplicate_entry_point_refuses_before_either_import(
    monkeypatch: pytest.MonkeyPatch, strict: bool
) -> None:
    def forbidden() -> Commands:
        pytest.fail("ambiguous factory must not be loaded")

    monkeypatch.setattr(
        discovery,
        "entry_points",
        lambda **_: [Entry("same", forbidden), Entry("same", forbidden)],
    )
    result = discovery.PluginLoader().load_enabled_entry_points(["same"], strict=strict)
    assert not result.success
    assert not result.loaded
    assert "Ambiguous" in result.errors[0]


def test_duplicate_unselected_name_does_not_load_or_block_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        discovery,
        "entry_points",
        lambda **_: [
            Entry("same", lambda: Commands("same")),
            Entry("same", lambda: Commands("same")),
            Entry("selected", lambda: Commands("selected")),
        ],
    )
    result = discovery.PluginLoader().load_enabled_entry_points(
        ["selected"], auto_register=False
    )
    assert result.success
    assert result.loaded == ["selected"]
