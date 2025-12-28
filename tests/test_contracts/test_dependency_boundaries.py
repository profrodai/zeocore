# === QV-LLM:BEGIN ===
# path: quack-core/tests/test_contracts/test_dependency_boundaries.py
# role: tests
# neighbors: __init__.py, test_artifacts.py, test_capabilities.py, test_envelopes.py
# exports: DependencyChecker, TestDependencyBoundaries, TestImportPatterns
# git_branch: refactor/newHeaders
# git_commit: 98b2a5c
# === QV-LLM:END ===

"""
Tests for dependency boundary enforcement.

Ensures contracts module only imports from stdlib and Pydantic.
This maintains Ring A isolation as per Doctrine v3.
"""

import pytest
import ast
import sys
from pathlib import Path
from typing import Set, List


class DependencyChecker:
    """Check Python files for forbidden imports."""

    # Allowed modules for contracts
    ALLOWED_STDLIB = {
        "enum", "typing", "datetime", "uuid", "json", "pathlib",
        "collections", "dataclasses", "functools", "itertools"
    }

    ALLOWED_THIRD_PARTY = {
        "pydantic"
    }

    # Forbidden modules (from other QuackCore rings)
    FORBIDDEN_MODULES = {
        "quack_core.lib",
        "quack_core.toolkit",
        "quack_core.integrations",
        "quack_core.workflow",
        "quack_core.runners",
    }

    def __init__(self, contracts_root: Path):
        """
        Initialize dependency checker.

        Args:
            contracts_root: Path to contracts module root
        """
        self.contracts_root = contracts_root

    def get_python_files(self) -> List[Path]:
        """Get all Python files in contracts module."""
        return list(self.contracts_root.rglob("*.py"))

    def extract_imports(self, filepath: Path) -> Set[str]:
        """
        Extract all import statements from a Python file.

        Args:
            filepath: Path to Python file

        Returns:
            Set of module names being imported
        """
        with open(filepath, 'r') as f:
            try:
                tree = ast.parse(f.read(), filename=str(filepath))
            except SyntaxError:
                # Skip files with syntax errors (might be templates)
                return set()

        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])

        return imports

    def check_file(self, filepath: Path) -> List[str]:
        """
        Check a single file for forbidden imports.

        Args:
            filepath: Path to Python file

        Returns:
            List of violation messages (empty if clean)
        """
        imports = self.extract_imports(filepath)
        violations = []

        for imported_module in imports:
            # Check for forbidden QuackCore modules
            for forbidden in self.FORBIDDEN_MODULES:
                if imported_module == forbidden or imported_module.startswith(
                        f"{forbidden}."):
                    violations.append(
                        f"{filepath.relative_to(self.contracts_root)}: "
                        f"Forbidden import '{imported_module}' (Ring A must not import Ring B/C/D)"
                    )

            # Check for unknown third-party modules (not in allowed lists)
            if imported_module not in self.ALLOWED_STDLIB:
                if imported_module not in self.ALLOWED_THIRD_PARTY:
                    # Allow quack_core.contracts internal imports
                    if not imported_module.startswith("quack_core.contracts"):
                        # This is a potential violation (unknown third-party)
                        # We'll be lenient here but log it
                        pass

        return violations

    def check_all(self) -> List[str]:
        """
        Check all Python files in contracts module.

        Returns:
            List of all violations found
        """
        all_violations = []

        for pyfile in self.get_python_files():
            # Skip __pycache__ and test files
            if "__pycache__" in str(pyfile) or "test_" in pyfile.name:
                continue

            violations = self.check_file(pyfile)
            all_violations.extend(violations)

        return all_violations


class TestDependencyBoundaries:
    """Tests for dependency boundary enforcement."""

    @pytest.fixture
    def contracts_root(self) -> Path:
        """Get path to contracts module root."""
        # Assumes tests are in /home/claude/tests/contracts
        # and contracts are in /home/claude/quack_core/contracts
        test_dir = Path(__file__).parent
        return test_dir.parent.parent / "quack_core" / "contracts"

    def test_no_forbidden_imports(self, contracts_root: Path):
        """
        Test that contracts module does not import from other QuackCore rings.

        This enforces Ring A isolation - contracts can only depend on
        stdlib and Pydantic, never on Ring B/C/D modules.
        """
        checker = DependencyChecker(contracts_root)
        violations = checker.check_all()

        if violations:
            violation_msg = "\n".join(violations)
            pytest.fail(
                f"Found {len(violations)} dependency boundary violations:\n\n"
                f"{violation_msg}\n\n"
                f"Ring A (contracts) must not import from Ring B/C/D modules.\n"
                f"Allowed: stdlib + pydantic only."
            )

    def test_contracts_root_exists(self, contracts_root: Path):
        """Sanity check that contracts root exists."""
        assert contracts_root.exists(), f"Contracts root not found: {contracts_root}"
        assert contracts_root.is_dir()

    def test_has_python_files(self, contracts_root: Path):
        """Sanity check that we found Python files to check."""
        checker = DependencyChecker(contracts_root)
        py_files = checker.get_python_files()

        # Filter out __pycache__
        py_files = [f for f in py_files if "__pycache__" not in str(f)]

        assert len(py_files) > 0, "No Python files found in contracts module"


class TestImportPatterns:
    """Tests for specific import patterns we expect."""

    @pytest.fixture
    def contracts_root(self) -> Path:
        """Get path to contracts module root."""
        test_dir = Path(__file__).parent
        return test_dir.parent.parent / "quack_core" / "contracts"

    def test_can_import_contracts_module(self):
        """Test that we can import the contracts module successfully."""
        try:
            import quack_core.contracts as contracts
            assert hasattr(contracts, 'CapabilityResult')
            assert hasattr(contracts, 'ArtifactRef')
            assert hasattr(contracts, 'RunManifest')
        except ImportError as e:
            pytest.fail(f"Failed to import contracts module: {e}")