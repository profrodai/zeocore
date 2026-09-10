"""Export versioned wire schemas; --check grades drift, not behavioral correctness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from zeo_core.contracts.runtime import (
    EffectRequest,
    HostResult,
    InvocationRequest,
    LaunchContext,
    ProviderBinding,
    RuntimeReply,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "contracts" / "runtime-host-v1"
    models = {
        "provider-binding": ProviderBinding,
        "launch-context": LaunchContext,
        "invocation-request": InvocationRequest,
        "host-result": HostResult,
        "effect-request": EffectRequest,
        "runtime-reply": RuntimeReply,
    }
    errors = []
    for name, model in models.items():
        path = root / f"{name}.schema.json"
        value = model.model_json_schema()
        value["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        rendered = json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        if args.check:
            if not path.exists() or path.read_text() != rendered:
                errors.append(str(path))
        else:
            root.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered)
    for error in errors:
        print(f"Schema drift: {error}")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
