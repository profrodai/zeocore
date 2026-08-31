"""
Data models for Google Docs integration.

Per RULING-408 DESIGN-02 approach B (the typing seam ruling): only the small,
closed LEAF types that recur across the Docs API's `batchUpdate` request
shapes get real Pydantic models. Everything at the request-kind level (the
actual `Request` union members like `InsertTextRequest`,
`ReplaceAllTextRequest`, `DeleteContentRangeRequest`, etc.) stays
`dict[str, Any]` -- building 40 TypedDicts for the 40 Docs request kinds was
explicitly REJECTED (approach C, "a second library").

`Color` is the one leaf type modeled here: it recurs repeatedly inside Docs'
`TextStyle`/`ParagraphStyle` structures (e.g. `TextStyle.foregroundColor.
color.rgbColor`, `TextStyle.backgroundColor.color.rgbColor`) any time a
caller wants to express a color in a `batchUpdate` request. It is small (4
fields), closed (Google's `Color` message shape is stable across the Docs,
Sheets, and Slides APIs alike), and genuinely reused -- unlike the 40
request-kind dicts, which are each used in exactly one place and gain
nothing from a dedicated type.
"""

from pydantic import BaseModel, Field


class Color(BaseModel):
    """An RGBA color, matching the Google Workspace APIs' shared `Color`
    message shape (`red`/`green`/`blue`/`alpha`, each a float 0-1, `alpha`
    optional and defaulting to fully opaque when omitted by the API).

    This same shape recurs across Docs' `TextStyle.foregroundColor.color`,
    `TextStyle.backgroundColor.color`, `ParagraphStyle` border colors, etc.
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
        Render this Color as the Docs API's wire shape:
        `{"color": {"rgbColor": {"red": ..., "green": ..., "blue": ...}}}`,
        with `alpha` folded in only when set (the real API represents alpha
        as a sibling key next to `rgbColor`, not nested inside it).

        Returns:
            The Docs API `OptionalColor`-style dict for use inside a
            `TextStyle`/`ParagraphStyle` request payload.
        """
        rgb_color: dict[str, object] = {
            "red": self.red,
            "green": self.green,
            "blue": self.blue,
        }
        color: dict[str, object] = {"rgbColor": rgb_color}
        if self.alpha is not None:
            color["alpha"] = self.alpha
        return {"color": color}

    @classmethod
    def from_api_dict(cls, data: dict[str, object]) -> "Color":
        """
        Parse a Docs API `Color`/`OptionalColor` dict back into a `Color`.

        Args:
            data: A dict shaped like `{"rgbColor": {"red":.., "green":..,
                "blue":..}, "alpha": ..}` or the `{"color": {...}}`-wrapped
                form returned inside `TextStyle`/`ParagraphStyle`.

        Returns:
            The parsed Color.
        """
        # Accept both the wrapped ({"color": {...}}) and unwrapped
        # ({"rgbColor": ...}) shapes, since the Docs API uses the wrapped
        # form inside TextStyle/ParagraphStyle but the unwrapped form
        # elsewhere (e.g. some table border colors).
        inner = data.get("color", data)
        rgb = inner.get("rgbColor", {}) if isinstance(inner, dict) else {}
        alpha = inner.get("alpha") if isinstance(inner, dict) else None
        return cls(
            red=float(rgb.get("red", 0.0)) if isinstance(rgb, dict) else 0.0,
            green=float(rgb.get("green", 0.0)) if isinstance(rgb, dict) else 0.0,
            blue=float(rgb.get("blue", 0.0)) if isinstance(rgb, dict) else 0.0,
            alpha=float(alpha) if isinstance(alpha, int | float) else None,
        )
