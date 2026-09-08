"""CLI for explicit integration environment execution."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import warnings
from pathlib import Path

from zeo_core.integrations.environments import IntegrationEnvironment
from zeo_core.integrations.environments.catalog import CATALOG


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run an application with separate test/production state."
    )
    parser.add_argument("--mode", choices=("test", "production"), required=True)
    parser.add_argument(
        "--root",
        type=Path,
        required=True,
        help="Parent of separate test and production directories",
    )
    parser.add_argument(
        "--integration", choices=sorted(CATALOG), action="append", required=True
    )
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Test only: supply no provider credentials; your app must inject fixtures",
    )
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Create directories and print setup locations without running a command",
    )
    parser.add_argument(
        "--secret",
        action="append",
        default=[],
        metavar="VARIABLE",
        help="Prompt securely if a selected provider variable is missing",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    try:
        environment = IntegrationEnvironment(
            args.mode,
            args.root,
            tuple(args.integration),
            "fixture" if args.fixture else "live",
        )
        if args.prepare:
            if command or args.secret:
                parser.error("--prepare does not accept a command or secret prompt")
            environment.prepare()
            print(
                json.dumps(
                    {
                        "mode": environment.mode,
                        "backend": environment.backend,
                        "state_dir": str(environment.state_dir),
                        "work_dir": str(environment.work_dir),
                        "integrations": environment.integrations,
                    }
                )
            )
            return 0
        if not command or not command[0]:
            parser.error("An application command is required")
        print(
            f"[zeocore] mode={environment.mode} backend={environment.backend} "
            f"work_dir={environment.work_dir}",
            file=sys.stderr,
        )
        allowed = {
            key for name in environment.integrations for key in CATALOG[name].variables
        }
        if args.secret and (
            args.fixture or any(key not in allowed for key in args.secret)
        ):
            parser.error(
                "Secret prompts require live mode and a selected provider variable"
            )
        source = dict(os.environ)
        for key in args.secret:
            scoped = f"ZEO_{environment.mode.upper()}_{key}"
            if not source.get(scoped):
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("error", getpass.GetPassWarning)
                        source[scoped] = getpass.getpass(f"{environment.mode} {key}: ")
                except EOFError, getpass.GetPassWarning:
                    parser.error(
                        "A secure terminal or a preconfigured scoped secret is required"
                    )
                if not source[scoped]:
                    parser.error("The selected credential must not be empty")
        return environment.run(command, source=source)
    except (ValueError, OSError) as exc:
        # Errors in our path/argument checks contain no credential material.
        parser.exit(2, f"Integration environment could not start: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
