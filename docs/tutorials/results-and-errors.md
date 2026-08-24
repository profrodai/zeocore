# Results and errors

Capabilities need to report both ordinary outcomes and exceptional bugs.
ZeoCore keeps those two concerns separate:

- return a `CapabilityResult` for an outcome the workflow should branch on;
- raise a `ZeoError` for an exceptional condition outside that result
  contract.

The canonical imports are:

```python
from zeo_core.contracts import CapabilityResult
from zeo_core.core.errors import ZeoError
```

## The four result constructors

### Success: `ok`

Use success when the capability produced its intended payload:

```python
result = CapabilityResult.ok(
    data={"word_count": 2},
    msg="Counted words",
)
```

It has `status == "success"`, `outcome == "success"`, typed `data`, no error,
and no machine message.

### Intentional non-work: `skip`

Use a skip when policy or already-satisfied state says not to do the work:

```python
result = CapabilityResult.skip(
    reason="Output already exists",
    code="ZEO_FILE_ALREADY_EXISTS",
)
```

It has `status == "skipped"` and `outcome == "policy_skipped"`. A skip is not
an error. Its machine code must begin with `ZEO_` (the compatibility prefixes
`ZC_` and `QC_` are also accepted).

### Missing dependency: `unavailable`

Use unavailable when the declared capability cannot run because a dependency
is absent:

```python
result = CapabilityResult.unavailable(
    reason="Calendar service was not provided",
)
```

It also has `status == "skipped"`, but its more precise outcome is
`"unavailable"` and its default code is `ZEO_CAP_UNAVAILABLE`. This difference
lets a runner distinguish policy from missing infrastructure. Invocation
helpers produce this result automatically when declared requirements are not
available in `ToolContext`.

### Expected operational failure: `fail`

Use failure when the capability ran but an expected operational problem
prevented completion:

```python
result = CapabilityResult.fail(
    msg="Calendar API rejected the request",
    code="ZEO_CALENDAR_API_ERROR",
    exception=api_error,
)
```

It has `status == "error"`, normally
`outcome == "integration_failure"`, a machine code, and a structured
`CapabilityError`. When converting a caught exception directly,
`CapabilityResult.fail_from_exc(...)` is a convenience that records an
`"unexpected_exception"` outcome.

## Branch safely

Status is the broad workflow branch; outcome is the precise reason:

```python
if result.status == "success":
    assert result.data is not None
    print(result.data)
elif result.status == "skipped":
    print(f"{result.outcome}: {result.human_message}")
else:
    print(f"{result.machine_message}: {result.human_message}")
```

Do not assume every skipped result is a policy skip. Check `result.outcome`
when `unavailable` matters.

## When to raise `ZeoError`

`ZeoError` and its subclasses are typed exceptions with structured context.
They are useful for configuration loaders, low-level I/O helpers, and other
APIs where returning `CapabilityResult` is not the function's contract:

```python
from zeo_core.core.errors import (
    ZeoError,
    ZeoFileNotFoundError,
    ZeoFormatError,
    ZeoValidationError,
)

try:
    settings = load_settings(path)
except ZeoFileNotFoundError as exc:
    print(exc.context)
except ZeoFormatError as exc:
    print(exc.context)
except ZeoValidationError as exc:
    print(exc.context)
except ZeoError as exc:
    print(f"Other Zeo error: {exc}")
```

See the runnable
[`examples/error_handling.py`](../../examples/error_handling.py), which shows
missing-file, invalid-JSON, validation, and success paths. It also demonstrates
`wrap_io_errors`, which converts unhandled standard I/O/value exceptions into
the Zeo error family.

## How invocation treats exceptions

Direct helper functions such as `load_settings()` may raise `ZeoError` to
their callers. A handler invoked through `invoke_sync` or `invoke_async` is a
different boundary: an exception escaping the handler is caught and converted
to an error `CapabilityResult` with code `ZEO_CAP_UNEXPECTED`.

Therefore:

- return `ok`, `skip`, `unavailable`, or `fail` for expected capability
  outcomes;
- use specific `ZeoError` subclasses in APIs whose contract is exceptional;
- do not use exceptions as routine workflow branches;
- still allow truly unexpected exceptions to surface to the invocation
  boundary, where ZeoCore normalizes them.

Next, learn how those handlers receive dependencies in
[Context, configuration, and files](context-config-files.md).
