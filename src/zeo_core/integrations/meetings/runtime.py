"""Bounded local Unix-socket calls to the existing meeting runtime API."""

from __future__ import annotations

import json
import os
import socket
import stat
import struct
import uuid
from pathlib import Path
from typing import Protocol

from pydantic import JsonValue

from .contracts import (
    AuthorizationResult,
    InvocationAuthorization,
    InvocationReceipt,
    InvocationReconciliation,
)


class RuntimeRefusalError(RuntimeError):
    """No provider call may follow a missing or invalid runtime answer."""


class MeetingRuntimePort(Protocol):
    def authorize(self, request: InvocationAuthorization) -> AuthorizationResult: ...
    def admit_receipt(self, receipt: InvocationReceipt) -> InvocationReceipt: ...


class UnixMeetingRuntime:
    """Use a private runtime socket; never mint authority or retry an effect."""

    def __init__(self, socket_path: Path, *, timeout: float = 30.0) -> None:
        self._path = socket_path
        self._timeout = timeout

    def authorize(self, request: InvocationAuthorization) -> AuthorizationResult:
        return AuthorizationResult.model_validate(
            self._call(
                "meeting.capability.authorize",
                request.model_dump(mode="json", exclude_none=True),
            )
        )

    def admit_receipt(self, receipt: InvocationReceipt) -> InvocationReceipt:
        return InvocationReceipt.model_validate(
            self._call(
                "meeting.capability.receipt.admit", receipt.model_dump(mode="json")
            )
        )

    def reconcile(self, record: InvocationReconciliation) -> InvocationReconciliation:
        """Admit host-supplied reconciliation evidence to the original invocation."""
        return InvocationReconciliation.model_validate(
            self._call("meeting.capability.reconcile", record.model_dump(mode="json"))
        )

    def _call(self, method: str, params: dict[str, JsonValue]) -> object:
        try:
            info = self._path.lstat()
            parent = self._path.parent.stat()
            if (
                not stat.S_ISSOCK(info.st_mode)
                or info.st_uid != os.getuid()
                or info.st_mode & 0o077
                or parent.st_uid != os.getuid()
                or parent.st_mode & 0o077
            ):
                raise RuntimeRefusalError("runtime socket is not private")
            request_id = "meeting-" + uuid.uuid4().hex
            body = json.dumps(
                {
                    "api_version": 1,
                    "request_id": request_id,
                    "method": method,
                    "params": params,
                },
                separators=(",", ":"),
            ).encode()
            if len(body) > 1024 * 1024:
                raise RuntimeRefusalError("runtime request is too large")
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
                stream.settimeout(self._timeout)
                stream.connect(str(self._path))
                stream.sendall(struct.pack("!I", len(body)) + body)
                length = struct.unpack("!I", _read_exact(stream, 4))[0]
                if not 0 < length <= 1024 * 1024:
                    raise RuntimeRefusalError("runtime response is invalid")
                response = _read_exact(stream, length)
            decoded = json.loads(response)
            if (
                not isinstance(decoded, dict)
                or decoded.get("api_version") != 1
                or decoded.get("request_id") != request_id
                or decoded.get("error")
                or "result" not in decoded
            ):
                raise RuntimeRefusalError("runtime request was refused")
            return decoded["result"]
        except RuntimeRefusalError:
            raise
        except Exception:
            raise RuntimeRefusalError("runtime is unavailable") from None


def _read_exact(stream: socket.socket, length: int) -> bytes:
    data = bytearray()
    while len(data) < length:
        chunk = stream.recv(length - len(data))
        if not chunk:
            raise RuntimeRefusalError("runtime frame was truncated")
        data.extend(chunk)
    return bytes(data)
