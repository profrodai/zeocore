"""Independent upstream contract and FIFO HTTP boundary for Kit tests."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from zeo_core.integrations.kit import KitClient, KitTransport

CONTRACT = json.loads(Path(__file__).with_name("api_contract.json").read_text())
CANARY = "kit-test-credential-do-not-log"
ClientFixture = tuple[KitClient, list[httpx.Request], list[httpx.Response | Exception]]


def upstream(path: str, method: str = "get") -> dict[str, Any]:
    operation = CONTRACT["paths"][path][method]
    response = next(iter(operation["responses"].values()))
    return json.loads(json.dumps(response["content"]["application/json"]["example"]))  # type: ignore[no-any-return]


def assert_schema(value: object, schema: dict[str, Any], location: str) -> None:
    # The two documented upstream schema contradictions remain visible exceptions.
    if location == "PUT /v4/broadcasts/{id}/send_at" and value is None:
        return
    if value is None:
        assert schema.get("nullable"), location
        return
    kind = schema.get("type")
    if kind == "object":
        assert isinstance(value, dict), location
        required = set(schema.get("required", []))
        if location.endswith("/subscriber_filter/[]"):
            required = set()  # Prose: exactly one of all/any/none, not all three.
            assert len(value) == 1
        assert required <= value.keys(), location
        properties = schema.get("properties", {})
        assert value.keys() <= properties.keys(), (location, value.keys())
        for key, item in value.items():
            assert_schema(item, properties[key], location + "/" + key)
    elif kind == "array":
        assert isinstance(value, list), location
        for item in value:
            assert_schema(item, schema["items"], location + "/[]")
    elif kind in {"integer", "boolean", "string"}:
        assert type(value) is {"integer": int, "boolean": bool, "string": str}[kind], (
            location
        )
    if "enum" in schema:
        assert value in schema["enum"], location


def wire_contract(request: httpx.Request) -> None:
    matches = [
        (path, methods[request.method.lower()])
        for path, methods in CONTRACT["paths"].items()
        if request.method.lower() in methods
        and re.fullmatch(re.sub(r"\{[^}]+\}", "[0-9]+", path), request.url.path)
    ]
    assert len(matches) == 1, (request.method, request.url.path)
    path, operation = matches[0]
    query = {p["name"] for p in operation.get("parameters", []) if p["in"] == "query"}
    assert set(request.url.params) <= query
    if request.content:
        schema = operation["requestBody"]["content"]["application/json"]["schema"]
        assert_schema(json.loads(request.content), schema, request.method + " " + path)


@pytest.fixture
def setup_client() -> Iterator[ClientFixture]:
    calls: list[httpx.Request] = []
    responses: list[httpx.Response | Exception] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.url.host == "api.kit.com"
        assert request.headers["X-Kit-Api-Key"] == CANARY
        assert "authorization" not in request.headers
        wire_contract(request)
        assert responses, "Unexpected extra HTTP operation"
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    client = KitClient(
        transport=KitTransport(
            SecretStr(CANARY), transport=httpx.MockTransport(handler)
        )
    )
    yield client, calls, responses
    client.close()


@pytest.fixture
def broadcast() -> dict[str, Any]:
    data = upstream("/v4/broadcasts/{id}")["broadcast"]
    data.update(id=57, content=" <p>Reviewed news</p> ", subject=" News ")
    return dict(data)


@pytest.fixture
def sequence() -> dict[str, Any]:
    data = upstream("/v4/sequences/{id}")["sequence"]
    data.update(
        id=23, email_address="editor@example.com", email_template_id=6, active=False
    )
    return dict(data)


@pytest.fixture
def email() -> dict[str, Any]:
    data = upstream("/v4/sequences/{sequence_id}/emails", "post")["email"]
    data.update(
        id=38,
        sequence_id=23,
        content="<p>Welcome</p>",
        preview_text="Welcome",
        published=True,
    )
    return dict(data)


def page(key: str, rows: list[dict[str, Any]], *, more: bool = False) -> dict[str, Any]:
    return {
        key: rows,
        "pagination": {
            "has_previous_page": False,
            "has_next_page": more,
            "end_cursor": "cursor2",
            "start_cursor": "cursor1",
            "per_page": 50,
        },
    }


def snapshot(sequence: dict[str, Any], email: dict[str, Any]) -> dict[str, Any]:
    return {
        "sequence": {
            k: v
            for k, v in sequence.items()
            if k not in {"email_count", "subscriber_count", "stats"}
        },
        "emails": [email],
    }


def queue_snapshot(
    responses: list[httpx.Response | Exception],
    sequence: dict[str, Any],
    email: dict[str, Any],
) -> None:
    responses.extend(
        [
            httpx.Response(200, json={"sequence": sequence}),
            httpx.Response(200, json=page("emails", [email])),
        ]
    )
