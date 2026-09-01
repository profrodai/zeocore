"""
Protocol definitions for Google Sheets integration.

This module defines protocol classes for the Google Sheets service and
resource shape, ensuring proper typing throughout the codebase and avoiding
the use of Any -- mirrors `google/docs/protocols.py`'s structure, adapted to
the Sheets v4 REST surface this integration actually calls.

Per RULING-408 DESIGN-04 approach B, the curated surface is 7 of Sheets'
17 methods: `spreadsheets.create`, `spreadsheets.get`,
`spreadsheets.values.get`, `spreadsheets.values.update`,
`spreadsheets.values.append`, `spreadsheets.values.clear`, and
`spreadsheets.batchUpdate` -- no more, no less, and no escape-hatch method
(that is a separate, not-yet-built ruling item for the shared workspace
surface, same as Docs).

Two resources are modeled because the real API nests them that way: the top-
level `spreadsheets` resource (create/get/batchUpdate) and the
`spreadsheets.values` sub-resource (get/update/append/clear) reached via
`service.spreadsheets().values()`.
"""

from typing import Any, Protocol, TypeVar, runtime_checkable

from zeo_core.integrations.core.protocols import IntegrationProtocol
from zeo_core.integrations.core.results import IntegrationResult

T = TypeVar("T")  # Generic type for result content
R = TypeVar("R", covariant=True)  # Generic type for return values


@runtime_checkable
class SheetsRequest(Protocol[R]):
    """Protocol for Google Sheets request objects."""

    def execute(self) -> R:
        """
        Execute the request.

        Returns:
            R: The API response.
        """
        ...


@runtime_checkable
class SheetsValuesResource(Protocol):
    """Protocol for the Google Sheets `spreadsheets.values` sub-resource.

    Reached via `service.spreadsheets().values()`. Per the brief's own
    verified fact: `ValueRange` (the body every one of these four methods
    reads or writes) has exactly three fields (`range`, `majorDimension`,
    `values`) and never the 69-kind `Request` union -- this whole resource
    is plainly typed with no union, independent of `batchUpdate`.
    """

    def get(
        self,
        spreadsheetId: str,  # noqa: N803 -- matches the real googleapiclient parameter name verbatim
        range: str,  # noqa: A002 -- matches the real googleapiclient parameter name verbatim
    ) -> SheetsRequest[dict[str, object]]:
        """
        Get values from a range.

        Args:
            spreadsheetId: ID of the spreadsheet to read from.
            range: A1 notation range to read (e.g. "Sheet1!A1:B10").

        Returns:
            SheetsRequest: Request object for getting the values.
        """
        ...

    def update(
        self,
        spreadsheetId: str,  # noqa: N803
        range: str,  # noqa: A002 -- matches the real googleapiclient parameter name verbatim
        body: dict[str, object],
        valueInputOption: str,  # noqa: N803
    ) -> SheetsRequest[dict[str, object]]:
        """
        Update values in a range (overwrites existing content).

        Args:
            spreadsheetId: ID of the spreadsheet to update.
            range: A1 notation range to write.
            body: `ValueRange` payload (`{"values": [[...], ...]}`).
            valueInputOption: "RAW" or "USER_ENTERED".

        Returns:
            SheetsRequest: Request object for updating the values.
        """
        ...

    def append(
        self,
        spreadsheetId: str,  # noqa: N803
        range: str,  # noqa: A002
        body: dict[str, object],
        valueInputOption: str,  # noqa: N803
    ) -> SheetsRequest[dict[str, object]]:
        """
        Append values after the last row of a range (never overwrites).

        Args:
            spreadsheetId: ID of the spreadsheet to append to.
            range: A1 notation range identifying the table to append after.
            body: `ValueRange` payload (`{"values": [[...], ...]}`).
            valueInputOption: "RAW" or "USER_ENTERED".

        Returns:
            SheetsRequest: Request object for appending the values.
        """
        ...

    def clear(
        self,
        spreadsheetId: str,  # noqa: N803
        range: str,  # noqa: A002
    ) -> SheetsRequest[dict[str, object]]:
        """
        Clear values from a range, leaving formatting untouched.

        Args:
            spreadsheetId: ID of the spreadsheet to clear.
            range: A1 notation range to clear.

        Returns:
            SheetsRequest: Request object for clearing the values.
        """
        ...


@runtime_checkable
class SheetsSpreadsheetsResource(Protocol):
    """Protocol for the Google Sheets `spreadsheets` resource."""

    def get(self, spreadsheetId: str) -> SheetsRequest[dict[str, object]]:  # noqa: N803
        """
        Get a spreadsheet's metadata and (optionally) its data.

        Args:
            spreadsheetId: ID of the spreadsheet to retrieve.

        Returns:
            SheetsRequest: Request object for getting the spreadsheet.
        """
        ...

    def create(self, body: dict[str, object]) -> SheetsRequest[dict[str, object]]:
        """
        Create a new spreadsheet.

        Args:
            body: Spreadsheet resource body (e.g.
                `{"properties": {"title": ...}}`).

        Returns:
            SheetsRequest: Request object for creating the spreadsheet.
        """
        ...

    def batchUpdate(  # noqa: N802 -- matches the real googleapiclient method name verbatim
        self,
        spreadsheetId: str,  # noqa: N803
        body: dict[str, object],
    ) -> SheetsRequest[dict[str, object]]:
        """
        Apply a batch of update requests to a spreadsheet.

        Args:
            spreadsheetId: ID of the spreadsheet to update.
            body: `{"requests": [...]}` payload.

        Returns:
            SheetsRequest: Request object for applying the batch update.
        """
        ...

    def values(self) -> SheetsValuesResource:
        """
        Get the `spreadsheets.values` sub-resource.

        Returns:
            SheetsValuesResource: The values sub-resource.
        """
        ...


@runtime_checkable
class SheetsService(Protocol):
    """Protocol for the Google Sheets API service (the object
    `googleapiclient.discovery.build("sheets", "v4", ...)` returns)."""

    def spreadsheets(self) -> SheetsSpreadsheetsResource:
        """
        Get the spreadsheets resource.

        Returns:
            SheetsSpreadsheetsResource: The spreadsheets resource.
        """
        ...


@runtime_checkable
class GoogleCredentials(Protocol):
    """Protocol for Google API credentials."""

    token: str
    refresh_token: str
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list[str]


@runtime_checkable
class SheetsIntegrationProtocol(IntegrationProtocol, Protocol):
    """Protocol for the Google Sheets integration's public surface.

    Built following `calendar/protocols.py`'s `CalendarIntegrationProtocol`
    and `docs/protocols.py`'s `DocsIntegrationProtocol` precedent: a
    `@runtime_checkable` Protocol subclassing `IntegrationProtocol`. Per
    RULING-408, the curated surface is exactly 7 of Sheets' 17 API methods:
    `create_spreadsheet`, `get_spreadsheet`, `get_values`, `update_values`,
    `append_values`, `clear_values`, `batch_update`.
    """

    def get_spreadsheet(self, spreadsheet_id: str) -> IntegrationResult[dict[str, Any]]:
        """Retrieve a spreadsheet's metadata (wraps `spreadsheets.get`)."""
        ...

    def create_spreadsheet(self, title: str) -> IntegrationResult[dict[str, Any]]:
        """Create a new, empty spreadsheet with the given title."""
        ...

    def get_values(
        self, spreadsheet_id: str, range_a1: str
    ) -> IntegrationResult[dict[str, Any]]:
        """Read values from a range (wraps `spreadsheets.values.get`)."""
        ...

    def update_values(
        self,
        spreadsheet_id: str,
        range_a1: str,
        values: list[list[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> IntegrationResult[dict[str, Any]]:
        """Overwrite values in a range (wraps
        `spreadsheets.values.update`)."""
        ...

    def append_values(
        self,
        spreadsheet_id: str,
        range_a1: str,
        values: list[list[Any]],
        value_input_option: str = "USER_ENTERED",
    ) -> IntegrationResult[dict[str, Any]]:
        """Append values after the last row of a range (wraps
        `spreadsheets.values.append`)."""
        ...

    def clear_values(
        self, spreadsheet_id: str, range_a1: str
    ) -> IntegrationResult[dict[str, Any]]:
        """Clear values from a range, leaving formatting untouched (wraps
        `spreadsheets.values.clear`)."""
        ...

    def batch_update(
        self, spreadsheet_id: str, requests: list[dict[str, Any]]
    ) -> IntegrationResult[dict[str, Any]]:
        """Apply a batch of update requests to a spreadsheet (wraps
        `spreadsheets.batchUpdate`), ordered internally per
        `SheetsRequestBuilder`'s policy."""
        ...
