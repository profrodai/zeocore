"""Tests for NotionIntegration (service.py) -- the orchestration layer.

Mirrors github/test_service.py's pattern: a mocked ConfigProviderProtocol,
a mocked AuthProviderProtocol (or a config-supplied token), and a mocked
NotionClient injected after initialize() so no real network/token is used.
"""

from unittest.mock import MagicMock

import pytest

from zeo_core.integrations.core.results import ConfigResult, IntegrationResult
from zeo_core.integrations.notion.client import NotionClient
from zeo_core.integrations.notion.models import NotionBlock, NotionDatabase, NotionPage
from zeo_core.integrations.notion.service import NotionIntegration


@pytest.fixture
def mock_config_provider() -> MagicMock:
    provider = MagicMock()
    provider.load_config.return_value = ConfigResult.success_result(
        content={"token": "config_token", "timeout_ms": 60_000, "max_retries": 3},
    )
    return provider


@pytest.fixture
def integration(
    mock_config_provider: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> NotionIntegration:
    """A NotionIntegration wired to a process-local fake environment token."""
    monkeypatch.setenv("NOTION_TOKEN", "test-only-token")
    fake_client = NotionClient("test-only-token", sdk_client=MagicMock())
    client_factory = MagicMock(return_value=fake_client)
    svc = NotionIntegration(
        config_provider=mock_config_provider,
        auth_provider=None,
        client_factory=client_factory,
    )
    result = svc.initialize()
    assert result.success is True
    client_factory.assert_called_once_with(
        token="test-only-token",  # noqa: S106 -- inert SDK-double fixture
        timeout_ms=60_000,
        max_retries=3,
    )
    return svc


class TestNotionIntegrationLifecycle:
    """Initialization / availability behavior."""

    def test_name_and_version(self, integration: NotionIntegration) -> None:
        assert integration.name == "Notion"
        assert integration.version == "1.0.0"
        assert integration.integration_id == "notion"

    def test_is_available_after_init(self, integration: NotionIntegration) -> None:
        assert integration.is_available() is True

    def test_not_available_before_init(self, mock_config_provider: MagicMock) -> None:
        svc = NotionIntegration(config_provider=mock_config_provider)
        assert svc.is_available() is False

    def test_methods_error_before_init(self, mock_config_provider: MagicMock) -> None:
        svc = NotionIntegration(config_provider=mock_config_provider)
        result = svc.get_page("page-1")

        assert result.success is False
        assert result.error is not None
        assert "not initialized" in result.error.lower()

    def test_initialize_no_token_anywhere(self) -> None:
        provider = MagicMock()
        provider.load_config.return_value = ConfigResult.success_result(content={})
        svc = NotionIntegration(config_provider=provider, auth_provider=None)

        result = svc.initialize()

        assert result.success is False
        assert result.error is not None
        assert "token" in result.error.lower()

    def test_initialize_config_load_failure(self) -> None:
        provider = MagicMock()
        provider.load_config.side_effect = RuntimeError("config broke")
        svc = NotionIntegration(config_provider=provider, auth_provider=None)

        result = svc.initialize()

        assert result.success is False

    def test_auth_provider_arg_is_deliberately_discarded(self) -> None:
        """NotionIntegration mirrors GitHubIntegration's own documented
        contract exactly (see github/test_service.py's
        test_init_with_default_providers: "We no longer auto-create an
        auth_provider... service.auth_provider is None"): the constructor
        accepts an auth_provider for API-compat but always passes
        auth_provider=None to BaseIntegrationService.__init__, so
        self.auth_provider is None regardless of what was passed in. The
        real, sole auth path is "token in config" (config's own
        _extract_config already falls back to the NOTION_TOKEN env var).
        Not a bug in this port -- ported byte-for-byte on purpose,
        Chesterton's-fence per CLAUDE.md s7."""
        auth_provider = MagicMock()
        svc = NotionIntegration(auth_provider=auth_provider)

        assert svc.auth_provider is None

    def test_initialize_no_token_in_config_fails_even_with_auth_provider(
        self,
    ) -> None:
        """Consequence of the above: initialize() fails when config has no
        token, even if a caller passed an auth_provider -- matches
        GitHubIntegration's identical behavior for the identical reason."""
        config_provider = MagicMock()
        config_provider.load_config.return_value = ConfigResult.success_result(
            content={}
        )
        auth_provider = MagicMock()
        auth_provider.get_credentials.return_value = {"token": "auth_provider_token"}

        svc = NotionIntegration(
            config_provider=config_provider, auth_provider=auth_provider
        )
        result = svc.initialize()

        assert result.success is False
        assert result.error is not None
        assert "token" in result.error.lower()


class TestNotionIntegrationRead:
    """Read-surface tests against the service layer, mocked client."""

    def test_get_page_success(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.get_page.return_value = NotionPage(id="page-1")
        integration.client = fake_client

        result = integration.get_page("page-1")

        assert isinstance(result, IntegrationResult)
        assert result.success is True
        assert result.content is not None
        assert result.content.id == "page-1"
        fake_client.get_page.assert_called_once_with("page-1")

    def test_get_page_error_wrapped(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.get_page.side_effect = RuntimeError("not found")
        integration.client = fake_client

        result = integration.get_page("missing")

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error

    def test_list_page_blocks(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.list_page_blocks.return_value = (
            [NotionBlock(id="b1", type="paragraph")],
            None,
        )
        integration.client = fake_client

        result = integration.list_page_blocks("page-1")

        assert result.success is True
        assert result.content is not None
        assert len(result.content) == 1

    def test_search(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.search.return_value = [{"id": "page-1", "object": "page"}]
        integration.client = fake_client

        result = integration.search(query="hello")

        assert result.success is True
        assert result.content == [{"id": "page-1", "object": "page"}]

    def test_get_database(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.get_database.return_value = NotionDatabase(id="db-1", title="Tasks")
        integration.client = fake_client

        result = integration.get_database("db-1")

        assert result.success is True
        assert result.content is not None
        assert result.content.title == "Tasks"

    def test_query_database_with_filter(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.query_database.return_value = ([NotionPage(id="page-1")], None)
        integration.client = fake_client

        filter_obj = {"property": "Status", "select": {"equals": "Done"}}
        result = integration.query_database("db-1", filter=filter_obj)

        assert result.success is True
        assert result.content is not None
        assert len(result.content) == 1
        fake_client.query_database.assert_called_once_with(
            "db-1", filter=filter_obj, sorts=None, page_size=100
        )

    def test_query_database_error_wrapped(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.query_database.side_effect = RuntimeError("no data source")
        integration.client = fake_client

        result = integration.query_database("db-1")

        assert result.success is False
        assert result.error is not None


class TestNotionIntegrationWrite:
    """Write-surface tests against the service layer -- the operator's ask."""

    def test_create_page(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.create_page.return_value = NotionPage(id="new-page")
        integration.client = fake_client

        parent = {"type": "page_id", "page_id": "parent-1"}
        properties = {"title": [{"text": {"content": "New"}}]}
        result = integration.create_page(parent=parent, properties=properties)

        assert result.success is True
        assert result.content is not None
        assert result.content.id == "new-page"
        fake_client.create_page.assert_called_once_with(
            parent=parent, properties=properties, children=None
        )

    def test_create_page_error_wrapped(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.create_page.side_effect = RuntimeError("validation_error")
        integration.client = fake_client

        result = integration.create_page(parent={}, properties={})

        assert result.success is False
        assert result.error is not None
        assert "validation_error" in result.error

    def test_create_database_entry(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.create_database_entry.return_value = NotionPage(id="entry-1")
        integration.client = fake_client

        properties = {"Name": {"title": [{"text": {"content": "Task"}}]}}
        result = integration.create_database_entry("db-1", properties=properties)

        assert result.success is True
        assert result.content is not None
        assert result.content.id == "entry-1"
        fake_client.create_database_entry.assert_called_once_with(
            database_id="db-1", properties=properties, children=None
        )

    def test_update_page(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.update_page.return_value = NotionPage(id="page-1")
        integration.client = fake_client

        result = integration.update_page(
            "page-1", properties={"Status": {"select": {"name": "Done"}}}
        )

        assert result.success is True
        assert result.content is not None

    def test_append_blocks(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.append_blocks.return_value = [
            NotionBlock(id="new-block", type="paragraph")
        ]
        integration.client = fake_client

        children = [{"object": "block", "type": "paragraph"}]
        result = integration.append_blocks("page-1", children=children)

        assert result.success is True
        assert result.content is not None
        assert len(result.content) == 1
        fake_client.append_blocks.assert_called_once_with(
            block_id="page-1", children=children
        )

    def test_append_blocks_error_wrapped(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.append_blocks.side_effect = RuntimeError("rate_limited")
        integration.client = fake_client

        result = integration.append_blocks("page-1", children=[])

        assert result.success is False
        assert result.error is not None
        assert "rate_limited" in result.error


class TestNotionIntegrationClientNoneGuard:
    """The mypy-narrowing guard: every method must also handle client=None
    defensively even though _ensure_initialized should prevent it in
    practice (matches GitHubIntegration's own identical guard everywhere).
    Exercised across all 9 public methods, not just get_page, so each
    method's own guard line is actually covered rather than assumed
    identical by inspection."""

    def test_get_page_client_none(self, integration: NotionIntegration) -> None:
        integration.client = None
        integration._initialized = True

        result = integration.get_page("page-1")

        assert result.success is False
        assert result.error is not None
        assert "not initialized" in result.error.lower()

    def test_list_page_blocks_client_none(self, integration: NotionIntegration) -> None:
        integration.client = None
        integration._initialized = True

        result = integration.list_page_blocks("page-1")

        assert result.success is False
        assert result.error is not None
        assert "not initialized" in result.error.lower()

    def test_search_client_none(self, integration: NotionIntegration) -> None:
        integration.client = None
        integration._initialized = True

        result = integration.search()

        assert result.success is False
        assert result.error is not None

    def test_get_database_client_none(self, integration: NotionIntegration) -> None:
        integration.client = None
        integration._initialized = True

        result = integration.get_database("db-1")

        assert result.success is False
        assert result.error is not None

    def test_query_database_client_none(self, integration: NotionIntegration) -> None:
        integration.client = None
        integration._initialized = True

        result = integration.query_database("db-1")

        assert result.success is False
        assert result.error is not None

    def test_create_page_client_none(self, integration: NotionIntegration) -> None:
        integration.client = None
        integration._initialized = True

        result = integration.create_page(parent={}, properties={})

        assert result.success is False
        assert result.error is not None

    def test_create_database_entry_client_none(
        self, integration: NotionIntegration
    ) -> None:
        integration.client = None
        integration._initialized = True

        result = integration.create_database_entry("db-1", properties={})

        assert result.success is False
        assert result.error is not None

    def test_update_page_client_none(self, integration: NotionIntegration) -> None:
        integration.client = None
        integration._initialized = True

        result = integration.update_page("page-1")

        assert result.success is False
        assert result.error is not None

    def test_append_blocks_client_none(self, integration: NotionIntegration) -> None:
        integration.client = None
        integration._initialized = True

        result = integration.append_blocks("page-1", children=[])

        assert result.success is False
        assert result.error is not None


class TestNotionIntegrationRemainingErrorBranches:
    """The remaining reachable exception-wrapped branches per method (not
    yet exercised above) and the has-more-results pagination message
    branches -- closes the rest of the real, reachable gap between
    service.py's line count and this file's coverage."""

    def test_list_page_blocks_more_results_message(
        self, integration: NotionIntegration
    ) -> None:
        fake_client = MagicMock()
        fake_client.list_page_blocks.return_value = (
            [NotionBlock(id="b1", type="paragraph")],
            "cursor-2",
        )
        integration.client = fake_client

        result = integration.list_page_blocks("page-1")

        assert result.success is True
        assert result.message is not None
        assert "more results available" in result.message

    def test_list_page_blocks_error_wrapped(
        self, integration: NotionIntegration
    ) -> None:
        fake_client = MagicMock()
        fake_client.list_page_blocks.side_effect = RuntimeError("boom")
        integration.client = fake_client

        result = integration.list_page_blocks("page-1")

        assert result.success is False
        assert result.error is not None
        assert "boom" in result.error

    def test_search_error_wrapped(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.search.side_effect = RuntimeError("search failed")
        integration.client = fake_client

        result = integration.search(query="x")

        assert result.success is False
        assert result.error is not None
        assert "search failed" in result.error

    def test_get_database_error_wrapped(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.get_database.side_effect = RuntimeError("object_not_found")
        integration.client = fake_client

        result = integration.get_database("missing-db")

        assert result.success is False
        assert result.error is not None
        assert "object_not_found" in result.error

    def test_query_database_more_results_message(
        self, integration: NotionIntegration
    ) -> None:
        fake_client = MagicMock()
        fake_client.query_database.return_value = (
            [NotionPage(id="page-1")],
            "cursor-2",
        )
        integration.client = fake_client

        result = integration.query_database("db-1")

        assert result.success is True
        assert result.message is not None
        assert "more results available" in result.message

    def test_create_database_entry_error_wrapped(
        self, integration: NotionIntegration
    ) -> None:
        fake_client = MagicMock()
        fake_client.create_database_entry.side_effect = RuntimeError("no_data_source")
        integration.client = fake_client

        result = integration.create_database_entry("db-1", properties={})

        assert result.success is False
        assert result.error is not None
        assert "no_data_source" in result.error

    def test_update_page_error_wrapped(self, integration: NotionIntegration) -> None:
        fake_client = MagicMock()
        fake_client.update_page.side_effect = RuntimeError("conflict_error")
        integration.client = fake_client

        result = integration.update_page("page-1", archived=True)

        assert result.success is False
        assert result.error is not None
        assert "conflict_error" in result.error

    # NOTE: _check_config_available's own except-Exception branch
    # (service.py lines 101-106) requires self.config's *access* to raise,
    # not merely be None -- unreachable for a plain dict | None attribute
    # without a contrived subclass. GitHubIntegration's structurally
    # identical branch (github/service.py lines 95-98) is equally
    # untested in that integration's own suite for the same reason;
    # left undocumented-but-real here rather than covered by a fabricated
    # trigger, matching that precedent (CLAUDE.md s7: don't force a
    # circle-of-control fix/workaround for a pattern shared by the
    # template this integration was built from).
