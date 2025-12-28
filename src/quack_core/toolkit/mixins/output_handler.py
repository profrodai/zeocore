# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/toolkit/mixins/output_handler.py
# module: quack_core.toolkit.mixins.output_handler
# role: module
# neighbors: __init__.py, env_init.py, integration_enabled.py, lifecycle.py
# exports: OutputFormatMixin
# git_branch: refactor/newHeaders
# git_commit: 98b2a5c
# === QV-LLM:END ===

"""
This mixin allows tools to specify the output file extension
(e.g., '.json', '.yaml'), by overriding the `_get_output_extension()` method.
If more complex control is needed (different OutputWriter classes),
tools should override `get_output_writer()` directly in BaseQuackToolPlugin.
"""


from quack_core.workflow.output import OutputWriter


class OutputFormatMixin:
    """
    Mixin that provides customization of output format for QuackTool plugins.

    This mixin allows tools to specify the output format and customize
    how their output is written.
    """

    def _get_output_extension(self) -> str:
        """
        Get the file extension for output files.

        Override this method to return a different extension if needed.

        Returns:
            str: File extension (with leading dot) for output files
        """
        return ".json"

    def get_output_writer(self) -> OutputWriter | None:
        """
        Get the output writer for this tool.

        Override this method to return a custom OutputWriter if the tool wants.
        By default, returns None which means the default writer will be used
        with the extension from _get_output_extension().

        Returns:
            OutputWriter | None: The output writer to use, or None for default
        """
        return None
