# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/toolkit/mixins/env_init.py
# module: quack_core.toolkit.mixins.env_init
# role: module
# neighbors: __init__.py, integration_enabled.py, lifecycle.py, output_handler.py
# exports: ToolEnvInitializerMixin
# git_branch: refactor/newHeaders
# git_commit: 72778e2
# === QV-LLM:END ===

"""
Environment initializer mixin for QuackTool plugins.

This module provides a mixin that allows tools to dynamically initialize
their environment by importing and initializing the tool's module.
"""

import importlib

from quack_core.integrations.core import IntegrationResult


class ToolEnvInitializerMixin:
    """
    Mixin that provides dynamic environment initialization for tools.

    This mixin allows tools to dynamically import and initialize
    their environment by importing the tool's module.
    """

    def _initialize_environment(self, tool_name: str) -> IntegrationResult:
        """
        Dynamically import and initialize the environment for a tool.

        This method attempts to import a module with the given tool name
        and call its initialize() function if available.

        Args:
            tool_name: The name of the tool module to import

        Returns:
            IntegrationResult: Result of the initialization process
        """
        try:
            # Attempt to import the tool module
            module = importlib.import_module(tool_name)

            # Check if the module has an initialize function
            if hasattr(module, "initialize") and callable(module.initialize):
                # Call the initialize function
                result = module.initialize()

                # If the function returns an IntegrationResult, return it
                if isinstance(result, IntegrationResult):
                    return result

                # Otherwise, return a success result
                return IntegrationResult.success_result(
                    message=f"Successfully initialized {tool_name} environment"
                )

            # If no initialize function is found, return a success result
            return IntegrationResult.success_result(
                message=f"Imported {tool_name} module (no initialize function found)"
            )

        except ImportError as e:
            # If the module cannot be imported, return an error result
            return IntegrationResult.error_result(
                error=str(e),
                message=f"Failed to import {tool_name} module"
            )
        except Exception as e:
            # If any other error occurs, return an error result
            return IntegrationResult.error_result(
                error=str(e),
                message=f"Error initializing {tool_name} environment"
            )
