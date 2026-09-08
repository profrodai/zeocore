"""Behavioral boundaries for every supported integration environment."""

from __future__ import annotations

import json
import os
import sys
import tomllib
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from zeo_core.integrations.environment import (
    IntegrationMode,
    managed_path,
    managed_state_dir,
)
from zeo_core.integrations.environments import IntegrationEnvironment
from zeo_core.integrations.environments.catalog import CATALOG


@pytest.mark.parametrize("integration", sorted(CATALOG))
def test_each_integration_selects_only_its_mode_inputs(
    tmp_path: Path, integration: str
) -> None:
    setup = CATALOG[integration]
    inputs = {
        "HOME": str(tmp_path),
        "PATH": os.environ["PATH"],
        "PYTHONPATH": "production-modules",
        "HTTPS_PROXY": "production-proxy",
    }
    for key in setup.variables:
        inputs[key] = "ambient-credential"
        inputs["ZEO_TEST_" + key] = "test-value"
        inputs["ZEO_PRODUCTION_" + key] = "production-value"
    original = dict(inputs)
    for mode in ("test", "production"):
        environment = IntegrationEnvironment(mode, tmp_path, (integration,))
        child = environment.child_environment(inputs)
        assert all(child[key] == mode + "-value" for key in setup.variables)
        assert not any(
            key.startswith(("ZEO_TEST_", "ZEO_PRODUCTION_")) for key in child
        )
        assert "PYTHONPATH" not in child and "HTTPS_PROXY" not in child
        assert child["HOME"] == inputs["HOME"]
        assert child["ZEO_INTEGRATION_MODE"] == mode
    assert inputs == original


def test_missing_test_credentials_never_fall_back(tmp_path: Path) -> None:
    env = IntegrationEnvironment("test", tmp_path, ("kit.marketing",))
    child = env.child_environment(
        {"KIT_API_KEY": "ambient", "ZEO_PRODUCTION_KIT_API_KEY": "production"}
    )
    assert "KIT_API_KEY" not in child
    with pytest.raises(ValueError, match="different credentials"):
        env.child_environment(
            {"ZEO_TEST_KIT_API_KEY": "reused", "ZEO_PRODUCTION_KIT_API_KEY": "reused"}
        )
    assert "NOTION_TOKEN" not in env.child_environment(
        {"ZEO_TEST_NOTION_TOKEN": "other-provider"}
    )


def test_fixture_state_and_credentials_are_separate(tmp_path: Path) -> None:
    fixture = IntegrationEnvironment("test", tmp_path, ("kit.marketing",), "fixture")
    live = IntegrationEnvironment("test", tmp_path, ("kit.marketing",))
    assert fixture.state_dir != live.state_dir
    assert "KIT_API_KEY" not in fixture.child_environment(
        {"ZEO_TEST_KIT_API_KEY": "test-secret"}
    )
    with pytest.raises(ValueError, match="Fixture"):
        IntegrationEnvironment("production", tmp_path, ("kit.marketing",), "fixture")


def test_prepare_is_idempotent_and_preserves_user_config(tmp_path: Path) -> None:
    env = IntegrationEnvironment("test", tmp_path, ("notion",))
    env.prepare()
    config = env.state_dir / "config" / "integrations.yaml"
    config.write_text("notion: {timeout_ms: 12345}\n")
    env.prepare()
    assert config.read_text() == "notion: {timeout_ms: 12345}\n"
    if os.name != "nt":
        assert config.stat().st_mode & 0o777 == 0o600
    prod = IntegrationEnvironment("production", tmp_path, ("notion",))
    prod.prepare()
    assert (prod.state_dir / "config" / "integrations.yaml").read_text() == "{}\n"


@pytest.mark.parametrize("alias", ["mode", "work", "config"])
def test_symlinks_cannot_join_modes(tmp_path: Path, alias: str) -> None:
    prod = tmp_path / "production"
    prod.mkdir()
    test = tmp_path / "test"
    if alias == "mode":
        test.symlink_to(prod, target_is_directory=True)
    else:
        test.mkdir()
        (test / alias).symlink_to(prod, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        IntegrationEnvironment("test", tmp_path, ("notion",)).prepare()


def activate(
    monkeypatch: pytest.MonkeyPatch, environment: IntegrationEnvironment
) -> None:
    environment.prepare()
    for key, value in environment.child_environment({}).items():
        monkeypatch.setenv(key, value)


def test_config_loading_uses_actual_selected_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from zeo_core.integrations.notion.config import NotionConfigProvider

    env = IntegrationEnvironment("test", tmp_path, ("notion",))
    activate(monkeypatch, env)
    monkeypatch.setenv("NOTION_TOKEN", "test-only")
    (env.state_dir / "config" / "integrations.yaml").write_text(
        "notion: {timeout_ms: 12345}\n"
    )
    monkeypatch.setenv("ZEO_NOTION_CONFIG", str(tmp_path / "production.yaml"))
    result = NotionConfigProvider().load_config()
    assert result.success and result.content and result.content["timeout_ms"] == 12345
    with pytest.raises(ValueError, match="inside"):
        managed_path(str(tmp_path / "production.yaml"))


def test_google_and_bluesky_never_migrate_ambient_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from zeo_core.integrations.google import credential_paths as google
    from zeo_core.integrations.social.bluesky import credential_paths as bluesky

    env = IntegrationEnvironment("test", tmp_path, ("google.drive", "social.bluesky"))
    activate(monkeypatch, env)
    monkeypatch.setattr(
        google,
        "migrate_one_shot",
        MagicMock(side_effect=AssertionError("must not read ambient files")),
    )
    assert Path(google.resolve_credentials_path()).is_relative_to(env.state_dir)
    assert Path(google.resolve_client_secret_path()).is_relative_to(env.state_dir)
    assert Path(bluesky.default_credentials_path()).is_relative_to(env.state_dir)
    outside = tmp_path / "production" / "token.json"
    with pytest.raises(ValueError, match="inside"):
        google.resolve_credentials_path(str(outside))
    inside = env.state_dir / "credentials" / "alias.json"
    inside.symlink_to(outside)
    with pytest.raises(ValueError, match="inside"):
        google.resolve_client_secret_path(str(inside))


def test_keychain_custody_is_separate_for_modes_and_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from zeo_core.integrations.hosted.pairing import KeychainSecureSessionStore

    services = []
    cases: tuple[tuple[Path, IntegrationMode], ...] = (
        (tmp_path, "test"),
        (tmp_path, "production"),
        (tmp_path / "other", "test"),
    )
    for root, mode in cases:
        env = IntegrationEnvironment(mode, root, ("zeoconnect",))
        activate(monkeypatch, env)
        runner = MagicMock()
        runner.run.return_value.returncode = 44
        store = KeychainSecureSessionStore(runner=runner)
        assert store.load() is None
        args = runner.run.call_args.args[0]
        services.append(args[args.index("-s") + 1])
    assert len(set(services)) == 3


@pytest.mark.parametrize("module", ["service", "service.integration"])
@pytest.mark.parametrize("mode", ["test", "production"])
def test_managed_llm_never_falls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: IntegrationMode, module: str
) -> None:
    from importlib import import_module

    integration_class = import_module(
        "zeo_core.integrations.llms." + module
    ).LLMIntegration
    from zeo_core.integrations.llms.service import managed

    activate(monkeypatch, IntegrationEnvironment(mode, tmp_path, ("llms",)))
    failing = MagicMock(side_effect=RuntimeError("provider-secret"))
    monkeypatch.setattr(managed, "get_llm_client", failing)
    client = integration_class(
        provider="openai", api_key="selected-key", enable_fallback=True
    )
    result = client.initialize()
    assert not result.success and not client.is_available() and client.client is None
    assert "provider-secret" not in str(result) and "selected-key" not in str(result)
    assert failing.call_count == 1 and failing.call_args.kwargs["provider"] == "openai"
    assert not integration_class(provider="mock").initialize().success


def test_managed_mock_must_be_explicit_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from zeo_core.integrations.llms.service import LLMIntegration

    activate(
        monkeypatch, IntegrationEnvironment("test", tmp_path, ("llms",), "fixture")
    )
    assert not LLMIntegration(provider="openai", api_key="key").initialize().success
    client = LLMIntegration(provider="mock")
    assert client.initialize().success and client.is_using_mock
    result = client.chat([{"role": "user", "content": "hello"}])
    assert result.success and result.content


def test_mode_is_required_when_state_is_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ZEO_INTEGRATION_MODE", raising=False)
    monkeypatch.setenv("ZEO_INTEGRATION_STATE_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="Incomplete"):
        managed_state_dir()


def test_child_application_exercises_kit_and_separates_outputs(tmp_path: Path) -> None:
    # Actual separate interpreters, real client serialization and transport dispatch.
    script = r"""
import json, os
from pathlib import Path
import httpx
from pydantic import SecretStr
from zeo_core.integrations.kit import KitClient, KitTransport
mode = os.environ['ZEO_INTEGRATION_MODE']
assert os.environ['KIT_API_KEY'] == mode + '-credential'
assert 'HUBSPOT_ACCESS_TOKEN' not in os.environ
calls = []
def provider(request):
    calls.append(request)
    assert request.headers['X-Kit-Api-Key'] == mode + '-credential'
    return httpx.Response(200, json={
        'broadcasts': [],
        'pagination': {'has_next_page': False, 'has_previous_page': False},
    })
client = KitClient(transport=KitTransport(
    SecretStr(os.environ['KIT_API_KEY']), transport=httpx.MockTransport(provider)
))
try:
    assert client.list_broadcasts().results == []
    assert len(calls) == 1 and calls[0].method == 'GET'
    Path('receipt.json').write_text(json.dumps({'mode': mode, 'calls': len(calls)}))
finally:
    client.close()
"""
    source = {
        "PATH": os.environ["PATH"],
        "ZEO_TEST_KIT_API_KEY": "test-credential",
        "ZEO_PRODUCTION_KIT_API_KEY": "production-credential",
        "KIT_API_KEY": "wrong-ambient",
        "HUBSPOT_ACCESS_TOKEN": "wrong-other",
    }
    for mode in ("test", "production"):
        env = IntegrationEnvironment(mode, tmp_path, ("kit.marketing",))
        assert env.run([sys.executable, "-c", script], source=source) == 0
        assert json.loads((env.work_dir / "receipt.json").read_text()) == {
            "mode": mode,
            "calls": 1,
        }
    env = IntegrationEnvironment("test", tmp_path, ("kit.marketing",))
    assert env.run([sys.executable, "-c", "raise SystemExit(7)"], source=source) == 7
    assert (
        json.loads((tmp_path / "production" / "work" / "receipt.json").read_text())[
            "mode"
        ]
        == "production"
    )


def test_inventory_covers_every_shipped_entry_point() -> None:
    root = Path(__file__).resolve().parents[2]
    config = tomllib.loads((root / "pyproject.toml").read_text())
    assert set(config["project"]["entry-points"]["zeo_core.integrations"]) == {
        name for name, setup in CATALOG.items() if setup.entry_point
    }


@pytest.mark.parametrize("integration", sorted(CATALOG))
def test_setup_catalog_links_to_complete_account_tracks(integration: str) -> None:
    root = Path(__file__).resolve().parents[2]
    guide = root / "docs" / "integrations" / CATALOG[integration].guide
    content = guide.read_text()
    assert "## " in content and "test" in content.lower()
    assert "production" in content.lower() and "E2E" in content
    assert "environments.md" in content


def test_cli_prepare_and_command_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from zeo_core.integrations.environments import __main__ as cli

    args = ["--mode", "test", "--root", str(tmp_path), "--integration", "kit.marketing"]
    prompt = MagicMock(side_effect=AssertionError("must not prompt"))
    monkeypatch.setattr(cli.getpass, "getpass", prompt)
    assert cli.main([*args, "--prepare"]) == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "test"
    for suffix in (
        [],
        ["--secret", "KIT_API_KEY"],
        ["--prepare", "--", "app"],
        ["--fixture", "--secret", "KIT_API_KEY", "--", "app"],
        ["--secret", "NOTION_TOKEN", "--", "app"],
    ):
        with pytest.raises(SystemExit) as exc:
            cli.main([*args, *suffix])
        assert exc.value.code == 2
    prompt.assert_not_called()


def test_cli_secret_is_scoped_private_and_not_persisted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from zeo_core.integrations.environments import __main__ as cli

    args = [
        "--mode",
        "test",
        "--root",
        str(tmp_path),
        "--integration",
        "kit.marketing",
        "--secret",
        "KIT_API_KEY",
        "--",
        "application",
    ]
    monkeypatch.delenv("ZEO_TEST_KIT_API_KEY", raising=False)
    prompt = MagicMock(return_value="private-test-secret")
    run = MagicMock(return_value=7)
    monkeypatch.setattr(cli.getpass, "getpass", prompt)
    monkeypatch.setattr(IntegrationEnvironment, "run", run)
    assert cli.main(args) == 7
    assert (
        run.call_args.kwargs["source"]["ZEO_TEST_KIT_API_KEY"] == "private-test-secret"
    )
    assert "ZEO_TEST_KIT_API_KEY" not in os.environ
    captured = capsys.readouterr()
    assert "private-test-secret" not in captured.out + captured.err
    assert list(tmp_path.iterdir()) == []
    monkeypatch.setenv("ZEO_TEST_KIT_API_KEY", "ci-test-secret")
    assert cli.main(args) == 7
    assert prompt.call_count == 1
    assert run.call_args.kwargs["source"]["ZEO_TEST_KIT_API_KEY"] == "ci-test-secret"


@pytest.mark.parametrize("failure", ["empty", "eof", "insecure"])
def test_cli_secret_prompt_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    import warnings

    from zeo_core.integrations.environments import __main__ as cli

    def prompt(_message: str) -> str:
        if failure == "eof":
            raise EOFError
        if failure == "insecure":
            warnings.warn(
                "terminal cannot hide input", cli.getpass.GetPassWarning, stacklevel=2
            )
        return ""

    monkeypatch.delenv("ZEO_TEST_KIT_API_KEY", raising=False)
    monkeypatch.setattr(cli.getpass, "getpass", prompt)
    run = MagicMock()
    monkeypatch.setattr(IntegrationEnvironment, "run", run)
    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "--mode",
                "test",
                "--root",
                str(tmp_path),
                "--integration",
                "kit.marketing",
                "--secret",
                "KIT_API_KEY",
                "--",
                "application",
            ]
        )
    assert exc.value.code == 2
    run.assert_not_called()


def test_missing_managed_llm_key_does_not_probe_other_services(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from zeo_core.integrations.llms import service
    from zeo_core.integrations.llms.service import managed

    activate(monkeypatch, IntegrationEnvironment("test", tmp_path, ("llms",)))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    probe = MagicMock(side_effect=AssertionError("unexpected dependency probing"))
    factory = MagicMock(side_effect=AssertionError("unexpected client construction"))
    monkeypatch.setattr(service, "check_llm_dependencies", probe)
    monkeypatch.setattr(managed, "get_llm_client", factory)
    result = service.LLMIntegration(provider="openai").initialize()
    assert not result.success
    probe.assert_not_called()
    factory.assert_not_called()


def test_documented_jupytext_example_runs_in_both_modes(tmp_path: Path) -> None:
    import re

    root = Path(__file__).resolve().parents[2]
    guide = (root / "docs" / "integrations" / "local-tools.md").read_text()
    section = guide.split("## Jupytext\n", 1)[1].split("## Production", 1)[0]
    match = re.search(r"```python\n(.*?)\n```", section, re.S)
    assert match
    for mode in ("test", "production"):
        env = IntegrationEnvironment(mode, tmp_path, ("jupytext",))
        assert env.run([sys.executable, "-c", match[1]]) == 0
        assert (env.work_dir / "probe.ipynb").is_file()
        assert "value = 2 + 3" in (env.work_dir / "roundtrip.py").read_text()
