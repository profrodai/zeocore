# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/_dev/run_local.py
# module: quack_core._dev.run_local
# role: module
# neighbors: __init__.py
# exports: run_flow
# git_branch: feat/9-make-setup-work
# git_commit: de7513d4
# === QV-LLM:END ===

"""
LOCAL ORCHESTRATOR (DEV ONLY)
Use this to test chains of capabilities without spinning up n8n.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from quack_core.contracts.capabilities.demo import EchoRequest, echo_text


def run_flow():
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
