"""Prepare a meeting Sheets-read payload offline from the current source API.

No Google SDK, credentials, Runtime socket or authorization is required. The
host must obtain a real lease for the exact payload and resource before use.
"""

from __future__ import annotations

from pydantic import JsonValue

from zeo_core.integrations.meetings import request_digest


def main() -> None:
    payload: dict[str, JsonValue] = {
        "spreadsheet_id": "example-sheet",
        "range_a1": "Agenda!A1:C10",
    }
    resource = f"sheets:{payload['spreadsheet_id']}:{payload['range_a1']}"
    changed: dict[str, JsonValue] = {**payload, "range_a1": "Agenda!A1:C11"}
    print("Operation: sheets.values.read")
    print(f"Resource: {resource}")
    print(f"Request digest: {request_digest(payload)}")
    print(
        "Changed range changes digest: "
        f"{request_digest(changed) != request_digest(payload)}"
    )
    print("REQUEST ONLY: no authorization minted, Runtime contacted or provider called")


if __name__ == "__main__":
    main()
