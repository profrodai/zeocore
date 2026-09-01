"""
Example: converting between percent-format scripts and Jupyter notebooks
with zeo_core.integrations.jupytext.

Requires the 'jupytext' extra:

    uv pip install "zeocore[jupytext]"

This mirrors how the org's own quackslides app uses jupytext today: author
exercises as plain, diff-friendly ``.py`` files in percent format
(cell-delimited with ``# %%`` markers), then convert them to ``.ipynb`` for
anything that expects a real notebook (nbviewer, Jupyter, Colab, grading
tooling). ``script_to_notebook()`` is the primary, most-used direction --
exactly ``jupytext.reads(text, fmt="py:percent")`` / ``jupytext.writes(nb,
fmt="ipynb")`` under the hood. ``notebook_to_script()`` is its natural
inverse, added so the integration is a real round trip rather than a
one-way tool matching only today's single consumer.

Note on paths: zeo_core.core.fs sandboxes file access to the current
project root by default (allow_absolute=False) -- this example writes its
scratch files under a directory relative to the current working directory,
NOT under the system temp directory (e.g. /tmp or macOS's /var/folders),
which the fs service would correctly reject as outside the sandbox.

Run this file directly, from the repo root:

    uv run examples/jupytext_usage.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

from zeo_core.integrations.jupytext import JupytextIntegration

PERCENT_SCRIPT = """# %% [markdown]
# ## Exercise 1 -- Tool Calling
# Implement a basic tool-calling loop.

# %%
def call_tool(name: str, args: dict) -> str:
    return f"{name}({args})"
"""


def main() -> None:
    """
    Convert a percent-format script to a notebook, then back again.

    Uses a scratch directory relative to cwd (cleaned up at the end) so
    this example is safe to run repeatedly with no lasting side effects.
    """
    scratch_dir = Path("./tmp_jupytext_example")
    scratch_dir.mkdir(exist_ok=True)

    try:
        script_path = scratch_dir / "exercise_01.py"
        script_path.write_text(PERCENT_SCRIPT)

        # The entry-point factory (create_integration()) is typed to
        # return the generic IntegrationProtocol, which does not declare
        # script_to_notebook()/notebook_to_script() -- constructing the
        # concrete class directly keeps this example mypy --strict clean.
        jupytext = JupytextIntegration()
        init_result = jupytext.initialize()
        if not init_result.success:
            print(f"Failed to initialize jupytext integration: {init_result.error}")
            return
        print(f"Jupytext integration initialized: {init_result.message}")

        # script -> notebook (the primary, most-used direction -- this is
        # exactly what quackslides does with its own exercise scripts)
        to_notebook_result = jupytext.script_to_notebook(str(script_path))
        if not to_notebook_result.success:
            print(f"script_to_notebook failed: {to_notebook_result.error}")
            return

        notebook_path = Path(str(to_notebook_result.content))
        print(f"Notebook written to: {notebook_path.name}")
        print(f"Notebook exists on disk: {notebook_path.exists()}")

        notebook_text = notebook_path.read_text()
        has_cells = '"cells"' in notebook_text
        print(f"Notebook is valid JSON with real cells: {has_cells}")

        # notebook -> script (the natural inverse -- round-trips back to
        # percent format by default)
        to_script_result = jupytext.notebook_to_script(str(notebook_path))
        if not to_script_result.success:
            print(f"notebook_to_script failed: {to_script_result.error}")
            return

        round_tripped_path = Path(str(to_script_result.content))
        round_tripped_text = round_tripped_path.read_text()
        preserved = "def call_tool" in round_tripped_text
        print(f"Round-tripped script: {round_tripped_path.name}")
        print(f"Round trip preserved the function: {preserved}")
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
