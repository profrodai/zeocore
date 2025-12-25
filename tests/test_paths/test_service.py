# quack-core/tests/test_paths/test_service.py
"""
Tests for the QuackCore path service.
"""

import os
from unittest.mock import patch

import pytest

from quack_core.paths.api.public.results import ContextResult, PathResult
from quack_core.paths.service import PathService


# Create a fixture for the service
@pytest.fixture
def path_service():
    """Create a PathService instance for testing."""
    return PathService()


def test_get_project_root(tmp_path, path_service):
    """Test getting the project root."""
    # Create a project-like structure
    (tmp_path / "pyproject.toml").write_text("")

    result = path_service.get_project_root(str(tmp_path))

    assert isinstance(result, PathResult)
    assert result.success
    assert result.path == str(tmp_path)
    assert result.error is None


def test_get_project_root_failure(tmp_path, path_service):
    """Test getting the project root when it doesn't exist."""
    # No project markers in this directory
    non_project_dir = tmp_path / "non_project"
    non_project_dir.mkdir()

    result = path_service.get_project_root(str(non_project_dir))

    assert isinstance(result, PathResult)
    assert not result.success
    assert result.path is None
    assert result.error is not None


def test_resolve_project_path(tmp_path, path_service):
    """Test resolving a path relative to the project root."""
    # Create a project-like structure
    (tmp_path / "pyproject.toml").write_text("")

    result = path_service.resolve_project_path("src/module.py", str(tmp_path))

    assert isinstance(result, PathResult)
    assert result.success
    assert result.path == os.path.join(str(tmp_path), "src/module.py")
    assert result.error is None


def test_detect_project_context(tmp_path, path_service):
    """Test detecting the project context."""
    # Create a project-like structure
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "data").mkdir()

    result = path_service.detect_project_context(str(tmp_path))

    assert isinstance(result, ContextResult)
    assert result.success
    assert result.context is not None
    assert result.context.root_dir == str(tmp_path)
    assert len(result.context.directories) >= 3  # At least src, tests, data
    assert result.error is None


def test_detect_content_context(tmp_path, path_service):
    """Test detecting the content context."""
    # Create a project-like structure with content
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "tutorials").mkdir()
    (tmp_path / "src" / "tutorials" / "sample").mkdir()

    result = path_service.detect_content_context(str(tmp_path), "tutorials")

    assert isinstance(result, ContextResult)
    assert result.success
    assert result.context is not None
    assert result.context.root_dir == str(tmp_path)
    assert result.context.content_type == "tutorials"
    assert result.error is None


def test_get_known_directory(tmp_path, path_service):
    """Test getting a known directory."""
    # Create a project-like structure
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "src").mkdir()

    with patch.object(path_service, "detect_project_context") as mock_detect:
        # Mock the detect_project_context method to return a context with a known directory
        from quack_core.paths._internal.context import ProjectContext

        context = ProjectContext(root_dir=str(tmp_path))
        src_dir = str(tmp_path / "src")
        context._add_directory("src", src_dir, is_source=True)
        mock_detect.return_value = ContextResult(success=True, context=context)

        result = path_service.get_known_directory("src")

        assert isinstance(result, PathResult)
        assert result.success
        assert result.path == src_dir
        assert result.error is None


def test_get_module_path(tmp_path, path_service):
    """Test getting a module path."""
    # Create a project-like structure with a module
    (tmp_path / "pyproject.toml").write_text("")
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    module_dir = src_dir / "mymodule"
    module_dir.mkdir()
    (module_dir / "__init__.py").write_text("")
    utils_dir = module_dir / "utils"
    utils_dir.mkdir()
    (utils_dir / "__init__.py").write_text("")
    (utils_dir / "helper.py").write_text("")

    with patch.object(path_service, "detect_project_context") as mock_detect:
        # Mock the detect_project_context method to return a context with a source directory
        from quack_core.paths._internal.context import ProjectContext

        context = ProjectContext(root_dir=str(tmp_path))
        context._add_directory("src", str(src_dir), is_source=True)
        mock_detect.return_value = ContextResult(success=True, context=context)

        # Test module path resolution with an existing module
        with patch("os.path.exists", return_value=True):
            result = path_service.get_module_path("mymodule.utils.helper")

            assert isinstance(result, PathResult)
            assert result.success
            assert result.path == str(utils_dir / "helper.py")
            assert result.error is None


def test_get_relative_path(tmp_path, path_service):
    """Test getting a relative path."""
    # Create a project-like structure
    (tmp_path / "pyproject.toml").write_text("")

    with patch.object(path_service, "get_project_root") as mock_get_root:
        mock_get_root.return_value = PathResult(success=True, path=str(tmp_path))

        # Test relative path resolution
        abs_path = os.path.join(str(tmp_path), "src/module.py")
        result = path_service.get_relative_path(abs_path)

        assert isinstance(result, PathResult)
        assert result.success
        assert result.path == "src/module.py" or result.path == os.path.join(
            "src", "module.py"
        )
        assert result.error is None


def test_get_content_dir(tmp_path, path_service):
    """Test getting a content directory."""
    # Create a project-like structure with content
    (tmp_path / "pyproject.toml").write_text("")
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    tutorials_dir = src_dir / "tutorials"
    tutorials_dir.mkdir()
    sample_dir = tutorials_dir / "sample"
    sample_dir.mkdir()

    with patch.object(path_service, "detect_project_context") as mock_detect:
        # Mock the detect_project_context method to return a context with a source directory
        from quack_core.paths._internal.context import ProjectContext

        context = ProjectContext(root_dir=str(tmp_path))
        context._add_directory("src", str(src_dir), is_source=True)
        mock_detect.return_value = ContextResult(success=True, context=context)

        # Test content directory resolution
        with patch("os.path.isdir", return_value=True):
            result = path_service.get_content_dir("tutorials", "sample")

            assert isinstance(result, PathResult)
            assert result.success
            assert result.path == str(sample_dir)
            assert result.error is None


def test_list_known_directories(tmp_path, path_service):
    """Test listing known directories."""
    # Create a project-like structure
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "data").mkdir()

    with patch.object(path_service, "detect_project_context") as mock_detect:
        # Mock the detect_project_context method to return a context with known directories
        from quack_core.paths._internal.context import ProjectContext

        context = ProjectContext(root_dir=str(tmp_path))
        context._add_directory("src", str(tmp_path / "src"), is_source=True)
        context._add_directory("tests", str(tmp_path / "tests"), is_test=True)
        context._add_directory("data", str(tmp_path / "data"), is_data=True)
        mock_detect.return_value = ContextResult(success=True, context=context)

        # Test listing known directories
        result = path_service.list_known_directories()

        assert isinstance(result, list)
        assert set(result) == {"src", "tests", "data"}


def test_is_inside_project(tmp_path, path_service):
    """Test checking if a path is inside the project."""
    # Create a project-like structure
    (tmp_path / "pyproject.toml").write_text("")

    with patch.object(path_service, "get_project_root") as mock_get_root:
        mock_get_root.return_value = PathResult(success=True, path=str(tmp_path))

        # Test inside path
        inside_path = os.path.join(str(tmp_path), "src/module.py")
        assert path_service.is_inside_project(inside_path)

        # Test outside path
        outside_path = "/some/other/path"
        assert not path_service.is_inside_project(outside_path)


def test_resolve_content_module(tmp_path, path_service):
    """Test resolving a content module."""
    # Create a project-like structure with content
    (tmp_path / "pyproject.toml").write_text("")
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    with patch.object(path_service, "detect_content_context") as mock_detect:
        # Mock the detect_content_context method to return a context with a source directory
        from quack_core.paths._internal.context import ContentContext

        context = ContentContext(root_dir=str(tmp_path))
        context._add_directory("src", str(src_dir), is_source=True)
        mock_detect.return_value = ContextResult(success=True, context=context)

        # Mock the _infer_module_from_path function
        with patch(
            "quack_core.paths._internal.utils._infer_module_from_path",
            return_value="tutorials.sample.intro",
        ):
            # Test content module resolution
            result = path_service.resolve_content_module(
                os.path.join(str(src_dir), "tutorials/sample/intro.py")
            )

            assert isinstance(result, PathResult)
            assert result.success
            assert result.path == "tutorials.sample.intro"
            assert result.error is None


def test_path_exists_in_known_dir(tmp_path, path_service):
    """Test checking if a path exists in a known directory."""
    # Create a project-like structure with assets
    (tmp_path / "pyproject.toml").write_text("")
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "images").mkdir()
    (assets_dir / "images" / "logo.png").write_text("")

    with patch.object(path_service, "get_known_directory") as mock_get_dir:
        mock_get_dir.return_value = PathResult(success=True, path=str(assets_dir))

        # Test existing path
        with patch("os.path.exists", return_value=True):
            assert path_service.path_exists_in_known_dir("assets", "images/logo.png")

        # Test non-existing path
        with patch("os.path.exists", return_value=False):
            assert not path_service.path_exists_in_known_dir(
                "assets", "images/missing.png"
            )


def test_find_source_directory(tmp_path, path_service):
    """Test finding the source directory."""
    # Create a project-like structure
    (tmp_path / "pyproject.toml").write_text("")
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    with patch.object(
        path_service._resolver, "_find_source_directory", return_value=str(src_dir)
    ):
        result = path_service.find_source_directory(str(tmp_path))

        assert isinstance(result, PathResult)
        assert result.success
        assert result.path == str(src_dir)
        assert result.error is None


def test_find_output_directory(tmp_path, path_service):
    """Test finding or creating the output directory."""
    # Create a project-like structure
    (tmp_path / "pyproject.toml").write_text("")
    output_dir = tmp_path / "output"

    # Test finding an existing output directory
    with patch.object(
        path_service._resolver, "_find_output_directory", return_value=str(output_dir)
    ):
        result = path_service.find_output_directory(str(tmp_path))

        assert isinstance(result, PathResult)
        assert result.success
        assert result.path == str(output_dir)
        assert result.error is None

    # Test creating a new output directory
    with patch.object(
        path_service._resolver,
        "_find_output_directory",
        side_effect=lambda start_dir, create: str(output_dir)
        if create
        else ValueError("Not found"),
    ):
        # Without create flag (should fail)
        result = path_service.find_output_directory(str(tmp_path), create=False)
        assert not result.success
        assert result.error is not None

        # With create flag (should succeed)
        result = path_service.find_output_directory(str(tmp_path), create=True)
        assert result.success
        assert result.path == str(output_dir)
        assert result.error is None


def test_infer_current_content(tmp_path, path_service):
    """Test inferring current content type and name."""
    # Create a project-like structure with content
    (tmp_path / "pyproject.toml").write_text("")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "tutorials").mkdir()
    (tmp_path / "src" / "tutorials" / "sample").mkdir()

    expected_result = {"type": "tutorials", "name": "sample"}

    with patch.object(
        path_service._resolver, "_infer_current_content", return_value=expected_result
    ):
        result = path_service.infer_current_content(str(tmp_path))

        assert isinstance(result, dict)
        assert result == expected_result
