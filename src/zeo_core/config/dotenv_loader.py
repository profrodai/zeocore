"""
Explicit `.env` loading for zeo_core.

RULING-407 item 4 (zeocore org corpus, 2026-08-31): `.env.example` has always
called `.env` "the documented home for secrets in ZeoCore," but nothing in
`src/` imported `dotenv` and `python-dotenv` was not a declared dependency --
the documented path was inert. RULING-356 s5 deferred making it real to a
charter that never took it up; RULING-407 closes that deferral: `.env` SHALL
actually load.

This is a SEPARATE, explicitly-called function, not import-time behavior --
matching zeo_core.config's own stated Kernel philosophy ("no implicit I/O on
import," see config/__init__.py's module docstring) and loader.py's own
"contains NO side effects... other than reading the config file" contract,
which mutating os.environ would violate if folded into that module. Call
`load_dotenv_file()` once, early, in your own entrypoint -- the same place
GET-STARTED.md already told you to call `uv run --env-file .env` or your own
`python-dotenv` snippet. This function IS that snippet, shipped.
"""

from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from zeo_core.core.logging import get_logger

logger = get_logger(__name__)


def load_dotenv_file(
    dotenv_path: str | Path | None = None, *, override: bool = False
) -> bool:
    """
    Load a `.env` file's contents into the process environment.

    Args:
        dotenv_path: Explicit path to a `.env` file. If None (the default),
            searches upward from the current working directory for a file
            named `.env`, exactly as `.env.example`'s own documented
            location implies -- matching `python-dotenv`'s own
            `find_dotenv()` default search.
        override: If True, values in the `.env` file overwrite variables
            already present in the process environment. Defaults to False,
            matching `python-dotenv`'s own default -- a value a caller
            already set explicitly (e.g. in their shell, or their process
            manager) is real signal and should not be silently clobbered by
            a file this function found on its own.

    Returns:
        bool: True if a `.env` file was found and at least one variable was
            set from it, False otherwise (no file found, or file empty).
            Never raises for a missing file -- "no .env present" is a normal,
            expected state (e.g. production deployments that inject secrets
            another way), not an error.
    """
    path = str(dotenv_path) if dotenv_path is not None else find_dotenv(usecwd=True)
    if not path:
        logger.debug("No .env file found; skipping dotenv load")
        return False

    loaded = load_dotenv(dotenv_path=path, override=override)
    if loaded:
        logger.debug(f"Loaded environment variables from {path}")
    return loaded


__all__ = ["load_dotenv_file"]
