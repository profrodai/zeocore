"""
Data models for Google Slides integration.

Per RULING-408 DESIGN-02 approach B (the typing seam ruling, made concrete
by live measurement against the Slides discovery document, revision
20260828): only the small, closed LEAF types that recur across the
Workspace `batchUpdate` request shapes get real Pydantic models --
`GridRange` (5 fields), `Color` (4), `TextFormat` (9), `NumberFormat` (2).
Everything at the request-kind level (the actual `Request` union members
like `CreateSlideRequest`, `InsertTextRequest`, `UpdateShapePropertiesRequest`,
etc. -- 44 of them for Slides) stays `dict[str, Any]` -- building 44
TypedDicts for the 44 Slides request kinds was explicitly REJECTED by
DESIGN-02 approach C ("a second library") on the same measured-scale ground
that rejected it for Docs' 40 and Sheets' 69.

`Color` is the one leaf type this module models. It is the SAME shared
`Color` message shape already modeled in `google/docs/models.py` (Google's
`Color`/`OptionalColor` wire shape is identical across Docs, Sheets, and
Slides -- see that module's own docstring). It recurs inside Slides'
`ShapeProperties.shapeBackgroundFill`, `PageProperties.pageBackgroundFill`,
`TextStyle.foregroundColor`/`backgroundColor`, and outline/border colors
any time a caller wants to express a solid color in a `batchUpdate`
request. Re-implemented here (not imported from `docs.models`) because
`RULING-408 DESIGN-03` ruled each Workspace API's request-builder package
is its own, not shared -- the same boundary applies to the small leaf
models that travel with it, so `slides` does not reach into `docs` as a
dependency.
"""

from pydantic import BaseModel, Field


class Color(BaseModel):
    """An RGBA color, matching the Google Workspace APIs' shared `Color`
    message shape (`red`/`green`/`blue`/`alpha`, each a float 0-1, `alpha`
    optional and defaulting to fully opaque when omitted by the API).

    This same shape recurs across Slides' `ShapeProperties.
    shapeBackgroundFill.solidFill.color`, `PageProperties.
    pageBackgroundFill.solidFill.color`, `TextStyle.foregroundColor.
    opaqueColor`, outline colors, etc.
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
        Render this Color as the Slides API's wire shape:
        `{"opaqueColor": {"rgbColor": {"red": ..., "green": ..., "blue":
        ...}}}`, with `alpha` folded in as a sibling of `rgbColor` only
        when set (the real API represents alpha this way, matching the
        `docs.models.Color` precedent for the same shared message shape).

        Returns:
            The Slides API `OptionalColor`-style dict for use inside a
            `TextStyle`/`ShapeProperties`/`PageProperties` request payload.
        """
        rgb_color: dict[str, object] = {
            "red": self.red,
            "green": self.green,
            "blue": self.blue,
        }
        opaque_color: dict[str, object] = {"rgbColor": rgb_color}
        if self.alpha is not None:
            opaque_color["alpha"] = self.alpha
        return {"opaqueColor": opaque_color}

    @classmethod
    def from_api_dict(cls, data: dict[str, object]) -> "Color":
        """
        Parse a Slides API `Color`/`OptionalColor` dict back into a
        `Color`.

        Args:
            data: A dict shaped like `{"rgbColor": {"red":.., "green":..,
                "blue":..}, "alpha": ..}` or the `{"opaqueColor": {...}}`-
                wrapped form returned inside `TextStyle`/`ShapeProperties`/
                `PageProperties`.

        Returns:
            The parsed Color.
        """
        # Accept both the wrapped ({"opaqueColor": {...}}) and unwrapped
        # ({"rgbColor": ...}) shapes, since the Slides API uses the wrapped
        # form inside style/properties objects but callers may also hand
        # back the unwrapped inner shape directly.
        inner = data.get("opaqueColor", data)
        rgb = inner.get("rgbColor", {}) if isinstance(inner, dict) else {}
        alpha = inner.get("alpha") if isinstance(inner, dict) else None
        return cls(
            red=float(rgb.get("red", 0.0)) if isinstance(rgb, dict) else 0.0,
            green=float(rgb.get("green", 0.0)) if isinstance(rgb, dict) else 0.0,
            blue=float(rgb.get("blue", 0.0)) if isinstance(rgb, dict) else 0.0,
            alpha=float(alpha) if isinstance(alpha, int | float) else None,
        )
