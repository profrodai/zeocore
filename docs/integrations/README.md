# Integration account setup

<!-- Teaches CLAUDE.md Rev 17; user documentation reviewed 2026-09-08. -->

Start with [test and production environments](environments.md). It explains the
launcher, secure key prompts, file locations, offline fixtures, and promotion.
Then follow your provider's complete account guide. These instructions apply to
the source checkout containing this feature; do not assume an older published
wheel includes the environment launcher.

| Integration ID | Get credentials and configure accounts | Test track |
|---|---|---|
| `hubspot.marketing` | [HubSpot](hubspot.md) | Developer test account; restricted recipients |
| `kit.marketing` | [Kit](kit.md) | Dedicated creator account and designated subscribers |
| `github` | [GitHub](github.md) | Separate token limited to a disposable repository |
| `google.mail` | [Gmail](google.md#gmail) | Dedicated Google user and seeded mailbox |
| `google.drive` | [Drive](google.md#drive) | Dedicated user and test folder/files |
| `google.calendar` | [Calendar](google.md#calendar) | Dedicated user and secondary calendar |
| `google.docs` | [Docs](google.md#docs) | Dedicated user and disposable document |
| `google.sheets` | [Sheets](google.md#sheets) | Dedicated user and disposable spreadsheet |
| `google.slides` | [Slides](google.md#slides) | Dedicated user and disposable presentation |
| `notion` | [Notion](notion.md) | Test workspace or separately shared test parent |
| `supabase` | [Supabase](supabase.md) | Local stack or separate hosted project |
| `social.bluesky` | [Bluesky](bluesky.md) | Dedicated account; posts remain public |
| `llms` | [OpenAI, Anthropic, Ollama and mock](llms.md) | Separate provider project/workspace or local model; explicit fixture |
| `pandoc` | [Pandoc](local-tools.md#pandoc) | Local sample documents and separate output directory |
| `ffmpeg` | [FFmpeg](local-tools.md#ffmpeg) | Local synthetic media and separate output directory |
| `jupytext` | [Jupytext](local-tools.md#jupytext) | Local sample notebooks and separate output directory |
| `zeoconnect` | [Hosted connection and pairing](zeoconnect.md) | Fake service or separately paired test identity/resources |

The first sixteen rows are package entry points. ZEOconnect is an additional
composition surface. The `database.sqlite` and `database.bigquery` directories
are placeholders with no implemented service or credential workflow; they are
not supported integrations. HTTP/MCP are adapters for exposing capabilities,
not additional provider accounts. Future integrations must join this inventory
and provide both tracks before their setup is considered complete.

Test mode is a ZeoCore environment selection. It does not turn an ordinary
provider account into a vendor sandbox. Provider credentials, account permissions,
selected resources and recipients still determine what the provider can change.

For staged notebook/document releases, use [authoring conversion receipts](authoring-receipts.md).
