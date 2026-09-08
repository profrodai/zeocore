"""Credentials, effects, canonical tool wiring, bounded reads and error privacy."""

from __future__ import annotations

import importlib.metadata
import logging
from unittest.mock import Mock

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from zeo_core.adapters.llm_tools import project_openai_tool
from zeo_core.contracts import EffectKind
from zeo_core.integrations.core.protocols import IntegrationProtocol
from zeo_core.integrations.kit import (
    KitAPIError,
    KitIntegration,
    KitTransport,
    Record,
    create_integration,
)
from zeo_core.tools import CapabilityRegistry, ToolContext, invoke_sync
from zeo_core.tools.builtin.hubspot import register_capabilities as register_hubspot
from zeo_core.tools.builtin.kit import ReadRequest, register_capabilities

from .conftest import CANARY, CONTRACT, ClientFixture, upstream


def context(service: KitIntegration | None = None) -> ToolContext:
    return ToolContext(
        run_id="kit-test",
        tool_name="kit",
        tool_version="1.0.0",
        logger=None,
        fs=None,
        work_dir=".",
        output_dir=".",
        services={"kit.marketing": service} if service else {},
    )


def test_provider_capabilities_coexist_and_all_project() -> None:
    registry = CapabilityRegistry()
    register_hubspot(registry)
    register_capabilities(registry)
    manifests = list(registry.manifests())
    assert len(manifests) == 24
    for manifest in manifests:
        projection = project_openai_tool(manifest)
        assert projection.ok, projection.incompatibility
    for name in [
        "broadcast.send",
        "sequence.email.publish",
        "sequence.state",
        "sequence.enroll",
        "subscriber.create",
        "tag.membership",
    ]:
        assert (
            EffectKind.EXTERNAL_COMMUNICATION
            in registry.get("kit.marketing." + name + "@1.0.0").definition.effects.kinds
        )


@pytest.mark.parametrize(
    "name,method",
    [
        ("broadcast.save", "create_broadcast"),
        ("broadcast.send", "send_broadcast"),
        ("sequence.save", "create_sequence"),
        ("sequence.email.save", "save_sequence_email"),
        ("sequence.email.publish", "publish_sequence_email"),
        ("sequence.state", "set_sequence_active"),
        ("sequence.enroll", "enroll"),
        ("subscriber.create", "create_subscriber"),
        ("subscriber.unsubscribe", "unsubscribe"),
        ("tag.save", "save_tag"),
        ("tag.membership", "set_tag"),
        ("delete", "delete_broadcast"),
    ],
)
def test_effect_capabilities_invoke_real_service_method(
    setup_client: ClientFixture, monkeypatch: pytest.MonkeyPatch, name: str, method: str
) -> None:
    client, _, _ = setup_client
    registry = CapabilityRegistry()
    register_capabilities(registry)
    bound = registry.get("kit.marketing." + name + "@1.0.0")
    spy = Mock(return_value=Record(data={"id": 42}))
    monkeypatch.setattr(client, method, spy)
    result = invoke_sync(
        bound,
        bound.request_model.model_validate(bound.definition.examples[0].request),
        context(KitIntegration(client)),
    )
    assert result.status == "success", result
    spy.assert_called_once()
    assert result.data is not None and result.data.data == {"id": 42}


@pytest.mark.parametrize(
    "operation,path,key",
    [
        ("account", "/v4/account", None),
        ("account_metrics", "/v4/account/email_stats", None),
        ("broadcasts", "/v4/broadcasts", None),
        ("broadcast", "/v4/broadcasts/{id}", "broadcast"),
        ("broadcast_metrics", "/v4/broadcasts/{broadcast_id}/stats", "broadcast"),
        ("broadcast_clicks", "/v4/broadcasts/{broadcast_id}/clicks", None),
        ("templates", "/v4/email_templates", None),
        ("segments", "/v4/segments", None),
        ("sequences", "/v4/sequences", None),
        ("sequence", "/v4/sequences/{id}", "sequence"),
        ("sequence_metrics", "/v4/sequences/{id}", "sequence"),
        ("sequence_emails", "/v4/sequences/{sequence_id}/emails", None),
        ("sequence_email", "/v4/sequences/{sequence_id}/emails/{id}", "email"),
        ("sequence_subscribers", "/v4/sequences/{sequence_id}/subscribers", None),
        ("subscribers", "/v4/subscribers", None),
        ("subscriber", "/v4/subscribers/{id}", "subscriber"),
        ("subscriber_tags", "/v4/subscribers/{subscriber_id}/tags", None),
        ("tags", "/v4/tags", None),
        ("tag_subscribers", "/v4/tags/{tag_id}/subscribers", None),
    ],
)
def test_reads_flow_from_capability_to_upstream_route(
    setup_client: ClientFixture, operation: str, path: str, key: str | None
) -> None:
    client, calls, responses = setup_client
    data = upstream(path)
    rid = data[key].get("id", 23) if key else 23
    responses.append(httpx.Response(200, json=data))
    registry = CapabilityRegistry()
    register_capabilities(registry)
    result = invoke_sync(
        registry.get("kit.marketing.read@1.0.0"),
        ReadRequest(operation=operation, resource_id=rid, sequence_id=23),
        context(KitIntegration(client)),
    )
    assert result.status == "success", result
    assert result.data is not None
    assert calls[-1].method == "GET"
    assert calls[-1].url.path == path.replace("{id}", str(rid)).replace(
        "{broadcast_id}", str(rid)
    ).replace("{sequence_id}", "23").replace("{subscriber_id}", str(rid)).replace(
        "{tag_id}", str(rid)
    )


def test_tool_errors_do_not_expose_provider_body(setup_client: ClientFixture) -> None:
    client, _, responses = setup_client
    registry = CapabilityRegistry()
    register_capabilities(registry)
    bound = registry.get("kit.marketing.read@1.0.0")
    request = ReadRequest(operation="account")
    assert invoke_sync(bound, request, context()).status == "error"
    responses.append(
        httpx.Response(401, json={"errors": [CANARY, "reader@example.com"]})
    )
    result = invoke_sync(bound, request, context(KitIntegration(client)))
    assert result.status == "error" and CANARY not in str(result)
    assert "reader@example.com" not in str(result)


@pytest.mark.parametrize(
    "method,status,unknown",
    [
        ("GET", 500, False),
        ("POST", 503, True),
        ("POST", 401, False),
        ("POST", 403, False),
        ("POST", 404, False),
        ("POST", 429, False),
        ("POST", 302, False),
    ],
)
def test_http_failures_are_safe_and_never_retried(
    method: str, status: int, unknown: bool
) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            status,
            text=CANARY,
            headers={"Retry-After": "60", "Location": "https://evil.invalid/" + CANARY},
        )

    transport = KitTransport(SecretStr(CANARY), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(KitAPIError) as error:
            transport.request(method, "/v4/broadcasts")
        assert error.value.outcome_unknown is unknown
        assert error.value.retry_after_seconds == 60
        assert CANARY not in str(error.value)
        assert len(calls) == 1
    finally:
        transport.close()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(201, text="bad-json"),
        httpx.Response(201, json=[]),
        httpx.ReadTimeout("secret-timeout"),
    ],
)
def test_ambiguous_mutation_outcome_is_not_replayed(
    response: httpx.Response | Exception,
) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if isinstance(response, Exception):
            raise response
        return response

    transport = KitTransport(SecretStr(CANARY), transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(KitAPIError) as error:
            transport.request("POST", "/v4/broadcasts", body={})
        assert error.value.outcome_unknown and len(calls) == 1
        assert "secret" not in str(error.value)
    finally:
        transport.close()


@pytest.mark.parametrize(
    "path,method",
    [
        ("https://evil.invalid/v4/account", "GET"),
        ("/v4/purchases", "POST"),
        ("/v4/broadcasts/../subscribers", "GET"),
        ("/v4/broadcasts/%2e%2e/subscribers", "GET"),
        ("/v4/account?key=secret", "GET"),
        ("/v4/sequences/1/subscribers/2", "DELETE"),
        ("/v4/subscribers/2", "PUT"),
    ],
)
def test_route_boundary_excludes_undocumented_or_nonmarketing_operations(
    path: str, method: str
) -> None:
    transport = KitTransport(
        SecretStr(CANARY),
        transport=httpx.MockTransport(
            lambda r: pytest.fail("Unexpected network request")
        ),
    )
    try:
        with pytest.raises(ValueError):
            transport.request(method, path)
    finally:
        transport.close()


def test_authentication_headers_and_log_privacy(
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        logging.getLogger("httpcore.http11").debug(CANARY)
        return httpx.Response(200, json={})

    caplog.set_level(logging.DEBUG)
    transport = KitTransport(
        access_token=SecretStr(CANARY), transport=httpx.MockTransport(handler)
    )
    try:
        transport.request("GET", "/v4/account")
        assert calls[0].headers["Authorization"] == "Bearer " + CANARY
        assert "X-Kit-Api-Key" not in calls[0].headers
        assert CANARY not in caplog.text
        logging.getLogger("httpx").info("other-call-visible")
        assert "other-call-visible" in caplog.text
    finally:
        transport.close()
    for kwargs in [
        {},
        {"api_key": SecretStr(" ")},
        {"api_key": SecretStr(CANARY), "access_token": SecretStr(CANARY)},
        {"api_key": SecretStr(CANARY), "timeout": 0},
    ]:
        with pytest.raises(ValueError):
            KitTransport(**kwargs)  # type: ignore[arg-type]


def test_configuration_and_installed_entrypoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KIT_API_KEY", raising=False)
    monkeypatch.delenv("KIT_ACCESS_TOKEN", raising=False)
    integration = create_integration()
    assert isinstance(integration, IntegrationProtocol)
    assert not integration.is_available()
    with pytest.raises(ValueError):
        _ = integration.client
    assert not integration.initialize().success
    monkeypatch.setenv("KIT_API_KEY", CANARY)
    assert integration.initialize().success and integration.is_available()
    assert integration.initialize().success
    integration.close()
    assert not integration.is_available()
    monkeypatch.setenv("KIT_ACCESS_TOKEN", CANARY)
    assert not integration.initialize().success
    monkeypatch.delenv("KIT_API_KEY")
    assert integration.initialize().success
    integration.close()
    entries = importlib.metadata.entry_points(group="zeo_core.integrations")
    assert entries["kit.marketing"].load() is create_integration


def test_required_ids_are_validated_before_dispatch() -> None:
    for payload in [
        {"operation": "subscriber"},
        {"operation": "sequence_email", "resource_id": 1},
        {"operation": "subscriber", "resource_id": True},
    ]:
        with pytest.raises(ValidationError):
            ReadRequest.model_validate(payload)
    path = "/v4/sequences/{sequence_id}/subscribers/{id}"
    assert set(CONTRACT["paths"][path]) == {"post"}
