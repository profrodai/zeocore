"""
LOCAL ORCHESTRATOR (DEV ONLY)
Use this to test chains of capabilities without spinning up n8n.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# demo/__init__.py deliberately does not re-export implementations ("DO NOT
# export implementations - they are for reference/testing only"). This is a
# _dev/-only script reaching past that boundary on purpose, per that
# docstring's own "for reference/testing only" carve-out (RULING-277 Bug 1).
from quack_core.contracts.capabilities.demo import EchoRequest
from quack_core.contracts.capabilities.demo._impl import echo_text


def run_flow() -> None:
    print("--- Step 1: Echo with Default Policy ---")
    res1 = echo_text(EchoRequest(text="World"))
    print(f"Status: {res1.status}")
    print(f"Data: {res1.data}")

    print("\n--- Step 2: Echo with 'Angry Duck' Preset ---")
    res2 = echo_text(EchoRequest(text="World", preset="angry_duck"))
    print(f"Status: {res2.status}")
    print(f"Data: {res2.data}")

    print("\n--- Step 3: Echo with Invalid Preset (Expect Error) ---")
    res3 = echo_text(EchoRequest(text="World", preset="missing_preset"))
    print(f"Status: {res3.status}")
    print(f"Error Code: {res3.machine_message}")
    print(f"Message: {res3.human_message}")


if __name__ == "__main__":
    run_flow()
