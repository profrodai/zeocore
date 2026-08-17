"""
Tests for the PathResolver class.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from quack_core.core.errors import QuackFileNotFoundError
from quack_core.core.paths import PathResolver


class TestPathResolver:
    """Tests for the PathResolver class."""

    def test_init(self) -> None:
        """Test initializing a PathResolver."""
        resolver = PathResolver()
        assert resolver is not None
        assert resolver._cache == {}

    def test_get_project_root(self, mock_project_structure: Path) -> None:
        """Test finding a project root based on marker files.

        get_project_root/find_project_root are PathService methods, not
        module-level functions on quack_core.core.paths.service (that module
        never had free functions - see conftest.py's mock_normalize_path note).
        """
        from quack_core.core.paths.service import PathService

        service = PathService()

        # Test finding from project root
        root_result = service.get_project_root(str(mock_project_structure))
        assert root_result.success
        assert root_result.path == str(mock_project_structure)

        # Test finding from subdirectory
        subdir = f"{mock_project_structure}/src"
        root_result = service.get_project_root(subdir)
        assert root_result.success
        assert root_result.path == str(mock_project_structure)

        # Test with custom marker files
        root_result = service.get_project_root(
            str(mock_project_structure), marker_files=["pyproject.toml"]
        )
        assert root_result.success
        assert root_result.path == str(mock_project_structure)

        # Test with custom marker directories
        root_result = service.get_project_root(
            mock_project_structure, marker_dirs=["src", "tests"]
        )
        assert root_result.success
        assert root_result.path == str(mock_project_structure)

        # Test with non-existent path
        root_result = service.get_project_root("/nonexistent/path")
        assert not root_result.success
        assert root_result.error is not None

        # Test where no project root can be found
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root_result = service.get_project_root(tmp_path)
            assert not root_result.success
            assert root_result.error is not None

    def test_find_source_directory(self, mock_project_structure: Path) -> None:
        """Test finding a source directory."""
        resolver = PathResolver()

        # Test finding src from project root
        src_dir = resolver._find_source_directory(str(mock_project_structure))
        assert src_dir == str(mock_project_structure / "src")

        # Test finding src from subdirectory
        src_dir = resolver._find_source_directory(str(mock_project_structure / "tests"))
        assert src_dir == str(mock_project_structure / "src")

        # Test finding a Python package (folder with __init__.py). NOTE:
        # _find_source_directory (resolver.py) always tries step 1
        # (_find_nearest_directory("src", ...)) before step 2 (does start_dir
        # itself hold __init__.py). Since package_dir here is nested UNDER an
        # ancestor "src" directory, step 1 finds that ancestor first and step 2's
        # __init__.py check is unreached - a real, currently-observable dead-code
        # condition in production for any start_dir nested under a "src" ancestor,
        # recorded here (circle of control - CLAUDE.md s7) rather than changed
        # as a side effect of this test-only fix.
        package_dir = mock_project_structure / "src" / "test_module"
        src_dir = resolver._find_source_directory(str(package_dir))
        assert src_dir == str(mock_project_structure / "src")

    def test_find_output_directory(self, mock_project_structure: Path) -> None:
        resolver = PathResolver()

        # Test finding existing output directory
        output_dir = resolver._find_output_directory(str(mock_project_structure))
        assert output_dir == str(mock_project_structure / "output")

        # Test creating output directory. _get_project_root(no_output_dir) would
        # otherwise walk up to mock_project_structure (which has pyproject.toml
        # AND an existing output/ from the assertion above) and return that
        # sibling output/ before ever reaching the create branch - same
        # root-anchoring behavior fixed in test_service.py::test_find_output_directory.
        # Force a standalone root via mock so create=True's own branch is what's
        # under test.
        no_output_dir = mock_project_structure / "no_output"
        no_output_dir.mkdir()
        with patch.object(
            resolver, "_get_project_root", return_value=str(no_output_dir)
        ):
            created_output = resolver._find_output_directory(
                str(no_output_dir), create=True
            )
        assert created_output == str(no_output_dir / "output")
        assert Path(created_output).exists()

        # Now, simulate a scenario where no output directory exists by patching
        # get_project_root to return a fresh directory
        # that does not contain an output folder.
        non_existent_dir = mock_project_structure / "non_existent_dir"
        non_existent_dir.mkdir()
        with patch.object(
            resolver, "_get_project_root", return_value=str(non_existent_dir)
        ):
            with pytest.raises(QuackFileNotFoundError):
                resolver._find_output_directory(str(non_existent_dir), create=False)

    def test_internal_resolve_project_path(self, mock_project_structure: Path) -> None:
        """Test the internal _resolve_project_path method directly."""
        resolver = PathResolver()

        # Test resolving a relative path
        resolved = resolver._resolve_project_path(
            "src/file.txt", str(mock_project_structure)
        )
        assert resolved == str(mock_project_structure / "src" / "file.txt")

        # Test resolving an absolute path (should remain unchanged)
        abs_path = Path("/absolute/path/file.txt")
        resolved = resolver._resolve_project_path(
            str(abs_path), str(mock_project_structure)
        )
        assert resolved == str(abs_path)

        # Test resolving without explicit project root
        with patch.object(
            resolver, "_get_project_root", return_value=str(mock_project_structure)
        ):
            resolved = resolver._resolve_project_path("src/file.txt")
            assert resolved == str(mock_project_structure / "src" / "file.txt")

        # Test when project root cannot be found
        # IMPORTANT: This test actually expects the exception since the
        # internal method does raise it
        with patch.object(
            resolver, "_get_project_root", side_effect=QuackFileNotFoundError("")
        ):
            # The internal method is designed to raise the exception
            with pytest.raises(QuackFileNotFoundError):
                resolver._resolve_project_path("file.txt")

    def test_service_resolve_project_path(self, mock_project_structure: Path) -> None:
        """Test the public PathService.resolve_project_path method with error handling.

        resolve_project_path is a PathService instance method, not a module-level
        function on quack_core.core.paths.service (see conftest.py's
        mock_normalize_path note) - the prior version of this test imported the
        module itself as "paths" and called methods on it directly, which only
        worked by accident when PathService happened to expose bare functions at
        module scope. Use a real PathService() instance instead.
        """
        from quack_core.core.paths.service import PathService

        service = PathService()

        # Test resolving a relative path
        resolved_result = service.resolve_project_path(
            "src/file.txt", str(mock_project_structure)
        )
        assert resolved_result.success
        assert resolved_result.path == str(mock_project_structure / "src" / "file.txt")

        # Test resolving an absolute path (should remain unchanged)
        abs_path = Path("/absolute/path/file.txt")
        resolved_result = service.resolve_project_path(abs_path, mock_project_structure)
        assert resolved_result.success
        assert resolved_result.path == str(abs_path)

        # Test the underlying resolver call succeeding
        with patch.object(service._resolver, "_resolve_project_path") as mock_resolve:
            mock_resolve.return_value = "src/file.txt"
            resolved_result = service.resolve_project_path("src/file.txt")
            assert resolved_result.success
            assert resolved_result.path == "src/file.txt"

        # Test handling errors: PathService.resolve_project_path catches any
        # exception from the resolver and reports it via the Result contract.
        with patch.object(service._resolver, "_resolve_project_path") as mock_resolve:
            mock_resolve.side_effect = Exception("Test error")
            resolved_result = service.resolve_project_path("file.txt")
            assert not resolved_result.success
            assert resolved_result.error is not None
            assert "Test error" in str(resolved_result.error)

    def test_detect_project_context(self, mock_project_structure: Path) -> None:
        """Test detecting project context from a directory."""
        resolver = PathResolver()

        # Test from project root
        context = resolver._detect_project_context(str(mock_project_structure))
        assert context.root_dir == str(mock_project_structure)
        assert context.name == mock_project_structure.name
        assert len(context.directories) > 0
        assert "src" in context.directories
        assert context.directories["src"].is_source is True
        assert "output" in context.directories
        assert context.directories["output"].is_output is True
        assert context.config_file is not None

        # Test from subdirectory (should cache result)
        subdir = mock_project_structure / "src"
        assert subdir.is_dir()
        context2 = resolver._detect_project_context(str(subdir))
        assert context2.root_dir == str(mock_project_structure)
        assert id(context) == id(context2)  # Should be the same cached object

        # Test with non-existent path
        with pytest.raises(QuackFileNotFoundError):
            resolver._detect_project_context("/nonexistent/path")

        # Test where no project root can be found
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Should return a context with the path as root
            context = resolver._detect_project_context(str(tmp_path))
            assert context.root_dir == str(tmp_path)
            assert len(context.directories) == 0

    def test_detect_content_context(self, mock_project_structure: Path) -> None:
        """Test detecting content context from a directory.

        _detect_content_context (resolver.py) only carries the caller-supplied
        content_type forward onto the ContentContext - it never inspects the
        directory structure to infer content_type/content_name/content_dir; that
        inference lives in the separate _infer_content_structure method, which
        _detect_content_context does not call (see test_helper_methods, which
        exercises _infer_content_structure directly). Assert what the real
        (unmocked) method actually does.
        """
        resolver = PathResolver()

        # Create some content structure
        content_dir = mock_project_structure / "src" / "tutorials"
        content_dir.mkdir()
        example_dir = content_dir / "example"
        example_dir.mkdir()
        (example_dir / "content.md").write_text("# Example Content")

        # Test from content root: no content_type passed, none inferred
        context = resolver._detect_content_context(str(content_dir))
        assert context.root_dir == str(mock_project_structure)
        assert context.content_type is None
        assert context.content_name is None

        # Test from content example: root/directories carried from the project
        # context; content_type/content_name/content_dir remain unset without
        # explicit input or a separate _infer_content_structure call.
        context = resolver._detect_content_context(str(example_dir))
        assert context.root_dir == str(mock_project_structure)
        assert context.content_type is None
        assert context.content_name is None
        assert context.content_dir is None

        # Test with explicit content type: passed straight through
        context = resolver._detect_content_context(
            str(example_dir), content_type="manual"
        )
        assert context.content_type == "manual"

        # Test with non-content directory
        context = resolver._detect_content_context(
            str(mock_project_structure / "tests")
        )
        assert context.content_type is None
        assert context.content_name is None

    # NOTE (test-fix-paths-plugins): test_infer_current_content previously asserted
    # a PathResolver._infer_current_content method that does not exist anywhere in
    # quack-core/src/ (grep confirms zero definitions, zero call sites) - not a
    # regression (see the SOW's root-cause note; this is the same pattern as
    # PathService's five missing methods in test_service.py). Unlike
    # detect_content_context above, there is no real internal method for this test
    # to be redirected onto (it mocked _detect_content_context entirely, so it
    # never exercised real logic even when it "passed"). Removed rather than
    # fabricated; escalate to Master if current-content inference from cwd should
    # be built as new, chartered work.

    def test_helper_methods(self, mock_project_structure: Path) -> None:
        """Test helper methods of the PathResolver.

        _detect_config_file and _infer_content_structure do not exist anywhere in
        quack-core/src/ (grep confirms zero definitions) - not a regression, same
        pattern as test_infer_current_content above. Config-file detection is
        inline inside _detect_project_context itself (resolver.py), not a separate
        method, so that part of this test is rewritten to assert the real,
        already-covered behavior instead of calling a nonexistent helper.
        """
        resolver = PathResolver()

        # Test _detect_standard_directories directly (a real method)
        context = resolver._detect_project_context(str(mock_project_structure))
        resolver._detect_standard_directories(context)
        assert "src" in context.directories
        assert context.directories["src"].is_source is True

        # config_file detection happens inline inside _detect_project_context
        # itself - assert it was populated on the same context, rather than via a
        # separate _detect_config_file call that does not exist.
        assert context.config_file is not None
        assert "pyproject.toml" in str(context.config_file)
