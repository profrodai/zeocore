"""Host boundary tests with an explicitly simulated protocol peer.

These are Python conformance tests, NOT a real Runtime/Creator acceptance proof.
"""

from __future__ import annotations

import json
import os
import platform
import socket
import struct
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pytest
from jsonschema import exceptions as schema_errors  # type: ignore[import-untyped]
from pydantic import BaseModel, ValidationError

from zeo_core.adapters.runtime_host.canonical import (
    ProtocolError,
    canonical_bytes,
    digest,
    manifest_inventory,
    parse_json,
)
from zeo_core.adapters.runtime_host.catalogue import (
    CandidateCatalogue,
    validate_inventory,
)
from zeo_core.adapters.runtime_host.channel import RuntimeChannel
from zeo_core.adapters.runtime_host.host import EffectPort, ManagedHost, parse_result
from zeo_core.contracts import (
    CapabilityExample,
    CapabilityResult,
    EffectKind,
)
from zeo_core.contracts.runtime import (
    AttemptBinding,
    EffectRequest,
    HostResult,
    InvocationRequest,
    LaunchContext,
    ProviderBinding,
)
from zeo_core.core import managed_execution
from zeo_core.tools import (
    CapabilityRegistry,
    ToolContext,
    bound_capability_of,
    capability,
)


class Request(BaseModel):
    text: str
    organization_id: str = "org-a"


class Response(BaseModel):
    text: str


@capability(
    id="example.echo@1.0.0",
    description="An echo for host conformance.",
    effects={EffectKind.READ},
    examples=(CapabilityExample(request={"text": "hello"}),),
)
def echo(request: Request, ctx: ToolContext) -> CapabilityResult[Response]:
    del ctx
    return CapabilityResult.ok(data=Response(text=request.text))


def factory() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register(bound_capability_of(echo))
    return registry


def binding() -> ProviderBinding:
    manifests = tuple(factory().manifests())
    return ProviderBinding(
        protocol_version=1,
        distribution="zeocore",
        version=version("zeocore"),
        python_version=platform.python_version(),
        environment_digest="sha256:" + "0" * 64,
        factory="unavailable_module:factory",
        manifests=manifests,
        manifest_digest=digest(manifest_inventory(manifests)),
        generation=1,
    )


def context() -> LaunchContext:
    provider = binding()
    return LaunchContext(
        protocol_version=1,
        provider=provider,
        attempt=AttemptBinding(
            organization_id="org-a",
            project_id="project-a",
            seat_id="seat-a",
            runtime_binding_id="runtime-a",
            packet_id="packet-a",
            operation_id="op-a",
            attempt_id="attempt-a",
            fencing_generation=1,
            capability_id="example.echo@1.0.0",
            manifest_digest=provider.manifest_digest,
            request_digest=digest(
                {
                    "capability_id": "example.echo@1.0.0",
                    "arguments": {"text": "hello", "organization_id": "org-a"},
                }
            ),
        ),
        bootstrap_id="bootstrap-a",
        admitted_capabilities=("example.echo@1.0.0",),
        deadline_unix_ms=int(time.time() * 1000) + 10000,
        workspace="/unused-host-workspace",
    )


@pytest.fixture(autouse=True)
def isolate_latch(monkeypatch: pytest.MonkeyPatch) -> None:
    # Reset test-process state after each test, never via a production reset API.
    monkeypatch.setattr(managed_execution, "_managed", False)


def read_frame(sock: socket.socket) -> dict[str, Any]:
    def take(size: int) -> bytes:
        result = bytearray()
        while len(result) < size:
            chunk = sock.recv(size - len(result))
            if not chunk:
                raise EOFError
            result.extend(chunk)
        return bytes(result)

    length = struct.unpack("!I", take(4))[0]
    result = json.loads(take(length))
    assert isinstance(result, dict)
    return result


class Peer:
    """Socket-level simulator for contract tests; does not grant real authority."""

    def __init__(
        self,
        ctx: LaunchContext,
        response: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
    ) -> None:
        host_socket, self.socket = socket.socketpair()
        self.channel = RuntimeChannel(host_socket, ctx)
        self.calls: list[dict[str, Any]] = []
        self.errors: list[Exception] = []
        self.response = response
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def run(self) -> None:
        try:
            while True:
                message = read_frame(self.socket)
                self.calls.append(message)
                data: dict[str, Any] = {}
                if message["method"] == "result.publish":
                    data = {
                        "data_digest": message["payload"]["data_digest"],
                        "artifact_refs": ["artifact-a"],
                    }
                reply = {
                    "protocol_version": 1,
                    "sequence": message["sequence"],
                    "host_nonce": message["host_nonce"],
                    "binding": message["binding"],
                    "request_digest": digest(message),
                    "state": "allowed",
                    "data": data,
                }
                if self.response:
                    override = self.response(message)
                    if override is None:
                        self.socket.close()
                        return
                    reply.update(override)
                encoded = canonical_bytes(reply)
                self.socket.sendall(struct.pack("!I", len(encoded)) + encoded)
        except EOFError:
            pass
        except OSError:
            pass
        except Exception as exc:
            self.errors.append(exc)

    def close(self) -> None:
        self.channel.close()
        self.thread.join(2)
        self.socket.close()
        assert not self.thread.is_alive()
        assert not self.errors


@pytest.fixture
def peer() -> Iterator[Peer]:
    value = Peer(context())
    yield value
    value.close()


@pytest.mark.parametrize(
    "raw",
    [
        b'{"x":1,"x":2}',
        b'{"x":NaN}',
        b'{"x":1e999}',
        b'{"x":9007199254740992}',
        b'"\\ud800"',
        b"",
        b"{} {}",
    ],
)
def test_strict_json_refuses_ambiguous_input(raw: bytes) -> None:
    with pytest.raises(ProtocolError):
        parse_json(raw)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ({"b": 1.0, "a": -0.0}, b'{"a":0,"b":1}'),
        ([1e-7, 1e20, 1e21], b"[1e-7,100000000000000000000,1e+21]"),
        ({"\ue000": 1, "\U00010000": 2}, '{"\U00010000":2,"\ue000":1}'.encode()),
        ({"z": [3, 1, 2], "a": {}}, b'{"a":{},"z":[3,1,2]}'),
    ],
)
def test_independent_jcs_vectors(value: object, expected: bytes) -> None:
    assert canonical_bytes(value) == expected


def test_multiseed_manifest_bytes(tmp_path: Path) -> None:
    original = binding().manifests[0].model_dump(mode="json")
    original["requirements"]["services"] = ["delta", "gamma", "beta", "alpha"]
    original["tags"] = ["b", "a"]
    original["examples"][0]["request"]["ordered"] = [3, 1, 2]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(original))
    code = """
from pathlib import Path
from zeo_core.contracts import CapabilityManifest
from zeo_core.adapters.runtime_host.canonical import canonical_bytes,manifest_inventory
import sys
m=CapabilityManifest.model_validate_json(Path(sys.argv[1]).read_bytes())
sys.stdout.buffer.write(canonical_bytes(manifest_inventory([m])))
"""
    outputs = [
        subprocess.check_output(  # noqa: S603 -- fixed interpreter and owned probe
            [sys.executable, "-c", code, str(path)],
            env={**os.environ, "PYTHONHASHSEED": seed},
            timeout=15,
        )
        for seed in ("1", "2", "3")
    ]
    assert outputs[0] == outputs[1] == outputs[2]
    assert json.loads(outputs[0])[0]["examples"][0]["request"]["ordered"] == [3, 1, 2]


def test_candidate_is_not_visible_before_factory_completes() -> None:
    catalogue = CandidateCatalogue()
    entered, release = threading.Event(), threading.Event()
    failures: list[Exception] = []

    def candidate() -> CapabilityRegistry:
        value = factory()
        assert value.list_all()
        entered.set()
        assert release.wait(2)
        raise ValueError("registration failed after adding a tool")

    def activate() -> None:
        try:
            catalogue.activate(binding(), candidate)
        except Exception as exc:
            failures.append(exc)

    thread = threading.Thread(target=activate)
    thread.start()
    try:
        assert entered.wait(2)
        assert catalogue.snapshot() is None
    finally:
        release.set()
        thread.join(2)
    assert len(failures) == 1
    assert catalogue.snapshot() is None


def test_old_cleanup_cannot_remove_replacement() -> None:
    catalogue = CandidateCatalogue()
    old = catalogue.activate(binding(), factory)
    new = catalogue.activate(binding().model_copy(update={"generation": 2}), factory)
    catalogue.dispose(old)
    assert catalogue.snapshot() is new
    catalogue.dispose(new)
    with pytest.raises(ProtocolError, match="stale"):
        catalogue.activate(binding(), factory)


def test_invalid_candidate_keeps_previous_generation() -> None:
    catalogue = CandidateCatalogue()
    old = catalogue.activate(binding(), factory)
    with pytest.raises(ProtocolError):
        catalogue.activate(
            binding().model_copy(update={"generation": 2}), CapabilityRegistry
        )
    assert catalogue.snapshot() is old


def test_empty_catalogue_is_valid() -> None:
    empty = binding().model_copy(
        update={"manifests": (), "manifest_digest": digest([])}
    )
    assert not CandidateCatalogue().activate(empty, CapabilityRegistry).capabilities


def test_collision_names_both_owners() -> None:
    first = binding().manifests[0].model_copy(update={"projection_name": "collision"})
    second = first.model_copy(
        update={"id": first.id.model_copy(update={"name": "other"})}
    )
    with pytest.raises(
        ProtocolError, match="example.echo@1.0.0 and example.other@1.0.0"
    ):
        validate_inventory(binding().model_copy(update={"manifests": (first, second)}))


def test_external_schema_and_invalid_examples_refuse() -> None:
    original = binding().manifests[0]
    for modified in [
        original.model_copy(
            update={"request_schema": {"$ref": "https://invalid.test/schema"}}
        ),
        original.model_copy(
            update={"examples": (CapabilityExample(request={"text": 3}),)}
        ),
    ]:
        with pytest.raises((ProtocolError, schema_errors.ValidationError)):
            validate_inventory(binding().model_copy(update={"manifests": (modified,)}))


def test_real_typed_invocation_and_publication(peer: Peer) -> None:
    result = ManagedHost(peer.channel.context, peer.channel).invoke(
        InvocationRequest(
            protocol_version=1,
            capability_id="example.echo@1.0.0",
            arguments={"text": "hello"},
        ),
        factory=factory,
    )
    assert result.state == "succeeded"
    assert result.artifact_refs == ("artifact-a",)
    assert [call["method"] for call in peer.calls] == [
        "bootstrap",
        "invoke.admit",
        "result.publish",
    ]
    assert peer.calls[-1]["payload"]["data"] == {"text": "hello"}


def test_scope_denial_before_factory_or_bootstrap(peer: Peer) -> None:
    result = ManagedHost(peer.channel.context, peer.channel).invoke(
        InvocationRequest(
            protocol_version=1, capability_id="example.other@1.0.0", arguments={}
        ),
        factory=lambda: pytest.fail("must not load provider"),
    )
    assert result.state == "refused"
    assert not peer.calls


def test_changed_request_denied_after_normalization(peer: Peer) -> None:
    result = ManagedHost(peer.channel.context, peer.channel).invoke(
        InvocationRequest(
            protocol_version=1,
            capability_id="example.echo@1.0.0",
            arguments={"text": "changed"},
        ),
        factory=factory,
    )
    assert result.state == "refused"
    assert [call["method"] for call in peer.calls] == ["bootstrap"]


@pytest.mark.parametrize("state", ["refused", "cancelled", "waiting_approval"])
def test_revocation_or_wait_after_bootstrap_never_calls_provider(state: str) -> None:
    peer = Peer(
        context(), lambda m: {"state": state} if m["method"] == "invoke.admit" else {}
    )
    try:
        result = ManagedHost(peer.channel.context, peer.channel).invoke(
            InvocationRequest(
                protocol_version=1,
                capability_id="example.echo@1.0.0",
                arguments={"text": "hello"},
            ),
            factory=factory,
        )
        assert result.state == state
        assert [call["method"] for call in peer.calls] == ["bootstrap", "invoke.admit"]
    finally:
        peer.close()


@pytest.mark.parametrize(
    "field", ["sequence", "host_nonce", "request_digest", "binding"]
)
def test_reply_binding_refuses(field: str) -> None:
    changes: dict[str, Any] = {
        "sequence": 99,
        "host_nonce": "other",
        "request_digest": "sha256:" + "f" * 64,
        "binding": context()
        .attempt.model_copy(update={"attempt_id": "old"})
        .model_dump(mode="json"),
    }
    peer = Peer(context(), lambda _: {field: changes[field]})
    try:
        with pytest.raises(ProtocolError):
            peer.channel.bootstrap()
        with pytest.raises(ProtocolError):
            peer.channel.bootstrap()
        assert len(peer.calls) == 1
    finally:
        peer.close()


def test_same_host_cannot_redeem_twice(peer: Peer) -> None:
    assert peer.channel.bootstrap().state == "allowed"
    with pytest.raises(ProtocolError):
        peer.channel.bootstrap()
    assert len(peer.calls) == 1


@pytest.mark.parametrize(
    "state,code",
    [
        ("succeeded", 0),
        ("waiting_approval", 10),
        ("cancelled", 6),
        ("needs_reconciliation", 10),
    ],
)
def test_envelope_checked_on_every_exit(state: str, code: int) -> None:
    data = {
        "protocol_version": 1,
        "binding": context().attempt.model_dump(mode="json"),
        "state": state,
        "effect_disposition": "unknown" if state == "needs_reconciliation" else "none",
    }
    raw = canonical_bytes(data)
    assert parse_result(raw, code, context().attempt).state == state
    with pytest.raises(ProtocolError):
        parse_result(raw, 127, context().attempt)
    with pytest.raises(ProtocolError):
        parse_result(
            raw, code, context().attempt.model_copy(update={"attempt_id": "new"})
        )


def test_zero_exit_does_not_bless_invalid_or_oversized_envelope() -> None:
    for raw in [b"not JSON", b"x" * (1024 * 1024 + 1)]:
        with pytest.raises(ProtocolError):
            parse_result(raw, 0, context().attempt)
    with pytest.raises(ValidationError):
        HostResult(
            protocol_version=1,
            binding=context().attempt,
            state="succeeded",
            effect_disposition="unknown",
        )


def test_effect_lost_response_stays_unknown() -> None:
    peer = Peer(
        context().model_copy(update={"total_dispatch_budget": 1}),
        lambda m: None if m["method"] == "effect.request" else {},
    )
    try:
        peer.channel.bootstrap()
        effects = EffectPort(peer.channel)
        request = EffectRequest(
            logical_effect_id="effect-a",
            connection_ref="connection-a",
            connector_revision="sha256:" + "1" * 64,
            operation="read",
            arguments={},
        )
        with pytest.raises(ProtocolError):
            effects.request(request)
        assert effects.unknown
        with pytest.raises(ProtocolError):
            effects.request(request)
        assert (
            len([call for call in peer.calls if call["method"] == "effect.request"])
            == 1
        )
    finally:
        peer.close()


def test_effect_replay_preserves_identity_and_budget() -> None:
    def respond(message: dict[str, Any]) -> dict[str, Any]:
        if message["method"] != "effect.request":
            return {}
        effect = message["payload"]
        return {
            "data": {
                "logical_effect_id": effect["logical_effect_id"],
                "effect_request_digest": digest(effect),
                "receipt_id": "receipt-a",
                "authorization_id": "auth-a",
                "effect_disposition": "confirmed",
            }
        }

    peer = Peer(context().model_copy(update={"total_dispatch_budget": 1}), respond)
    try:
        peer.channel.bootstrap()
        effects = EffectPort(peer.channel)
        request = EffectRequest(
            logical_effect_id="effect-a",
            connection_ref="connection-a",
            connector_revision="sha256:" + "1" * 64,
            operation="read",
            arguments={},
        )
        assert effects.request(request) == effects.request(request)
        with pytest.raises(ProtocolError, match="changed input"):
            effects.request(request.model_copy(update={"arguments": {"changed": True}}))
        with pytest.raises(ProtocolError, match="budget"):
            effects.request(
                request.model_copy(update={"logical_effect_id": "effect-b"})
            )
        assert len(peer.calls) == 3
    finally:
        peer.close()


def test_cli_discovery_does_not_import_provider(tmp_path: Path) -> None:
    path = tmp_path / "binding.json"
    path.write_bytes(canonical_bytes(binding().model_dump(mode="json")))
    with path.open("rb") as source:
        result = subprocess.run(  # noqa: S603 -- fixed interpreter and host entry point
            [
                sys.executable,
                "-m",
                "zeo_core.adapters.runtime_host",
                "capabilities",
                "list",
                "--json",
                "--binding-fd",
                str(source.fileno()),
            ],
            pass_fds=(source.fileno(),),
            capture_output=True,
            timeout=10,
            check=False,
        )
    assert result.returncode == 0
    assert not result.stderr
    assert json.loads(result.stdout)["capabilities"][0]["id"]["name"] == "echo"


def test_cli_refuses_scope_with_valid_private_context(tmp_path: Path) -> None:
    ctx = context().model_copy(update={"admitted_capabilities": ()})
    path = tmp_path / "context.json"
    path.write_bytes(canonical_bytes(ctx.model_dump(mode="json")))
    parent, child = socket.socketpair()
    try:
        with path.open("rb") as source:
            result = subprocess.run(  # noqa: S603 -- fixed interpreter and host entry point
                [
                    sys.executable,
                    "-m",
                    "zeo_core.adapters.runtime_host",
                    "invoke",
                    "--context-fd",
                    str(source.fileno()),
                    "--runtime-fd",
                    str(child.fileno()),
                ],
                pass_fds=(source.fileno(), child.fileno()),
                input=b'{"protocol_version":1,"capability_id":"example.echo@1.0.0","arguments":{"text":"hello"}}',
                capture_output=True,
                timeout=10,
                check=False,
            )
        assert result.returncode == 3
        assert (
            parse_result(result.stdout, result.returncode, ctx.attempt).error_code
            == "ZEO_HOST_SCOPE"
        )
        assert not result.stderr
    finally:
        parent.close()
        child.close()


def test_managed_mode_blocks_member_fallback_before_transport() -> None:
    from zeo_core.integrations.hosted.client import HostedClientError
    from zeo_core.integrations.hosted.transport import ZEOconnectHTTPTransport

    managed_execution.enter_managed_execution()
    # Central guard must run before touching a session, credentials or HTTP.
    transport = object.__new__(ZEOconnectHTTPTransport)
    with pytest.raises(HostedClientError, match="fallback"):
        transport._request_json("GET", "/v1/connections", authenticated=True)


def test_committed_cross_language_vectors() -> None:
    root = Path(__file__).resolve().parents[2]
    vectors = json.loads(
        (root / "contracts/runtime-host-v1/canonical-vectors.json").read_text()
    )
    for vector in vectors["valid"]:
        assert canonical_bytes(vector["input"]) == vector["canonical"].encode("utf-8")
    for raw in vectors["invalid_json"]:
        with pytest.raises(ProtocolError):
            parse_json(raw.encode())


def test_exported_schemas_are_current() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(  # noqa: S603 -- owned schema exporter
        [
            sys.executable,
            str(root / "tools/export-runtime-host-contract-v1.py"),
            "--check",
        ],
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stdout.decode()


def noisy_factory() -> CapabilityRegistry:
    """Owned subprocess fixture that attempts to contaminate the machine stream."""
    print("provider debug output")
    os.write(1, b'{"state":"fake-success"}\n')
    os.write(2, b"provider diagnostic\n")
    return factory()


def test_cli_success_is_one_envelope_despite_provider_output(tmp_path: Path) -> None:
    ctx = context()
    ctx = ctx.model_copy(
        update={
            "provider": ctx.provider.model_copy(
                update={
                    "factory": "tests.test_adapters.test_runtime_host:noisy_factory",
                }
            )
        }
    )
    path = tmp_path / "context.json"
    path.write_bytes(canonical_bytes(ctx.model_dump(mode="json")))
    peer = Peer(ctx)
    try:
        with path.open("rb") as source:
            fd = peer.channel._socket.fileno()
            result = subprocess.run(  # noqa: S603 -- owned host and test fixture
                [
                    sys.executable,
                    "-m",
                    "zeo_core.adapters.runtime_host",
                    "invoke",
                    "--context-fd",
                    str(source.fileno()),
                    "--runtime-fd",
                    str(fd),
                ],
                pass_fds=(source.fileno(), fd),
                input=b'{"protocol_version":1,"capability_id":"example.echo@1.0.0","arguments":{"text":"hello"}}',
                capture_output=True,
                timeout=15,
                check=False,
            )
        assert result.returncode == 0, result.stdout
        assert result.stderr == b""
        assert len(result.stdout.splitlines()) == 1
        assert (
            parse_result(result.stdout, result.returncode, ctx.attempt).state
            == "succeeded"
        )
    finally:
        peer.close()


def test_bad_business_input_is_not_protocol_failure(peer: Peer) -> None:
    result = ManagedHost(peer.channel.context, peer.channel).invoke(
        InvocationRequest(
            protocol_version=1,
            capability_id="example.echo@1.0.0",
            arguments={"text": 4},
        ),
        factory=factory,
    )
    assert result.state == "invalid_request"
    assert [call["method"] for call in peer.calls] == ["bootstrap"]


def test_expired_context_refuses_without_bootstrap() -> None:
    peer = Peer(context().model_copy(update={"deadline_unix_ms": 1}))
    try:
        result = ManagedHost(peer.channel.context, peer.channel).invoke(
            InvocationRequest(
                protocol_version=1,
                capability_id="example.echo@1.0.0",
                arguments={"text": "hello"},
            ),
            factory=factory,
        )
        assert result.state == "timed_out"
        assert not peer.calls
    finally:
        peer.close()


def test_ipc_timeout_bounds_entire_dribbled_reply() -> None:
    child, parent = socket.socketpair()
    channel = RuntimeChannel(child, context().model_copy(update={"rpc_timeout_ms": 60}))
    finished = threading.Event()

    def trickle() -> None:
        try:
            read_frame(parent)
            parent.sendall(struct.pack("!I", 1000))
            for _ in range(20):
                parent.sendall(b" ")
                time.sleep(0.02)
            finished.set()
        except OSError:
            pass
        finally:
            parent.close()

    thread = threading.Thread(target=trickle)
    thread.start()
    try:
        with pytest.raises(ProtocolError):
            channel.bootstrap()
        assert not finished.is_set()
    finally:
        channel.close()
        thread.join(2)
        assert not thread.is_alive()


@pytest.mark.parametrize("version", [None, True, 1.0, "1", 2])
def test_wire_requires_explicit_exact_protocol_version(version: object) -> None:
    raw: dict[str, Any] = {"capability_id": "example.echo@1.0.0", "arguments": {}}
    if version is not None:
        raw["protocol_version"] = version
    with pytest.raises(ValidationError):
        InvocationRequest.model_validate_json(json.dumps(raw))


@pytest.mark.parametrize(
    "state", ["waiting_approval", "refused", "cancelled", "needs_reconciliation"]
)
def test_pending_effect_does_not_become_success_or_retry(state: str) -> None:
    peer = Peer(
        context().model_copy(update={"total_dispatch_budget": 1}),
        lambda message: (
            {"state": state} if message["method"] == "effect.request" else {}
        ),
    )
    try:
        peer.channel.bootstrap()
        effects = EffectPort(peer.channel)
        request = EffectRequest(
            logical_effect_id="effect-a",
            connection_ref="connection-a",
            connector_revision="sha256:" + "1" * 64,
            operation="read",
            arguments={},
        )
        with pytest.raises(ProtocolError):
            effects.request(request)
        assert effects.pending is not None and effects.pending.state == state
        assert effects.unknown == (state == "needs_reconciliation")
        with pytest.raises(ProtocolError):
            effects.request(request)
        assert len(peer.calls) == 2
    finally:
        peer.close()


def test_wrong_organization_is_refused_despite_matching_request_digest() -> None:
    ctx = context()
    ctx = ctx.model_copy(
        update={
            "attempt": ctx.attempt.model_copy(
                update={
                    "request_digest": digest(
                        {
                            "capability_id": "example.echo@1.0.0",
                            "arguments": {"text": "hello", "organization_id": "org-b"},
                        }
                    )
                }
            )
        }
    )
    peer = Peer(ctx)
    try:
        result = ManagedHost(ctx, peer.channel).invoke(
            InvocationRequest(
                protocol_version=1,
                capability_id="example.echo@1.0.0",
                arguments={"text": "hello", "organization_id": "org-b"},
            ),
            factory=factory,
        )
        assert result.error_code == "ZEO_HOST_ORGANIZATION"
        assert len(peer.calls) == 1
    finally:
        peer.close()
