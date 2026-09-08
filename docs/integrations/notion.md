# Notion account setup

**Reviewed:** 2026-09-08. Integration: `notion`. Install with
`uv pip install -e ".[notion]"` in the source checkout. Read
[environment setup](environments.md) and the [Notion tutorial](../tutorials/notion-integration.md).

## Obtain the connection token

Sign into Notion as a workspace owner and open the
[Developer portal](https://www.notion.so/profile/integrations). Under **Build →
Internal connections**, create a connection, name it for the environment and select
the workspace. Its **Configuration** tab provides the installation access token.
Select **Read content**, and add **Insert content**/**Update content** only for
operations you intend to run. User-information capabilities are separate.
[Official internal connection instructions](https://developers.notion.com/guides/get-started/internal-connections).

A new connection cannot see your pages automatically. In its **Content access** tab,
edit access to the intended test parent; alternatively open that page's **••• →
Connections → Add connection** and select the connection. Sharing a parent grants
access to children, so never share a production root with a test connection.
Use `NOTION_TOKEN`, not the connection ID or OAuth client secret.

For public multi-workspace apps, use Notion's public connection OAuth flow in your
host and supply its installation access token. The token must correspond to the
chosen workspace and shared resources. See the tutorial's OAuth lifecycle rather
than treating an internal token as multi-tenant authorization.

## Test account track

ZeoCore does not assume a Notion sandbox endpoint. Create a dedicated test workspace
or a separately shared test parent named `ZeoCore integration test`. Use a new test
connection whose content grants include only that tree. A dedicated workspace is
preferable when tests will exercise parent/child access or destructive cleanup.

Create a child page containing synthetic text and copy its page ID from the URL or
Copy link. Record that ID in the test resource configuration. Save `check_notion.py`:

```python
from zeo_core.integrations.notion import NotionIntegration

service = NotionIntegration()
configured = service.initialize()
if not configured.success:
    raise SystemExit("Notion configuration failed; check the test token")
result = service.get_page("REPLACE_WITH_TEST_PAGE_ID")
if not result.success:
    raise SystemExit("Page read failed; check ID, workspace and connection sharing")
print("Selected Notion page read succeeded")
```

```bash
python -m zeo_core.integrations.environments --mode test   --root "$ZEO_ENV_ROOT" --integration notion --secret NOTION_TOKEN   -- python /absolute/path/check_notion.py
```

Use `ZEO_TEST_NOTION_TOKEN` for unattended tests. Non-secret options go under
`notion:` in `test/config/integrations.yaml`, for example `timeout_ms: 60000`.
No `.env` file is loaded automatically by this launcher.

## Production account track

Create a separate internal connection in the actual workspace or complete the
production public OAuth installation. Share only the required production parent
pages/data sources. Store the token as `ZEO_PRODUCTION_NOTION_TOKEN`, record the
production IDs, and run the harmless page-read script with `--mode production`.
Do not share the production page tree with the test connection to work around a
404. Keep test and production object IDs separate even if their titles match.

## Bounded E2E and cleanup

Under the test parent only, create a page titled `ZEO TEST <run-id>`, append a
synthetic paragraph, read the page and block contents back, update the paragraph,
and verify the result. Archive only that created page at the end. If testing data
sources, create a disposable data source with known property types and validate
schema before inserting rows; database IDs and data-source IDs are distinct.
The [offline demo](../../examples/notion_demo.py) exercises controlled responses
without credentials and can run with `--fixture`. It is not a live workspace test.

## Troubleshooting and rotation

401: repair the token. 403: check the connection's content capabilities. 404: first
check page ID, workspace and explicit sharing; lack of access can resemble absence.
If creating a connection is unavailable, verify workspace ownership/admin policy.
If the schema changed, review the actual data source before retrying mutations.

Regenerate/revoke the token or connection in its Developer portal settings, update
only the selected namespace, restart and rerun the page read. Remove the connection's
page access when retiring it. A public OAuth installation must be disconnected and
its token custody repaired by the host; do not mix tokens between workspaces.
