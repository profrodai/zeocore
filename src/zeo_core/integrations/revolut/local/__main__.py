"""``python -m zeo_core.integrations.revolut.local <step>``: guided local setup."""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from ..models import RevolutEnvironment
from .session import LocalEnrollmentError, LocalRevolutEnrollment
from .store import LocalStoreError, dump_public


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m zeo_core.integrations.revolut.local"
    )
    parser.add_argument(
        "--environment",
        choices=[item.value for item in RevolutEnvironment],
        default=os.environ.get("REVOLUT_ENVIRONMENT", RevolutEnvironment.SANDBOX.value),
    )
    steps = parser.add_subparsers(dest="step", required=True)
    setup = steps.add_parser("setup", help="create the key and certificate")
    setup.add_argument("--redirect-uri", default=os.environ.get("REVOLUT_REDIRECT_URI"))
    setup.add_argument("--new-key", action="store_true")
    authorize = steps.add_parser("authorize", help="record the client id; get the URL")
    authorize.add_argument("--client-id", default=os.environ.get("REVOLUT_CLIENT_ID"))
    steps.add_parser("complete", help="paste the URL Revolut redirected to")
    steps.add_parser("status", help="show enrollment state without any secret")
    steps.add_parser("accounts", help="list accounts as a first live check")
    arguments = parser.parse_args(argv)
    enrollment = LocalRevolutEnrollment(RevolutEnvironment(arguments.environment))
    try:
        if arguments.step == "setup":
            if not arguments.redirect_uri:
                parser.error("--redirect-uri or REVOLUT_REDIRECT_URI is required")
            path = enrollment.setup(
                redirect_uri=arguments.redirect_uri, new_key=arguments.new_key
            )
            print(f"Register this certificate in Revolut Business settings:\n{path}")
        elif arguments.step == "authorize":
            if not arguments.client_id:
                parser.error("--client-id or REVOLUT_CLIENT_ID is required")
            print(enrollment.authorize(client_id=arguments.client_id))
        elif arguments.step == "complete":
            # Hidden, so the one-time code does not land in shell history.
            enrollment.complete(getpass.getpass("URL Revolut redirected to: "))
            print("Enrolled.")
        elif arguments.step == "status":
            state = enrollment.status()
            print("Not set up." if state is None else dump_public(state))
        else:
            for account in enrollment.read(lambda client: client.list_accounts()):
                print(account.id, account.currency, account.state)
    except (LocalEnrollmentError, LocalStoreError) as error:
        code = getattr(error, "code", "STORE")
        print(f"{code}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
