"""Run canonical Kit draft and send capabilities against an offline HTTP boundary."""

from __future__ import annotations

import json

import httpx
from pydantic import SecretStr

from zeo_core.integrations.kit import (
    Audience,
    BroadcastDraft,
    KitClient,
    KitIntegration,
    KitTransport,
    SendBroadcast,
    broadcast_send_digest,
)
from zeo_core.tools import CapabilityRegistry, ToolContext, invoke_sync
from zeo_core.tools.builtin.kit import SaveBroadcastRequest, register_capabilities


def main() -> None:
    source: dict[str, object] = {}
    calls: list[str] = []

    def provider(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "GET":
            if request.url.path.endswith("/stats"):
                return httpx.Response(
                    200, json={"broadcast": {"stats": {"status": "draft"}}}
                )
            return httpx.Response(200, json={"broadcast": source})
        if request.method == "POST" and request.url.path == "/v4/broadcasts":
            data = json.loads(request.content)
            if data["send_at"] is None:
                source.update(
                    data, id=57, email_template={"id": 6, "name": "Text Only"}
                )
                return httpx.Response(201, json={"broadcast": source})
            return httpx.Response(201, json={"broadcast": {**data, "id": 58}})
        raise AssertionError("Unexpected Kit operation")

    integration = KitIntegration(
        KitClient(
            transport=KitTransport(
                SecretStr("offline-example-credential"),
                transport=httpx.MockTransport(provider),
            )
        )
    )
    registry = CapabilityRegistry()
    register_capabilities(registry)
    ctx = ToolContext(
        run_id="kit-example",
        tool_name="kit",
        tool_version="1.0.0",
        logger=None,
        fs=None,
        work_dir=".",
        output_dir=".",
        services={"kit.marketing": integration},
    )
    try:
        saved = invoke_sync(
            registry.get("kit.marketing.broadcast.save@1.0.0"),
            SaveBroadcastRequest(
                draft=BroadcastDraft(
                    subject="Weekly news",
                    content="<p>This week</p>",
                    email_address="editor@example.com",
                    email_template_id=6,
                    audience=Audience(entire_account=True),
                )
            ),
            ctx,
        )
        if saved.data is None:
            raise RuntimeError("Offline draft failed")
        print("Draft created through registered capability:", saved.data.data["id"])
        sent = invoke_sync(
            registry.get("kit.marketing.broadcast.send@1.0.0"),
            SendBroadcast(
                broadcast_id=57,
                expected_digest=broadcast_send_digest(saved.data.data),
                render_evidence_ref="offline/render",
                audience_policy_ref="offline/entire-account-approved",
                confirm=True,
            ),
            ctx,
        )
        if sent.data is None:
            raise RuntimeError("Offline send failed")
        print("Track the new send object:", sent.data.data["id"])
        print("HTTP operations:", ", ".join(calls))
        print("SIMULATED: no network, no live send, provider delivery unverified")
    finally:
        integration.close()


if __name__ == "__main__":
    main()
