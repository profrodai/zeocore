# quack-core/examples/config_tooling_test.py
"""
Test script for quack-core.config.tooling.

This is a simple script to test the functionality of the tooling module.
It is not intended to be included in the quack-core package.
"""

from pydantic import Field
from quackcore.config.tooling import (
    QuackToolConfigModel,
    load_tool_config,
    update_tool_config,
    setup_tool_logging,
    get_logger,
)

class MyConfig(QuackToolConfigModel):
    """Example tool-specific config model."""
    name: str = Field("demo")
    log_level: str = Field("DEBUG")

def main():
    """Test the tooling module."""
    # Load the tool config
    config, tool_config = load_tool_config("testtool", MyConfig)
    print(f"Initial tool config: {tool_config}")

    # Update the tool config
    update_tool_config(config, "testtool", {"name": "updated"})
    _, updated_config = load_tool_config("testtool", MyConfig)
    print(f"Updated tool config: {updated_config}")

    # Set up logging
    setup_tool_logging("testtool", tool_config.log_level)
    logger = get_logger("testtool")
    logger.debug("This should print and go to file.")
    logger.info("This is an INFO message.")
    logger.warning("This is a WARNING message.")

if __name__ == "__main__":
    main()