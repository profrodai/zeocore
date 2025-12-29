

"""
Environment initializer mixin for QuackTool modules.

This module provides a mixin that allows tools to dynamically initialize
their environment by importing and initializing the tool's module.

Changes from original:
- Returns CapabilityResult instead of IntegrationResult
- No runner logic imports
"""

import importlib

from quack_core.contracts import CapabilityResult


class ToolEnvInitializerMixin:
    """
    Mixin that provides dynamic environment initialization for tools.

    This mixin allows tools to dynamically import and initialize
    their environment by importing the tool's module.

    Use case: Tools that need to lazy-load heavy dependencies or
    initialize environment-specific configuration.

    Example:
        ```python
        from quack_core.tools import BaseQuackTool
        from quack_core.tools.mixins import ToolEnvInitializerMixin

        class MyTool(ToolEnvInitializerMixin, BaseQuackTool):
            def initialize(self, ctx):
                # Initialize environment (e.g., import heavy module)
                result = self._initialize_environment("my_heavy_module")
                if not result.status == "success":
                    return result

                return CapabilityResult.ok(
                    data=None,
                    msg="Tool initialized"
                )
        ```
    """

    def _initialize_environment(self, tool_name: str) -> CapabilityResult[None]:
        """
        Dynamically import and initialize the environment for a tool.

        This method attempts to import a module with the given tool name
        and call its initialize() function if available.

        Args:
            tool_name: The name of the tool module to import

        Returns:
            CapabilityResult[None]: Success if initialized, error otherwise

        Example:
            >>> result = self._initialize_environment("my_tool.setup")
            >>> if result.status == "success":
            ...     print("Environment ready")
        """
        try:
            # Attempt to import the tool module
            module = importlib.import_module(tool_name)

            # Check if the module has an initialize function
            if hasattr(module, "initialize") and callable(module.initialize):
                # Call the initialize function
                result = module.initialize()

                # If the function returns a CapabilityResult, return it
                if isinstance(result, CapabilityResult):
                    return result

                # Otherwise, return a success result
                return CapabilityResult.ok(
                    data=None,
                    msg=f"Successfully initialized {tool_name} environment"
                )

            # If no initialize function is found, return a success result
            return CapabilityResult.ok(
                data=None,
                msg=f"Imported {tool_name} module (no initialize function found)"
            )

        except ImportError as e:
            # If the module cannot be imported, return an error result
            return CapabilityResult.fail(
                msg=f"Failed to import {tool_name} module",
                code="QC_CFG_IMPORT_ERROR",
                exception=e
            )
        except Exception as e:
            # If any other error occurs, return an error result
            return CapabilityResult.fail(
                msg=f"Error initializing {tool_name} environment",
                code="QC_CFG_INIT_ERROR",
                exception=e
            )