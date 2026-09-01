"""
Data models for Google Sheets integration.

Per RULING-408 DESIGN-02 approach B (the typing seam ruling): only the small,
closed LEAF types that recur across the Sheets API's `batchUpdate` request
shapes get real Pydantic models. Everything at the request-kind level (the
actual `Request` union members -- 69 kinds, e.g. `AddSheetRequest`,
`UpdateCellsRequest`, `RepeatCellRequest`, etc.) stays `dict[str, Any]` --
building 69 TypedDicts was explicitly REJECTED (DESIGN-02 approach C, "a
second library" that also "freezes against an API that revises").

Four leaves are modeled here, matching the brief's own field-count audit
against the live discovery document (revision 20260828):

- `Color` (4 fields: red/green/blue/alpha) -- identical shape to
  `docs/models.py`'s `Color`. NOT imported from there: RULING-408 DESIGN-03
  ruled one request builder per API, NOT shared, and the same reasoning
  extends to these small leaf models -- Sheets is not Docs, and a shared
  models module would recreate exactly the coupling DESIGN-03 rejected at
  the builder level. The shape is copied, not imported, so Sheets can evolve
  it independently if Sheets' own `CellFormat.backgroundColor` (or similar)
  ever needs a Sheets-specific accessor Docs' `TextStyle.foregroundColor`
  does not.
- `GridRange` (5 fields: sheetId/startRowIndex/endRowIndex/startColumnIndex/
  endColumnIndex) -- the single most-reused leaf across Sheets' 69 request
  kinds: almost every request that targets "some region of a sheet"
  (`RepeatCellRequest.range`, `SortRangeRequest.range`,
  `DeleteRangeRequest.range`, `MergeCellsRequest.range`, etc.) anchors on
  this exact shape. All five fields are optional on the wire (Google treats
  a missing end index as "unbounded in that dimension"), so `int | None`
  throughout, matching the API's own optionality rather than forcing a
  caller to supply an artificial bound.
- `TextFormat` (9 fields) -- recurs inside `CellFormat.textFormat` any time
  a caller wants to express cell text styling (bold/italic/font/size/color)
  in a `batchUpdate` request (e.g. `RepeatCellRequest.cell.userEnteredFormat.
  textFormat`).
- `NumberFormat` (2 fields: type/pattern) -- recurs inside
  `CellFormat.numberFormat` for currency/date/percentage cell formatting.

`spreadsheets.values.*` (the plainly-typed, non-batchUpdate half of this
integration -- see `service.py`) does not need any of these leaves: its
`ValueRange` body has exactly three fields (`range`, `majorDimension`,
`values`), verified live against discovery revision 20260828, and none of
them are one of these four closed shapes.
"""

from pydantic import BaseModel, Field


class Color(BaseModel):
    """An RGBA color, matching the Google Workspace APIs' shared `Color`
    message shape (`red`/`green`/`blue`/`alpha`, each a float 0-1, `alpha`
    optional and defaulting to fully opaque when omitted by the API).

    Recurs inside Sheets' `CellFormat.backgroundColor`,
    `TextFormat.foregroundColor`, and border colors alike.
    """

    red: float = Field(0.0, ge=0.0, le=1.0, description="Red channel, 0.0-1.0")
    green: float = Field(0.0, ge=0.0, le=1.0, description="Green channel, 0.0-1.0")
    blue: float = Field(0.0, ge=0.0, le=1.0, description="Blue channel, 0.0-1.0")
    alpha: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Alpha channel, 0.0-1.0. Omitted means fully opaque.",
    )

    def to_api_dict(self) -> dict[str, object]:
        """
        Render this Color as the Sheets API's wire shape: a flat
        `{"red": ..., "green": ..., "blue": ..., "alpha": ...}` dict (Sheets'
        `Color` message, unlike Docs' `OptionalColor` wrapper, is used
        directly -- no `{"color": {"rgbColor": ...}}` nesting).

        Returns:
            The Sheets API `Color` dict, e.g. for
            `CellFormat.backgroundColor` or `TextFormat.foregroundColor`.
        """
        result: dict[str, object] = {
            "red": self.red,
            "green": self.green,
            "blue": self.blue,
        }
        if self.alpha is not None:
            result["alpha"] = self.alpha
        return result

    @classmethod
    def from_api_dict(cls, data: dict[str, object]) -> "Color":
        """
        Parse a Sheets API `Color` dict back into a `Color`.

        Args:
            data: A dict shaped like `{"red": .., "green": .., "blue": ..,
                "alpha": ..}`.

        Returns:
            The parsed Color.
        """
        red = data.get("red", 0.0)
        green = data.get("green", 0.0)
        blue = data.get("blue", 0.0)
        alpha = data.get("alpha")
        return cls(
            red=float(red) if isinstance(red, int | float) else 0.0,
            green=float(green) if isinstance(green, int | float) else 0.0,
            blue=float(blue) if isinstance(blue, int | float) else 0.0,
            alpha=float(alpha) if isinstance(alpha, int | float) else None,
        )


class GridRange(BaseModel):
    """A range on a single sheet, matching the Sheets API's `GridRange`
    message shape.

    All five fields are optional on the wire: a missing `sheetId` is
    invalid (every real range targets a sheet), but a missing
    `startRowIndex`/`endRowIndex`/`startColumnIndex`/`endColumnIndex` means
    "unbounded in that dimension" per the API's own documented semantics
    (e.g. omitting both column bounds selects entire rows). Indices are
    0-based, end-exclusive, matching the API exactly -- not remapped to any
    1-based or inclusive convention a spreadsheet UI might use.
    """

    sheet_id: int = Field(..., description="ID of the sheet this range is on")
    start_row_index: int | None = Field(
        None, description="0-based start row (inclusive), or unbounded if omitted"
    )
    end_row_index: int | None = Field(
        None, description="0-based end row (exclusive), or unbounded if omitted"
    )
    start_column_index: int | None = Field(
        None, description="0-based start column (inclusive), or unbounded if omitted"
    )
    end_column_index: int | None = Field(
        None, description="0-based end column (exclusive), or unbounded if omitted"
    )

    def to_api_dict(self) -> dict[str, object]:
        """
        Render this GridRange as the Sheets API's wire shape (camelCase
        keys), omitting any bound left unset so the API's own "unbounded in
        that dimension" semantics apply rather than a caller accidentally
        pinning an implicit 0.

        Returns:
            The Sheets API `GridRange` dict.
        """
        result: dict[str, object] = {"sheetId": self.sheet_id}
        if self.start_row_index is not None:
            result["startRowIndex"] = self.start_row_index
        if self.end_row_index is not None:
            result["endRowIndex"] = self.end_row_index
        if self.start_column_index is not None:
            result["startColumnIndex"] = self.start_column_index
        if self.end_column_index is not None:
            result["endColumnIndex"] = self.end_column_index
        return result

    @classmethod
    def from_api_dict(cls, data: dict[str, object]) -> "GridRange":
        """
        Parse a Sheets API `GridRange` dict back into a `GridRange`.

        Args:
            data: A dict shaped like `{"sheetId": 0, "startRowIndex": 1,
                ...}`.

        Returns:
            The parsed GridRange.
        """
        sheet_id = data.get("sheetId", 0)
        return cls(
            sheet_id=int(sheet_id) if isinstance(sheet_id, int) else 0,
            start_row_index=cls._optional_int(data.get("startRowIndex")),
            end_row_index=cls._optional_int(data.get("endRowIndex")),
            start_column_index=cls._optional_int(data.get("startColumnIndex")),
            end_column_index=cls._optional_int(data.get("endColumnIndex")),
        )

    @staticmethod
    def _optional_int(value: object) -> int | None:
        """Narrow an `object` pulled from a raw API dict to `int | None`."""
        return int(value) if isinstance(value, int) else None


class NumberFormat(BaseModel):
    """A cell number-format spec, matching the Sheets API's `NumberFormat`
    message shape (2 fields: `type`/`pattern`).

    Recurs inside `CellFormat.numberFormat` for currency/date/percentage/
    scientific cell formatting requests.
    """

    type: str = Field(
        ...,
        description=(
            "Format type, e.g. 'TEXT', 'NUMBER', 'PERCENT', 'CURRENCY', "
            "'DATE', 'TIME', 'DATE_TIME', 'SCIENTIFIC'"
        ),
    )
    pattern: str | None = Field(
        None,
        description="Custom pattern string, e.g. '#,##0.00' or 'yyyy-mm-dd'",
    )

    def to_api_dict(self) -> dict[str, object]:
        """
        Render this NumberFormat as the Sheets API's wire shape.

        Returns:
            The Sheets API `NumberFormat` dict.
        """
        result: dict[str, object] = {"type": self.type}
        if self.pattern is not None:
            result["pattern"] = self.pattern
        return result

    @classmethod
    def from_api_dict(cls, data: dict[str, object]) -> "NumberFormat":
        """
        Parse a Sheets API `NumberFormat` dict back into a `NumberFormat`.

        Args:
            data: A dict shaped like `{"type": "CURRENCY", "pattern":
                "$#,##0.00"}`.

        Returns:
            The parsed NumberFormat.
        """
        fmt_type = data.get("type", "")
        pattern = data.get("pattern")
        return cls(
            type=str(fmt_type) if isinstance(fmt_type, str) else "",
            pattern=str(pattern) if isinstance(pattern, str) else None,
        )


class TextFormat(BaseModel):
    """A cell text-format spec, matching the Sheets API's `TextFormat`
    message shape (9 fields).

    Recurs inside `CellFormat.textFormat` any time a caller wants to
    express cell text styling in a `batchUpdate` request (e.g.
    `RepeatCellRequest.cell.userEnteredFormat.textFormat`).
    """

    foreground_color: Color | None = Field(
        None, description="Text color (legacy single-color field)"
    )
    font_family: str | None = Field(None, description="Font family, e.g. 'Arial'")
    font_size: int | None = Field(None, description="Font size in points")
    bold: bool | None = Field(None, description="Whether the text is bold")
    italic: bool | None = Field(None, description="Whether the text is italic")
    strikethrough: bool | None = Field(
        None, description="Whether the text has a strikethrough"
    )
    underline: bool | None = Field(None, description="Whether the text is underlined")
    link_uri: str | None = Field(
        None, description="Hyperlink URI, if this text is a link"
    )
    foreground_color_style: Color | None = Field(
        None,
        description=(
            "Text color (newer ColorStyle field). Kept alongside the legacy "
            "foreground_color per the API's own coexistence of both fields "
            "-- writers should set one, not both."
        ),
    )

    def to_api_dict(self) -> dict[str, object]:
        """
        Render this TextFormat as the Sheets API's wire shape (camelCase
        keys), omitting any field left unset.

        Returns:
            The Sheets API `TextFormat` dict.
        """
        result: dict[str, object] = {}
        if self.foreground_color is not None:
            result["foregroundColor"] = self.foreground_color.to_api_dict()
        if self.font_family is not None:
            result["fontFamily"] = self.font_family
        if self.font_size is not None:
            result["fontSize"] = self.font_size
        if self.bold is not None:
            result["bold"] = self.bold
        if self.italic is not None:
            result["italic"] = self.italic
        if self.strikethrough is not None:
            result["strikethrough"] = self.strikethrough
        if self.underline is not None:
            result["underline"] = self.underline
        if self.link_uri is not None:
            result["link"] = {"uri": self.link_uri}
        if self.foreground_color_style is not None:
            result["foregroundColorStyle"] = {
                "rgbColor": self.foreground_color_style.to_api_dict()
            }
        return result

    @classmethod
    def from_api_dict(cls, data: dict[str, object]) -> "TextFormat":
        """
        Parse a Sheets API `TextFormat` dict back into a `TextFormat`.

        Args:
            data: A dict shaped like `{"bold": true, "fontSize": 12, ...}`.

        Returns:
            The parsed TextFormat.
        """
        fg_color = data.get("foregroundColor")
        fg_color_style = data.get("foregroundColorStyle")
        link = data.get("link")
        link_uri = (
            link.get("uri")
            if isinstance(link, dict) and isinstance(link.get("uri"), str)
            else None
        )
        rgb_style = (
            fg_color_style.get("rgbColor") if isinstance(fg_color_style, dict) else None
        )
        font_family_value = data.get("fontFamily")
        font_size_value = data.get("fontSize")
        bold_value = data.get("bold")
        italic_value = data.get("italic")
        strikethrough_value = data.get("strikethrough")
        underline_value = data.get("underline")
        return cls(
            foreground_color=(
                Color.from_api_dict(fg_color) if isinstance(fg_color, dict) else None
            ),
            font_family=(
                font_family_value if isinstance(font_family_value, str) else None
            ),
            font_size=(
                int(font_size_value) if isinstance(font_size_value, int) else None
            ),
            bold=bold_value if isinstance(bold_value, bool) else None,
            italic=italic_value if isinstance(italic_value, bool) else None,
            strikethrough=(
                strikethrough_value if isinstance(strikethrough_value, bool) else None
            ),
            underline=(underline_value if isinstance(underline_value, bool) else None),
            link_uri=link_uri,
            foreground_color_style=(
                Color.from_api_dict(rgb_style) if isinstance(rgb_style, dict) else None
            ),
        )
