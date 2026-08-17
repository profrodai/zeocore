"""
Tests for zeo_core.core.mime — MIME type and binary-detection utilities.

quackverse-coverage-90: this module carried 0% coverage (12 stmts, 0 tests) before
this file. Every assertion below calls the real production function directly
(no mocks, no stand-ins) and asserts on its actual return value.
"""

from zeo_core.core.mime import (
    BINARY_EXTENSIONS,
    TEXT_EXTENSIONS,
    get_content_type,
    is_binary_extension,
    is_text_extension,
)


class TestIsBinaryExtension:
    """Tests for is_binary_extension()."""

    def test_known_binary_extension_with_dot(self) -> None:
        assert is_binary_extension(".pdf") is True

    def test_known_binary_extension_without_dot(self) -> None:
        assert is_binary_extension("png") is True

    def test_known_text_extension_is_not_binary(self) -> None:
        assert is_binary_extension(".txt") is False

    def test_svg_is_not_binary(self) -> None:
        # SVG is text/XML despite being an image format — explicitly excluded
        # from BINARY_EXTENSIONS in the module itself.
        assert is_binary_extension("svg") is False

    def test_case_insensitive(self) -> None:
        assert is_binary_extension(".PDF") is True
        assert is_binary_extension("PNG") is True

    def test_unknown_extension_is_not_binary(self) -> None:
        assert is_binary_extension(".notarealext") is False

    def test_empty_string_is_not_binary(self) -> None:
        assert is_binary_extension("") is False

    def test_every_declared_binary_extension_round_trips(self) -> None:
        # Level-4: walk the real module-level set, not a hand-copied list,
        # so this stays correct if BINARY_EXTENSIONS is ever edited.
        for ext in BINARY_EXTENSIONS:
            assert is_binary_extension(ext) is True
            assert is_binary_extension(f".{ext}") is True
            assert is_binary_extension(ext.upper()) is True


class TestIsTextExtension:
    """Tests for is_text_extension()."""

    def test_known_text_extension_with_dot(self) -> None:
        assert is_text_extension(".py") is True

    def test_known_text_extension_without_dot(self) -> None:
        assert is_text_extension("json") is True

    def test_binary_extension_is_not_text(self) -> None:
        assert is_text_extension(".pdf") is False

    def test_case_insensitive(self) -> None:
        assert is_text_extension(".MD") is True

    def test_unknown_extension_is_not_text(self) -> None:
        assert is_text_extension(".notarealext") is False

    def test_binary_and_text_sets_are_disjoint(self) -> None:
        # A behavioral invariant the module's own docstring claims
        # ("NOT just 'not binary'") — assert it holds against the real sets.
        assert BINARY_EXTENSIONS.isdisjoint(TEXT_EXTENSIONS)

    def test_every_declared_text_extension_round_trips(self) -> None:
        for ext in TEXT_EXTENSIONS:
            assert is_text_extension(ext) is True
            assert is_text_extension(f".{ext}") is True
            assert is_binary_extension(ext) is False


class TestGetContentType:
    """Tests for get_content_type()."""

    def test_json_extension(self) -> None:
        assert get_content_type(".json") == "application/json"

    def test_png_without_dot(self) -> None:
        assert get_content_type("png") == "image/png"

    def test_unknown_extension_falls_back_to_octet_stream(self) -> None:
        assert get_content_type(".unknown") == "application/octet-stream"

    def test_case_insensitive(self) -> None:
        assert get_content_type(".JSON") == "application/json"

    def test_docx_office_open_xml_type(self) -> None:
        assert (
            get_content_type("docx")
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_svg_is_image_svg_xml_not_binary_octet_stream(self) -> None:
        # Confirms get_content_type and is_binary_extension agree on SVG's
        # special-cased text nature.
        assert get_content_type("svg") == "image/svg+xml"
        assert is_binary_extension("svg") is False

    def test_empty_extension_falls_back_to_octet_stream(self) -> None:
        assert get_content_type("") == "application/octet-stream"
