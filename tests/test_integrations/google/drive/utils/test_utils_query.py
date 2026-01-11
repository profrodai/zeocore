# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_integrations/google/drive/utils/test_utils_query.py
# role: utils
# neighbors: __init__.py, test_utils_api.py
# exports: TestDriveUtilsQuery
# git_branch: feat/9-make-setup-work
# git_commit: e6c6b5b8
# === QV-LLM:END ===

"""
Tests for Google Drive api query module.
"""

from quack_core.integrations.google.drive.utils import query


class TestDriveUtilsQuery:
    """Tests for Google Drive api query functions."""

    def test_build_query_with_folder_id(self) -> None:
        """Test building a query string with folder ID."""
        result = query.build_query(folder_id="folder123")

        assert "'folder123' in parents" in result
        assert "trashed = false" in result
        assert "and" in result  # Should join conditions with 'and'

    def test_build_query_without_folder_id(self) -> None:
        """Test building a query string without folder ID."""
        result = query.build_query()

        assert "trashed = false" in result
        assert "in parents" not in result  # Should not have parent condition

    def test_build_query_with_wildcard_pattern(self) -> None:
        """Test building a query string with wildcard pattern."""
        result = query.build_query(pattern="*.txt")

        assert "name contains '.txt'" in result
        assert "trashed = false" in result

    def test_build_query_with_exact_pattern(self) -> None:
        """Test building a query string with exact pattern."""
        result = query.build_query(pattern="document.txt")

        assert "name = 'document.txt'" in result
        assert "trashed = false" in result

    def test_build_query_with_empty_wildcard_pattern(self) -> None:
        """Test building a query string with empty wildcard pattern."""
        result = query.build_query(pattern="*")

        assert "name contains ''" in result
        assert "trashed = false" in result

    def test_build_query_with_complex_pattern(self) -> None:
        """Test building a query string with complex wildcard pattern."""
        result = query.build_query(pattern="report*.pdf")

        assert "name contains 'report'" in result
        assert "trashed = false" in result

    def test_build_query_all_parameters(self) -> None:
        """Test building a query string with all parameters."""
        result = query.build_query(folder_id="folder123", pattern="*.txt")

        assert "'folder123' in parents" in result
        assert "name contains '.txt'" in result
        assert "trashed = false" in result
        assert result.count("and") == 2  # Should have two 'and' connectors

    def test_build_file_fields_basic(self) -> None:
        """Test building a fields parameter string without permissions."""
        result = query.build_file_fields(include_permissions=False)

        assert result.startswith("files(")
        assert result.endswith(")")
        assert "id" in result
        assert "name" in result
        assert "mimeType" in result
        assert "permissions" not in result

    def test_build_file_fields_with_permissions(self) -> None:
        """Test building a fields parameter string with permissions."""
        result = query.build_file_fields(include_permissions=True)

        assert result.startswith("files(")
        assert result.endswith(")")
        assert "id" in result
        assert "name" in result
        assert "mimeType" in result
        assert "permissions" in result
        assert "permissions(id,type,role" in result  # Should include permission fields
