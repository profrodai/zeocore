"""Google Sheets integration for zeo_core.

Read + write access to Google Sheets spreadsheets via the `googleapiclient`
Sheets v4 REST API, using the same OAuth (`InstalledAppFlow` + local-server)
flow as `integrations.google.drive`/`mail`/`calendar`/`docs` -- reuses
`GoogleAuthProvider` and `GoogleConfigProvider` as-is, no new auth or config
mechanism invented.

Per RULING-408 (the "workspace triple" design ruling), this ships the
curated 7-of-17-method surface DESIGN-04 approach B ruled:
`get_spreadsheet`/`create_spreadsheet` (wrapping `spreadsheets.get`/
`spreadsheets.create`), `get_values`/`update_values`/`append_values`/
`clear_values` (wrapping `spreadsheets.values.get`/`update`/`append`/
`clear` -- the plainly-typed, non-`batchUpdate` half of the Sheets API,
verified live to use a 3-field `ValueRange` body rather than the 69-kind
`Request` union), and `batch_update` (wrapping `spreadsheets.batchUpdate`,
the one method that does touch that union).

Follows the same registration shape as `integrations.google.docs`: a shared
config model in `google/config.py`, a service class implementing
`SheetsIntegrationProtocol`, and registration under the
`zeo_core.integrations` entry-point group (see this repo's `pyproject.toml`,
`[project.entry-points."zeo_core.integrations"]`, key `google.sheets`).

Quickstart::

    from zeo_core.integrations.google.sheets import GoogleSheetsService

    sheets = GoogleSheetsService(
        client_secrets_file="config/google_client_secret.json",
        credentials_file="config/google_credentials.json",
    )
    result = sheets.initialize()
    assert result.success

    # Create a spreadsheet from scratch, then read/write it -- entirely
    # through the values.* surface, no batchUpdate needed.
    created = sheets.create_spreadsheet(title="Q3 numbers")
    spreadsheet_id = created.content["spreadsheetId"]
    sheets.update_values(spreadsheet_id, "Sheet1!A1:B1", [["Name", "Score"]])
    sheets.append_values(spreadsheet_id, "Sheet1!A1", [["Ada", 100]])
    values = sheets.get_values(spreadsheet_id, "Sheet1!A1:B2")

    # Structural/formatting edits go through batch_update.
    sheets.batch_update(
        spreadsheet_id,
        [{"addSheet": {"properties": {"sheetId": 1, "title": "Notes"}}}],
    )

Every call returns an `IntegrationResult[T]` (`.success`, `.content`,
`.error`) -- see `zeo_core.integrations.core.results`.
"""

from __future__ import annotations

from zeo_core.integrations.google.sheets.models import (
    Color,
    GridRange,
    NumberFormat,
    TextFormat,
)
from zeo_core.integrations.google.sheets.protocols import (
    SheetsIntegrationProtocol,
)
from zeo_core.integrations.google.sheets.request_builder import SheetsRequestBuilder
from zeo_core.integrations.google.sheets.service import GoogleSheetsService

__all__ = [
    "GoogleSheetsService",
    "Color",
    "GridRange",
    "NumberFormat",
    "TextFormat",
    "SheetsRequestBuilder",
    "SheetsIntegrationProtocol",
    "create_integration",
]


def create_integration() -> SheetsIntegrationProtocol:
    """
    Create and configure a Google Sheets integration.

    This function is used as an entry point for automatic integration
    discovery.

    Returns:
        SheetsIntegrationProtocol: Configured Google Sheets service.
    """
    return GoogleSheetsService()
