"""
Helper module to set up the Python path for zeocore tests.
This should be imported at the beginning of conftest.py.
"""

import os
import sys
from pathlib import Path


def setup_python_path() -> None:
    """
    Adds the necessary directories to the Python path.
    """
    # Get the absolute path to the zeocore directory
    zeocore_dir = Path(__file__).parent.parent.absolute()
    src_dir = zeocore_dir / "src"

    # Add src directory to Python path
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # Print current working directory and Python path for debugging
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")

    # Verify that the zeocore module can be found
    try:
        import zeo_core

        print(f"zeocore found at: {zeo_core.__file__}")
    except ImportError as e:
        print(f"Error importing zeocore: {e}")
        # Try a different approach
        try:
            zeo_core_path = os.path.join(str(src_dir), "zeo_core")
            if os.path.exists(zeo_core_path):
                sys.path.insert(0, zeo_core_path)
                print(f"Added zeo_core directory to path: {zeo_core_path}")
        except Exception as e:
            print(f"Failed to add zeocore to path: {e}")


setup_python_path()
