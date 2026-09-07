"""Run the real marketing capability/client pipeline with an offline HTTP boundary."""

from __future__ import annotations

import json

import httpx
from pydantic import SecretStr

from zeo_core.integrations.hubspot import (
    Audience,
    EmailContent,
    EmailDraft,
    HubSpotClient,
    HubSpotIntegration,
    HubSpotTransport,
    PublishRequest,
    send_spec_digest,
)
from zeo_core.tools import CapabilityRegistry, ToolContext, invoke_sync
from zeo_core.tools.builtin.hubspot import (
    SaveEmailRequest,
    register_capabilities,
)


def main() -> None:
    """No account, credential lookup, or network access; do not infer delivery."""
    email: dict[str, object] = {}
    calls: list[str] = []

    def provider(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if request.method == "POST" and request.url.path.endswith("/2026-03"):
            email.update(json.loads(request.content))
            email.update(
                id="123",
                type="BATCH_EMAIL",
                updatedAt="2026-09-07T10:00:00Z",
                isPublished=False,
                isTransactional=False,
            )
            return httpx.Response(201, json=email)
        if request.method == "GET":
            return httpx.Response(200, json=email)
        if request.method == "PATCH":
            email.update(json.loads(request.content))
            return httpx.Response(200, json=email)
        if request.url.path.endswith("/publish"):
            return httpx.Response(204)
        raise AssertionError("Unexpected marketing request")

    client = HubSpotClient(
        transport=HubSpotTransport(
            SecretStr("offline-example-credential"),
            transport=httpx.MockTransport(provider),
        )
    )
    integration = HubSpotIntegration(client)
    registry = CapabilityRegistry()
    register_capabilities(registry)
    ctx = ToolContext(
        run_id="hubspot-example",
        tool_name="hubspot",
        tool_version="1.0.0",
        logger=None,
        fs=None,
        work_dir=".",
        output_dir=".",
        services={"hubspot.marketing": integration},
    )
    draft = EmailDraft(
        name="Weekly issue",
        subject="This week",
        content=EmailContent(template_path="email/newsletter.html", plain_text="News"),
        from_name="Editor",
        from_email="editor@example.com",
        subscription_id="5",
        office_location_id="6",
        audience=Audience(contact_ids=("42",)),
    )
    try:
        saved = invoke_sync(
            registry.get("hubspot.marketing.email.save@1.0.0"),
            SaveEmailRequest(draft=draft),
            ctx,
        )
        if saved.data is None:
            raise RuntimeError("Offline draft failed")
        print("Draft created through registered capability:", saved.data.data["id"])
        published = invoke_sync(
            registry.get("hubspot.marketing.email.publish@1.0.0"),
            PublishRequest(
                email_id="123",
                expected_updated_at="2026-09-07T10:00:00Z",
                expected_send_spec_sha256=send_spec_digest(saved.data.data),
                render_evidence_ref="offline-example/render-reviewed",
                audience=draft.audience,
                subscription_id="5",
                confirm=True,
            ),
            ctx,
        )
        if published.data is None:
            raise RuntimeError("Offline publish failed")
        print("HTTP operations:", ", ".join(calls))
        print("SIMULATED: no network, no live send, provider delivery unverified")
    finally:
        integration.close()


if __name__ == "__main__":
    main()
