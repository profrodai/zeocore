"""
Behavioural proofs for protocols.py's SecretStore, ConnectionStore and
EffectAuthorizationVerifier, step-two contract bounds 1, 2 and 4:

  1. SecretStore exposes put, short-lived broker-only resolution, rotate,
     delete, and health through SecretRef.
  2. ConnectionStore persists and retrieves typed connection,
     connector-revision, execution, receipt, and evidence-reference
     records behind organization-scoped methods; callers cannot supply or
     override trusted organization context through generic payload data.
  4. Protocols have no production fake, environment bypass, default-allow
     branch, adapter import, provider call, filesystem write, or database
     behavior.

METHOD (per Master's brief): "Enumerate the ruling's required set from the
ruling's own bytes, then diff your implementation against it in BOTH
directions -- required-PRESENT as well as forbidden-ABSENT... Mutation
testing cannot catch a missing requirement... a missing method or an
unenforced bound is a hole, and a hole cannot be injected. Check for
absence by enumeration, not by injection."

So this file is deliberately split into two kinds of test:

  * ENUMERATION tests (TestRequiredMethodsArePresent,
    TestOrganizationScopingBySignature, TestNoGenericPayloadParameter,
    TestProtocolsCarryNoImplementationBody) -- these check ABSENCE/PRESENCE
    directly by reading `protocol.__annotations__` /
    `inspect.signature(...)` / the module's own source text. No injection
    is possible for these because there is nothing to break -- a MISSING
    method has no broken variant to construct; it either exists or it does
    not, and enumeration is the only correct check.
  * INJECTION tests (the ProbeCanFail classes) -- these are for
    assertions that DO have a "what would breaking this look like"
    answer: e.g. "a caller-supplied payload cannot override organization
    context" is tested by constructing a deliberately permissive stand-in
    protocol/callable that DOES accept an override, and observing the
    difference from the real protocol's signature.
"""

from __future__ import annotations

import ast
import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, get_type_hints

from zeo_core.contracts.connections.protocols import (
    ConnectionStore,
    EffectAuthorizationVerifier,
    SecretStore,
)


def _protocols_module_path() -> Path:
    test_dir = Path(__file__).parent  # tests/connections/
    repo_root = test_dir.parent.parent  # zeocore/
    return repo_root / "src" / "zeo_core" / "contracts" / "connections" / "protocols.py"


# ===========================================================================
# BOUND 1 + 2: required-PRESENT method enumeration (not injectable -- a
# missing method has no broken variant, so this is checked directly).
# ===========================================================================


class TestSecretStoreRequiredMethodsArePresent:
    """
    Bound 1, verbatim: "SecretStore exposes put, short-lived broker-only
    resolution, rotate, delete, and health through SecretRef." Five
    required capabilities map to five required method names.
    """

    REQUIRED_METHODS = frozenset({"put", "resolve", "rotate", "delete", "health"})

    def test_every_required_method_is_present(self) -> None:
        present = {name for name in vars(SecretStore) if not name.startswith("_")}
        missing = self.REQUIRED_METHODS - present
        assert not missing, f"SecretStore is missing required methods: {missing}"

    def test_no_extra_public_methods_beyond_the_five(self) -> None:
        # Not a hard bound-1 requirement by itself, but guards against a
        # protocol that quietly grew a sixth "convenience" method (e.g. a
        # general-purpose reveal) alongside the required five -- the same
        # spirit as SecretRef's "no general-purpose reveal method" proof
        # in test_secret_ref_and_evidence_ref_safety.py.
        present = {name for name in vars(SecretStore) if not name.startswith("_")}
        assert present == self.REQUIRED_METHODS

    def test_is_runtime_checkable(self) -> None:
        # runtime_checkable is required for isinstance() structural checks
        # to work at all -- a Protocol without it raises TypeError on
        # isinstance(), which would make this protocol unusable as a type
        # boundary by any future adapter.
        assert any(base.__name__ == "Protocol" for base in SecretStore.__mro__)
        obj = object()
        # isinstance() against a non-runtime-checkable Protocol raises
        # TypeError instead of returning False; success here proves
        # runtime_checkable is actually in effect.
        result = isinstance(obj, SecretStore)
        assert result is False

    def test_every_method_signature_carries_secretref_or_secret_value_types(
        self,
    ) -> None:
        # "through SecretRef" -- every method's parameter/return
        # annotations that touch the secret must be SecretRef,
        # SecretResolution or SecretHealth, never a bare `str` that a
        # caller could construct from raw material and never `Any`/
        # `object`, which would defeat the point of a typed boundary.
        # `delete`'s return is `None` by design (deletion has nothing to
        # hand back) and is excluded from this shape check on that one
        # parameter name; every OTHER parameter/return on every method,
        # including delete's own `ref`/`organization_id` inputs, is still
        # checked.
        allowed_secret_shapes = {
            "SecretRef",
            "SecretResolution",
            "SecretHealth",
        }
        skip_entirely = {("delete", "return")}
        for method_name in self.REQUIRED_METHODS:
            method = getattr(SecretStore, method_name)
            hints = get_type_hints(method)
            for param_name, hint in hints.items():
                if param_name in ("organization_id", "material"):
                    continue
                if (method_name, param_name) in skip_entirely:
                    continue
                hint_str = str(hint)
                assert any(shape in hint_str for shape in allowed_secret_shapes), (
                    f"SecretStore.{method_name}'s {param_name!r} annotation "
                    f"{hint_str!r} does not carry a SecretRef-family type"
                )


class TestConnectionStoreRequiredMethodsArePresent:
    """
    Bound 2, verbatim: "ConnectionStore persists and retrieves typed
    connection, connector-revision, execution, receipt, and
    evidence-reference records behind organization-scoped methods." Five
    record kinds x {save, get} = ten required methods (evidence-reference's
    "get" is plural -- get_evidence_references_for_execution -- since more
    than one may exist per execution; every other kind is exactly one
    save/get pair).
    """

    # `receipt` is deliberately excluded from this singular save/get pair:
    # receipt.py's own docstring makes ExecutionReceipt "durable,
    # append-only" and possibly PLURAL per execution (an AMBIGUOUS
    # execution's original receipt plus a later resolving one, both kept,
    # never overwritten) -- so its read method is
    # get_receipts_for_execution (plural, execution-scoped), checked
    # separately below rather than folded into this kind/pair loop, which
    # would wrongly demand a nonexistent singular get_receipt.
    REQUIRED_RECORD_KINDS = (
        "connection",
        "connector_revision",
        "execution",
    )

    def test_every_record_kind_has_a_save_method(self) -> None:
        present = {name for name in vars(ConnectionStore) if not name.startswith("_")}
        for kind in self.REQUIRED_RECORD_KINDS:
            assert f"save_{kind}" in present, f"missing save_{kind}"

    def test_every_record_kind_has_a_get_method(self) -> None:
        present = {name for name in vars(ConnectionStore) if not name.startswith("_")}
        for kind in self.REQUIRED_RECORD_KINDS:
            assert f"get_{kind}" in present, f"missing get_{kind}"

    def test_receipt_save_is_present_and_append_only_shaped(self) -> None:
        present = {name for name in vars(ConnectionStore) if not name.startswith("_")}
        assert "save_receipt" in present
        # append-only: there must be no update_receipt/delete_receipt
        # method a caller could use to mutate or erase prior history.
        assert "update_receipt" not in present
        assert "delete_receipt" not in present

    def test_receipt_get_is_present_as_the_plural_execution_scoped_form(
        self,
    ) -> None:
        present = {name for name in vars(ConnectionStore) if not name.startswith("_")}
        assert "get_receipts_for_execution" in present
        # And the wrongly-singular form this stream must not have added
        # is absent -- receipt.py's append-only, possibly-plural-per-
        # execution shape has no single "the" receipt to fetch.
        assert "get_receipt" not in present

    def test_evidence_reference_save_and_get_are_present(self) -> None:
        present = {name for name in vars(ConnectionStore) if not name.startswith("_")}
        assert "save_evidence_reference" in present
        assert "get_evidence_references_for_execution" in present

    def test_is_runtime_checkable(self) -> None:
        assert any(base.__name__ == "Protocol" for base in ConnectionStore.__mro__)
        assert isinstance(object(), ConnectionStore) is False


class TestEffectAuthorizationVerifierRequiredMethodIsPresent:
    """
    Bound 3, verbatim: "EffectAuthorizationVerifier validates exact
    organization, connection, connector revision, business operation,
    normalized request digest, expiry, and replay identity." One method,
    `verify`, whose signature must name every one of those seven checked
    facts as an explicit parameter -- not folded into an opaque payload
    object a caller could construct with fewer fields.
    """

    REQUIRED_PARAMETERS = frozenset(
        {
            "authorization",
            "organization_id",
            "connection_id",
            "connector_revision",
            "operation_id",
            "request_digest",
            "now",
            "seen_nonces",
        }
    )

    def test_verify_method_is_present(self) -> None:
        assert "verify" in vars(EffectAuthorizationVerifier)

    def test_verify_signature_names_every_checked_fact(self) -> None:
        sig = inspect.signature(EffectAuthorizationVerifier.verify)
        params = set(sig.parameters) - {"self"}
        missing = self.REQUIRED_PARAMETERS - params
        assert not missing, f"verify() is missing required parameters: {missing}"

    def test_verify_returns_authorizationverdict(self) -> None:
        hints = get_type_hints(EffectAuthorizationVerifier.verify)
        assert "AuthorizationVerdict" in str(hints["return"])

    def test_is_runtime_checkable(self) -> None:
        assert any(
            base.__name__ == "Protocol" for base in EffectAuthorizationVerifier.__mro__
        )
        assert isinstance(object(), EffectAuthorizationVerifier) is False


# ===========================================================================
# BOUND 2: organization-scoping via signature, both directions.
# ===========================================================================


class TestOrganizationScopingBySignature:
    """
    Bound 2's second half: "callers cannot supply or override trusted
    organization context through generic payload data." Checked at the
    SIGNATURE level: every ConnectionStore method takes
    `organization_id: OrganizationId` as an explicit, separate,
    KEYWORD-ONLY parameter of its own -- proving organization context is
    never read solely from inside a generic payload argument.
    """

    ALL_METHOD_NAMES = (
        "save_connection",
        "get_connection",
        "save_connector_revision",
        "get_connector_revision",
        "save_execution",
        "get_execution",
        "save_receipt",
        "get_receipts_for_execution",
        "save_evidence_reference",
        "get_evidence_references_for_execution",
    )

    def test_every_method_takes_organization_id_as_its_own_parameter(self) -> None:
        missing: list[str] = []
        for name in self.ALL_METHOD_NAMES:
            method = getattr(ConnectionStore, name)
            sig = inspect.signature(method)
            if "organization_id" not in sig.parameters:
                missing.append(name)
        assert not missing, (
            "ConnectionStore methods missing an explicit organization_id "
            f"parameter: {missing}"
        )

    def test_organization_id_is_typed_as_the_wrapper_not_a_bare_str(self) -> None:
        # A bare `str` organization_id parameter would let a caller pass
        # ANY string, including one lifted straight out of a generic
        # payload dict -- the typed OrganizationId wrapper is what makes
        # "trusted runtime context, never caller JSON" (identity.py's own
        # docstring on OrganizationId) a signature-level fact rather than
        # a convention.
        for name in self.ALL_METHOD_NAMES:
            method = getattr(ConnectionStore, name)
            hints = get_type_hints(method)
            org_hint = str(hints.get("organization_id"))
            assert "OrganizationId" in org_hint, (
                f"ConnectionStore.{name}'s organization_id is not typed as "
                f"OrganizationId: {org_hint!r}"
            )

    def test_organization_id_is_keyword_only_on_every_method(self) -> None:
        # Keyword-only means a caller must write organization_id=... by
        # name at every call site -- it can never be supplied positionally
        # from an unpacked, order-dependent payload structure.
        for name in self.ALL_METHOD_NAMES:
            method = getattr(ConnectionStore, name)
            sig = inspect.signature(method)
            param = sig.parameters["organization_id"]
            assert param.kind == inspect.Parameter.KEYWORD_ONLY, (
                f"ConnectionStore.{name}'s organization_id must be "
                f"keyword-only, got {param.kind}"
            )

    def test_effect_authorization_verifier_organization_id_also_typed_and_kwonly(
        self,
    ) -> None:
        sig = inspect.signature(EffectAuthorizationVerifier.verify)
        param = sig.parameters["organization_id"]
        assert param.kind == inspect.Parameter.KEYWORD_ONLY
        hints = get_type_hints(EffectAuthorizationVerifier.verify)
        assert "OrganizationId" in str(hints["organization_id"])


class TestNoGenericPayloadParameter:
    """
    The other half of "cannot supply or override... through generic
    payload data": no ConnectionStore or SecretStore method accepts a
    `dict`, `Mapping`, `**kwargs`, or `Any`-typed catch-all parameter that
    could carry an organization override alongside the trusted
    `organization_id` argument. Enumerated directly against every
    parameter's kind and annotation -- there is no permissive payload
    parameter to injection-test the absence of; either one exists or it
    does not.
    """

    def _all_protocol_methods(self) -> list[tuple[str, Callable[..., object]]]:
        methods: list[tuple[str, Callable[..., object]]] = []
        for proto in (SecretStore, ConnectionStore, EffectAuthorizationVerifier):
            for name in vars(proto):
                if name.startswith("_"):
                    continue
                methods.append((f"{proto.__name__}.{name}", getattr(proto, name)))
        return methods

    def test_no_method_accepts_var_keyword_kwargs(self) -> None:
        offenders = []
        for qualname, method in self._all_protocol_methods():
            sig = inspect.signature(method)
            for param in sig.parameters.values():
                if param.kind == inspect.Parameter.VAR_KEYWORD:
                    offenders.append(qualname)
        assert not offenders, f"methods accept **kwargs (generic payload): {offenders}"

    def test_no_method_accepts_a_dict_or_mapping_parameter(self) -> None:
        offenders = []
        for qualname, method in self._all_protocol_methods():
            hints = get_type_hints(method)
            hints.pop("return", None)
            for param_name, hint in hints.items():
                hint_str = str(hint)
                if "dict" in hint_str.lower() or "Mapping" in hint_str:
                    offenders.append(f"{qualname}.{param_name}: {hint_str}")
        assert not offenders, f"methods accept a dict/Mapping payload: {offenders}"

    def test_no_method_parameter_is_typed_any_or_untyped(self) -> None:
        # `now` and `seen_nonces` on EffectAuthorizationVerifier.verify are
        # deliberately typed `object` (protocols.py's own docstring
        # explains why: the concrete replay-store shape belongs to a later
        # step's persistence adapter, which does not exist yet) -- `object`
        # is the narrowest possible "I don't know the shape yet" type and,
        # unlike `Any` or `dict`, offers no attribute/key access a caller
        # could exploit to smuggle an override through; it is excluded
        # here by name, not by weakening this check.
        allowed_object_typed_params = {
            ("EffectAuthorizationVerifier.verify", "now"),
            ("EffectAuthorizationVerifier.verify", "seen_nonces"),
        }
        offenders = []
        for qualname, method in self._all_protocol_methods():
            hints = get_type_hints(method)
            hints.pop("return", None)
            for param_name, hint in hints.items():
                if (qualname, param_name) in allowed_object_typed_params:
                    continue
                hint_str = str(hint)
                if hint_str in ("typing.Any", "<class 'object'>"):
                    offenders.append(f"{qualname}.{param_name}: {hint_str}")
        assert not offenders, f"methods have an Any/object-typed parameter: {offenders}"


class TestNoGenericPayloadParameterProbeCanFail:
    """
    Proves the enumeration checks above are real probes by defining a
    deliberately permissive synthetic protocol method -- one that DOES
    accept a generic `dict` payload a caller could smuggle an organization
    override through -- and observing the identical detection logic catch
    it.
    """

    def test_probe_catches_a_dict_payload_parameter(self) -> None:
        class LeakyConnectionStore(Protocol):
            def save_connection(
                self, *, organization_id: object, payload: dict[str, object]
            ) -> None: ...

        hints = get_type_hints(LeakyConnectionStore.save_connection)
        hints.pop("return", None)
        offenders = [
            f"{name}: {hint}"
            for name, hint in hints.items()
            if "dict" in str(hint).lower()
        ]
        injected = bool(offenders)
        print(f"injected: {injected}")
        assert injected, (
            "probe-of-the-probe failed: the deliberately leaky synthetic "
            "protocol did not carry a detectable dict payload parameter"
        )
        # The real ConnectionStore must not share this shape.
        real_hints = get_type_hints(ConnectionStore.save_connection)
        real_hints.pop("return", None)
        real_offenders = [
            f"{name}: {hint}"
            for name, hint in real_hints.items()
            if "dict" in str(hint).lower()
        ]
        assert not real_offenders

    def test_probe_catches_kwargs_catch_all(self) -> None:
        class LeakyVerifier(Protocol):
            def verify(self, **kwargs: object) -> object: ...

        sig = inspect.signature(LeakyVerifier.verify)
        has_var_keyword = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        injected = has_var_keyword
        print(f"injected: {injected}")
        assert injected, "probe-of-the-probe failed: no **kwargs detected"
        real_sig = inspect.signature(EffectAuthorizationVerifier.verify)
        assert not any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in real_sig.parameters.values()
        )


# ===========================================================================
# BOUND 4: no permissive default implementation / no adapter imports / no
# provider calls / no filesystem or database behavior. Enumerated directly
# against the module's own AST -- the only reliable way to prove ABSENCE of
# a body, an import, or a call.
# ===========================================================================


class TestProtocolsCarryNoImplementationBody:
    """
    "No permissive default implementation" -- every method body in
    protocols.py must be exactly `...` (an Ellipsis expression statement),
    the standard shape for a pure structural Protocol method with no
    fallback behavior. A `return True`, `return None` used as an
    allow-by-default, a `pass` that silently no-ops, or any real statement
    would all be a permissive default implementation; `...` is not
    executable logic at all.
    """

    def test_every_protocol_method_body_is_bare_ellipsis(self) -> None:
        source = _protocols_module_path().read_text()
        tree = ast.parse(source)
        offenders: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not isinstance(item, ast.FunctionDef):
                    continue
                body = item.body
                # A docstring Expr(Constant(str)) is permitted as the
                # first statement; the actual body after that must be
                # exactly one Expr(Constant(Ellipsis)) statement.
                statements = body
                if (
                    statements
                    and isinstance(statements[0], ast.Expr)
                    and isinstance(statements[0].value, ast.Constant)
                    and isinstance(statements[0].value.value, str)
                ):
                    statements = statements[1:]
                is_bare_ellipsis = (
                    len(statements) == 1
                    and isinstance(statements[0], ast.Expr)
                    and isinstance(statements[0].value, ast.Constant)
                    and statements[0].value.value is Ellipsis
                )
                if not is_bare_ellipsis:
                    offenders.append(f"{node.name}.{item.name}")
        assert not offenders, (
            f"protocol methods with a non-Ellipsis body (a permissive "
            f"default implementation): {offenders}"
        )

    def test_probe_catches_a_permissive_default_allow_body(self) -> None:
        # Deliberately broken synthetic source: a method with a real
        # `return True` body instead of `...` -- the textbook
        # default-allow-branch shape bound 4 forbids.
        broken_source = (
            "from typing import Protocol\n\n"
            "class Broken(Protocol):\n"
            "    def verify(self) -> bool:\n"
            "        return True\n"
        )
        tree = ast.parse(broken_source)
        offenders: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not isinstance(item, ast.FunctionDef):
                    continue
                statements = item.body
                is_bare_ellipsis = (
                    len(statements) == 1
                    and isinstance(statements[0], ast.Expr)
                    and isinstance(statements[0].value, ast.Constant)
                    and statements[0].value.value is Ellipsis
                )
                if not is_bare_ellipsis:
                    offenders.append(f"{node.name}.{item.name}")
        injected = bool(offenders)
        print(f"injected: {injected}")
        assert injected, (
            "probe-of-the-probe failed: the deliberately broken synthetic "
            "source's default-allow body was not detected"
        )


class TestNoAdapterOrProviderImports:
    """
    "No adapter import, no provider call, no filesystem write, no database
    behavior" -- reuses the exact same forbidden-import-roots technique as
    test_no_adapter_imports.py (this directory), applied to protocols.py
    specifically, plus a direct source-text scan for the filesystem/
    database/network call surfaces bound 4 names.
    """

    FORBIDDEN_IMPORT_ROOTS = (
        "zeo_core.connections.adapters",
        "zeo_core.integrations",
        "zeo_core.tools",
        "zeo_core.adapters",
    )

    #: Substrings that would indicate filesystem, database or network
    #: behavior leaking into a file that must be pure structural typing.
    #: Deliberately narrow (exact call-shape prefixes), not a broad
    #: word-match, so this does not flag the module's own prose about
    #: "filesystem write" appearing in a docstring.
    FORBIDDEN_CALL_PREFIXES = (
        "open(",
        "sqlite3.",
        "os.remove(",
        "os.unlink(",
        "Path(",
        "requests.",
        "httpx.",
        "urllib.",
        "subprocess.",
    )

    def test_no_forbidden_imports(self) -> None:
        source = _protocols_module_path().read_text()
        tree = ast.parse(source)
        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(self.FORBIDDEN_IMPORT_ROOTS):
                        violations.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith(self.FORBIDDEN_IMPORT_ROOTS):
                    violations.append(node.module)
        assert not violations, f"protocols.py imports an adapter module: {violations}"

    def test_no_filesystem_database_or_network_call_surfaces(self) -> None:
        source = _protocols_module_path().read_text()
        # Scan only executable lines, not docstrings/comments, by parsing
        # and re-serializing each function body's non-string statements --
        # simpler and sufficient: since every method body is proven bare
        # Ellipsis by TestProtocolsCarryNoImplementationBody above, this
        # check's real job is to catch a call surface introduced OUTSIDE a
        # method body (module level, a helper function) that the
        # bare-Ellipsis check would not cover.
        tree = ast.parse(source)
        offending_lines: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_source = ast.get_source_segment(source, node) or ""
                for prefix in self.FORBIDDEN_CALL_PREFIXES:
                    if call_source.startswith(prefix):
                        offending_lines.append(call_source)
        assert not offending_lines, (
            f"protocols.py contains a filesystem/database/network call: "
            f"{offending_lines}"
        )

    def test_probe_catches_an_integrations_import(self) -> None:
        broken_source = (
            "from zeo_core.integrations.google.auth import get_credentials\n"
        )
        tree = ast.parse(broken_source)
        violations = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith(self.FORBIDDEN_IMPORT_ROOTS)
        ]
        injected = bool(violations)
        print(f"injected: {injected}")
        assert injected, "probe-of-the-probe failed: import not detected"

    def test_probe_catches_a_filesystem_write_call(self) -> None:
        broken_source = 'open("/tmp/leak.txt", "w")\n'
        tree = ast.parse(broken_source)
        offending = [
            ast.get_source_segment(broken_source, node)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (ast.get_source_segment(broken_source, node) or "").startswith("open(")
        ]
        injected = bool(offending)
        print(f"injected: {injected}")
        assert injected, "probe-of-the-probe failed: open() call not detected"


class TestNoTestEnvironmentBranch:
    """
    Bound 4 + packet acceptance check: "full-tree search -> no production
    fake, no test-environment branch." protocols.py must not reference
    `pytest`, `sys.modules`, or `inspect.stack()` -- the exact
    hygiene-check probe named in the repo Makefile's own doctrine comment
    (production must never detect it is under test).
    """

    FORBIDDEN_SUBSTRINGS = ("pytest", "sys.modules", "inspect.stack")

    def test_no_test_detection_substrings_in_source(self) -> None:
        source = _protocols_module_path().read_text()
        found = [s for s in self.FORBIDDEN_SUBSTRINGS if s in source]
        assert not found, f"protocols.py references test-detection surface: {found}"
