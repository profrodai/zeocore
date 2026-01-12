# === QV-LLM:BEGIN ===
# path: scripts/verify_installation.py
# role: module
# neighbors: annotate_headers.py, fix_imports.py, fix_remaining_tests.py, flatten.py
# exports: check_package, main
# git_branch: feat/9-make-setup-work
# git_commit: 1a3eba04
# === QV-LLM:END ===

# verify_installation.py
"""Verify that all packages are correctly installed."""

import sys
import importlib.util


def check_package(package_name):
    """Check if a package is properly installed and importable."""
    try:
        # Import the package
        package = importlib.import_module(package_name)
        package_path = package.__file__
        print(f"✅ {package_name} is installed at: {package_path}")

        # Check expected submodules
        if package_name == 'quack-core':
            submodules = ["config", "fs", "modules"]
            for submodule in submodules:
                try:
                    full_name = f"{package_name}.{submodule}"
                    mod = importlib.import_module(full_name)
                    print(f"  - Submodule {full_name} found at: {mod.__file__}")
                except ImportError as e:
                    print(f"  - ❌ Failed to import {full_name}: {e}")

        return True
    except ImportError as e:
        print(f"❌ {package_name} could not be imported: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error importing {package_name}: {e}")
        return False


def main():
    """Check all packages in the monorepo."""
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print("Python path:")
    for path in sys.path:
        print(f"  - {path}")

    print("\nChecking packages...")
    packages = ["quack-core", "quack-chat", "quackster"]
    all_ok = True

    for package in packages:
        if not check_package(package):
            all_ok = False

    if all_ok:
        print("\n✅ All packages are correctly installed!")
        return 0
    else:
        print("\n❌ Some packages have installation issues.")
        return 1


if __name__ == "__main__":
    sys.exit(main())