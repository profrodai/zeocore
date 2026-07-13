"""Regression tests for Track B forward-fixes.

Locks the two fixes so they cannot silently regress:
  - Item 1 (commit 4253ec39): the Google config's ``_normalize_path`` must
    resolve from ``quack_core.config.loader`` (it was stale-imported from
    ``quack_core.config.models``, which never defined the symbol).
  - Item 2 (commit 8ace0138): ``quack-runner`` is a real installed package;
    ``ToolRunner`` imports with no ``sys.path`` / ``PYTHONPATH`` hack.

Deliberately imports NONE of the pre-existing runner test modules, which
reference an older ``quack_core.workflow`` layout that no longer exists and
fail collection. This file is self-contained so it collects and runs on its
own explicit path.
"""

import importlib
import importlib.metadata


def test_item1_normalize_path_resolves_from_loader() -> None:
    """Item 1: _normalize_path in the Google config must come from config.loader.

    Regression guard for the stale import (config.models never defined it).
    If a future edit re-points the import at config.models, this fails.
    """
    config = importlib.import_module("quack_core.integrations.google.config")
    normalize = config._normalize_path
    assert normalize.__module__ == "quack_core.config.loader", (
        f"_normalize_path resolved from {normalize.__module__!r}, "
        "expected 'quack_core.config.loader' (Item 1 regression)"
    )


def test_item1_normalize_path_single_positional_arg() -> None:
    """Item 1: the call site passes a single positional arg; the loader
    signature (base_dir defaulted) must accept it."""
    config = importlib.import_module("quack_core.integrations.google.config")
    # relative path is normalized against the default base_dir="./"
    assert config._normalize_path("x/y") == "x/y"


def test_item2_toolrunner_imports_without_path_hack() -> None:
    """Item 2: ToolRunner imports from the packaged runner with no path hack.

    The test process has no PYTHONPATH manipulation and no sys.path insert;
    a successful import proves quack-runner is a real installed distribution.
    """
    from quack_runner.workflow import ToolRunner

    assert ToolRunner.__module__ == "quack_runner.workflow.tool_runner"


def test_item2_quack_runner_is_installed_distribution() -> None:
    """Item 2: quack-runner resolves as an installed dist (not a loose dir on
    sys.path). importlib.metadata only sees installed distributions."""
    version = importlib.metadata.version("quack-runner")
    assert version  # non-empty; presence in metadata == properly installed
