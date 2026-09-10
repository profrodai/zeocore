"""Machine-only host entry point. No provider imports during discovery."""

from __future__ import annotations

import argparse
import os
import socket
import sys
from collections.abc import Sequence
from typing import Never

from zeo_core.adapters.runtime_host.canonical import (
    MAX_BYTES,
    InvalidRequestError,
    ProtocolError,
    canonical_bytes,
    manifest_inventory,
    parse_json,
)
from zeo_core.adapters.runtime_host.catalogue import validate_inventory
from zeo_core.adapters.runtime_host.channel import RuntimeChannel
from zeo_core.adapters.runtime_host.host import ManagedHost
from zeo_core.contracts.runtime import (
    EXIT_CODES,
    HostResult,
    InvocationRequest,
    LaunchContext,
    ProviderBinding,
)


class MachineParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise InvalidRequestError("invalid host command")


def read_fd(fd: int) -> bytes:
    if fd < 3:
        raise ProtocolError("private context requires an inherited descriptor")
    with os.fdopen(os.dup(fd), "rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    parse_json(raw)
    return raw


def read_invocation() -> InvocationRequest:
    raw = sys.stdin.buffer.read(MAX_BYTES + 1)
    try:
        parse_json(raw)
        return InvocationRequest.model_validate_json(raw)
    except ValueError as exc:
        raise InvalidRequestError("invalid invocation request") from exc


def main(argv: Sequence[str] | None = None) -> int:
    # Preserve the machine FD, then silence both Python prints and native FD1/2
    # from provider imports/calls. Runtime separately owns bounded diagnostics.
    machine_fd = os.dup(1)
    context: LaunchContext | None = None
    try:
        parser = MachineParser(add_help=False)
        parser.add_argument(
            "command", choices=["describe", "doctor", "capabilities", "invoke"]
        )
        parser.add_argument("detail", nargs="?")
        parser.add_argument("identity", nargs="?")
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--request", choices=["-"], default="-")
        parser.add_argument("--binding-fd", type=int, default=3)
        parser.add_argument("--context-fd", type=int, default=3)
        parser.add_argument("--runtime-fd", type=int, default=4)
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--offset", type=int, default=0)
        args = parser.parse_args(argv)
        if args.command == "invoke":
            if args.runtime_fd < 3 or args.runtime_fd == args.context_fd:
                raise ProtocolError("separate private Runtime descriptor required")
            context = LaunchContext.model_validate_json(read_fd(args.context_fd))
            request = read_invocation()
            channel = RuntimeChannel(
                socket.socket(fileno=os.dup(args.runtime_fd)), context
            )
            try:
                with open(os.devnull, "wb") as quiet:
                    os.dup2(quiet.fileno(), 1)
                    os.dup2(quiet.fileno(), 2)
                result = ManagedHost(context, channel).invoke(request)
            finally:
                channel.close()
            payload = result.model_dump(mode="json")
            code = EXIT_CODES[result.state]
        else:
            binding = ProviderBinding.model_validate_json(read_fd(args.binding_fd))
            validate_inventory(binding)
            inventory = manifest_inventory(binding.manifests)
            if args.command in {"describe", "doctor"}:
                payload = {
                    "protocol_version": 1,
                    "state": "succeeded",
                    "distribution": binding.distribution,
                    "version": binding.version,
                    "manifest_digest": binding.manifest_digest,
                    "readiness": "static_inventory_valid",
                    "authorized": False,
                }
            elif args.detail == "list" and 1 <= args.limit <= 100 and args.offset >= 0:
                page = inventory[args.offset : args.offset + args.limit]
                payload = {
                    "protocol_version": 1,
                    "state": "succeeded",
                    "capabilities": page,
                    "next_offset": args.offset + len(page)
                    if args.offset + len(page) < len(inventory)
                    else None,
                }
            elif args.detail == "describe":
                matches = [
                    m
                    for m in inventory
                    if f"{m['id']['namespace']}.{m['id']['name']}@{m['id']['version']}"
                    == args.identity
                ]
                if not matches:
                    raise ProtocolError("exact capability absent")
                payload = {
                    "protocol_version": 1,
                    "state": "succeeded",
                    "capability": matches[0],
                }
            else:
                raise ProtocolError("invalid catalogue command")
            code = 0
        encoded = canonical_bytes(payload)
        if len(encoded) > MAX_BYTES:
            raise ProtocolError("result exceeds maximum size")
    except InvalidRequestError:
        encoded = canonical_bytes(
            HostResult(
                protocol_version=1,
                binding=context.attempt if context else None,
                state="invalid_request",
                effect_disposition="none",
                error_code="ZEO_HOST_INVALID_REQUEST",
            ).model_dump(mode="json")
        )
        code = 2
    except Exception:
        encoded = canonical_bytes(
            HostResult(
                protocol_version=1,
                binding=None,
                state="protocol_error",
                effect_disposition="unknown",
                error_code="ZEO_HOST_PROTOCOL",
            ).model_dump(mode="json")
        )
        code = 8
    try:
        with os.fdopen(machine_fd, "wb") as machine:
            machine.write(encoded + b"\n")
            machine.flush()
    finally:
        # This CLI owns the process. Provider atexit handlers cannot write a
        # second envelope; their descriptors already point to the sink.
        pass
    return code


if __name__ == "__main__":
    raise SystemExit(main())
