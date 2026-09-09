"""Exercise the runtime's four-byte big-endian framing over actual Unix sockets."""

from __future__ import annotations

import json
import os
import socket
import struct
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from zeo_core.integrations.meetings import (
    InvocationReceipt,
    InvocationReconciliation,
    RuntimeRefusalError,
    UnixMeetingRuntime,
)

from .test_runner import NOW, authorization


@contextmanager
def server(reply: Callable[[dict[str, Any]], bytes]) -> Iterator[Path]:
    # macOS limits sockaddr_un paths to 104 bytes; pytest's tree can exceed it.
    with TemporaryDirectory(prefix="zm-", dir="/tmp") as directory:
        path = Path(directory) / "api.sock"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(path))
            path.chmod(0o600)
            listener.listen(1)
            listener.settimeout(5)

            def serve() -> None:
                with listener.accept()[0] as connection:
                    connection.settimeout(5)
                    header = connection.recv(4, socket.MSG_WAITALL)
                    length = struct.unpack("!I", header)[0]
                    assert 0 < length <= 1024 * 1024
                    request = json.loads(connection.recv(length, socket.MSG_WAITALL))
                    assert request["api_version"] == 1
                    connection.sendall(reply(request))

            with ThreadPoolExecutor(max_workers=1) as pool:
                result = pool.submit(serve)
                yield path
                result.result(timeout=6)


def frame(document: object) -> bytes:
    data = json.dumps(document).encode()
    return struct.pack("!I", len(data)) + data


def test_runtime_authorize_receipt_and_reconciliation() -> None:
    request = authorization({})

    def authorize(document: dict[str, Any]) -> bytes:
        assert document["method"] == "meeting.capability.authorize"
        assert document["params"] == request.model_dump(mode="json", exclude_none=True)
        return frame(
            {
                "api_version": 1,
                "request_id": document["request_id"],
                "result": {
                    "authorization": document["params"],
                    "disposition": "EXECUTE",
                },
            }
        )

    with server(authorize) as path:
        assert UnixMeetingRuntime(path).authorize(request).authorization == request
    receipt = InvocationReceipt(
        receipt_id="receipt_0123456789abcdef",
        invocation_id=request.invocation_id,
        operation=request.operation,
        resource=request.resource,
        request_sha256=request.request_sha256,
        outcome="SUCCEEDED",
        observed_at=NOW,
    )
    reconciliation = InvocationReconciliation(
        reconciliation_id="reconciliation_0123456789abcdef",
        invocation_id=request.invocation_id,
        outcome="SUCCEEDED",
        evidence_sha256="a" * 64,
        observed_at=NOW,
    )

    def admit(document: dict[str, Any]) -> bytes:
        assert document["method"] in {
            "meeting.capability.receipt.admit",
            "meeting.capability.reconcile",
        }
        return frame(
            {
                "api_version": 1,
                "request_id": document["request_id"],
                "result": document["params"],
            }
        )

    with server(admit) as path:
        assert UnixMeetingRuntime(path).admit_receipt(receipt) == receipt
    with server(admit) as path:
        assert UnixMeetingRuntime(path).reconcile(reconciliation) == reconciliation


@pytest.mark.parametrize(
    "mode",
    [
        "version",
        "identity",
        "error",
        "missing",
        "shape",
        "json",
        "zero",
        "large",
        "truncated",
        "header",
    ],
)
def test_runtime_refuses_invalid_answers(mode: str) -> None:
    def answer(request: dict[str, Any]) -> bytes:
        document = {"api_version": 1, "request_id": request["request_id"], "result": {}}
        if mode == "version":
            document["api_version"] = 2
        elif mode == "identity":
            document["request_id"] = "another-request"
        elif mode == "error":
            document["error"] = {"code": "refused"}
        elif mode == "missing":
            del document["result"]
        invalid_frames = {
            "shape": frame([]),
            "json": struct.pack("!I", 1) + b"{",
            "zero": b"\0\0\0\0",
            "large": struct.pack("!I", 1024 * 1024 + 1),
            "truncated": struct.pack("!I", 10) + b"{}",
            "header": b"\0",
        }
        return invalid_frames.get(mode, frame(document))

    with server(answer) as path, pytest.raises(RuntimeRefusalError):
        UnixMeetingRuntime(path).authorize(authorization({}))


def test_runtime_refuses_missing_regular_or_public_socket(tmp_path: Path) -> None:
    path = tmp_path / "api.sock"
    with pytest.raises(RuntimeRefusalError):
        UnixMeetingRuntime(path).authorize(authorization({}))
    path.write_text("not a socket")
    with pytest.raises(RuntimeRefusalError):
        UnixMeetingRuntime(path).authorize(authorization({}))
    with TemporaryDirectory(prefix="zm-", dir="/tmp") as directory:
        path = Path(directory) / "api.sock"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(path))
            os.chmod(path, 0o666)  # noqa: S103 - refusal fixture inside private parent
            with pytest.raises(RuntimeRefusalError):
                UnixMeetingRuntime(path).authorize(authorization({}))
            os.chmod(path, 0o600)
            Path(directory).chmod(0o755)
            with pytest.raises(RuntimeRefusalError):
                UnixMeetingRuntime(path).authorize(authorization({}))
            Path(directory).chmod(0o700)
            with pytest.raises(RuntimeRefusalError, match="too large"):
                UnixMeetingRuntime(path).authorize(
                    authorization({}).model_copy(update={"resource": "x" * 1024 * 1024})
                )
