# === QV-LLM:BEGIN ===
# path: examples/http_adapter_usage.py
# === QV-LLM:END ===

"""
Example of how to use the HTTP adapter with QuackCore's config system.
"""

import asyncio

from quack_core.adapters.http.config import HttpAdapterConfig
from quack_core.adapters.http.service import run
from quack_core.config.tooling import load_tool_config, setup_tool_logging


def main() -> None:
    """Main function demonstrating HTTP adapter usage."""

    # Set up logging for the HTTP adapter
    setup_tool_logging("http-adapter", "DEBUG")

    # Load configuration using QuackCore's config system
    quack_config, http_config = load_tool_config(
        tool_name="http",
        config_model=HttpAdapterConfig,
        config_path=None,  # Uses default config locations
    )

    print(f"Starting HTTP adapter on {http_config.host}:{http_config.port}")
    print(f"Auth enabled: {http_config.auth_token is not None}")
    print(f"Max workers: {http_config.max_workers}")

    # Run the HTTP adapter
    run(http_config)


if __name__ == "__main__":
    main()

# File: examples/sample_config.yaml
"""
Sample configuration file showing HTTP adapter integration.
Save as quack_config.yaml in your project root.

# Standard QuackCore configuration
general:
project_name: "QuackCore HTTP API"
environment: "development"
debug: true

logging:
level: "DEBUG"
console: true

paths:
base_dir: "./"
output_dir: "./output"

# HTTP adapter configuration
custom:
http:
host: "0.0.0.0"
port: 8080
cors_origins:
- "http://localhost:3000"
- "http://localhost:8000"
auth_token: "development-token-change-in-production"
hmac_secret: "webhook-signing-secret"
job_ttl_seconds: 1800
max_workers: 4
request_timeout_seconds: 600

"""
# File: examples/client_example.py
"""
Example client for testing the HTTP adapter.
"""

import time
from typing import Any

import httpx


class QuackCoreHTTPClient:
    """Simple client for QuackCore HTTP adapter."""

    def __init__(self, base_url: str, auth_token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {}
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"

    async def health_check(self) -> dict[str, Any]:
        """Check if the API is healthy."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health/live")
            response.raise_for_status()
            return response.json()

    async def create_job(
        self,
        op: str,
        params: dict[str, Any],
        callback_url: str | None = None,
        idempotency_key: str | None = None,
    ) -> str:
        """Create a new job."""
        payload = {"op": op, "params": params}
        if callback_url:
            payload["callback_url"] = callback_url
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/jobs", json=payload, headers=self.headers
            )
            response.raise_for_status()
            return response.json()["job_id"]

    async def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get job status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/jobs/{job_id}", headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def wait_for_completion(
        self, job_id: str, timeout: int = 300, poll_interval: float = 1.0
    ) -> dict[str, Any]:
        """Wait for job completion."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = await self.get_job_status(job_id)

            if status["status"] in ["done", "error"]:
                return status

            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")

    async def slice_video_sync(
        self,
        input_path: str,
        output_path: str,
        start: str,
        end: str,
        overwrite: bool = True,
    ) -> dict[str, Any]:
        """Slice video synchronously."""
        params = {
            "input_path": input_path,
            "output_path": output_path,
            "start": start,
            "end": end,
            "overwrite": overwrite,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/quack-media/slice", json=params, headers=self.headers
            )
            response.raise_for_status()
            return response.json()


async def demo() -> None:
    """Demonstrate the HTTP client."""

    client = QuackCoreHTTPClient(
        base_url="http://localhost:8080",
        auth_token="development-token-change-in-production",  # noqa: S106 -- demo placeholder, self-documenting, not a real credential
    )

    print("Testing HTTP adapter...")

    # Health check
    try:
        health = await client.health_check()
        print(f"✓ Health check: {health}")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return

    # Test synchronous endpoint
    try:
        result = await client.slice_video_sync(
            input_path="/test/input.mp4",
            output_path="/test/output.mp4",
            start="00:00:10",
            end="00:00:20",
        )
        print(f"✓ Sync slice result: {result}")
    except Exception as e:
        print(f"✗ Sync slice failed: {e}")

    # Test asynchronous job
    try:
        job_id = await client.create_job(
            op="quack-media.transcribe_audio",
            params={
                "input_path": "/test/audio.mp3",
                "model_name": "small",
                "device": "auto",
            },
        )
        print(f"✓ Created job: {job_id}")

        # Wait for completion
        final_status = await client.wait_for_completion(job_id, timeout=30)
        print(f"✓ Job completed: {final_status}")

    except Exception as e:
        print(f"✗ Async job failed: {e}")

    # Test idempotency
    try:
        job_id1 = await client.create_job(
            op="quack-media.extract_frames",
            params={"input_path": "/test/video.mp4", "output_dir": "/test/frames"},
            idempotency_key="test-idempotency-key",
        )

        job_id2 = await client.create_job(
            op="quack-media.extract_frames",
            params={"input_path": "/test/video.mp4", "output_dir": "/test/frames"},
            idempotency_key="test-idempotency-key",
        )

        if job_id1 == job_id2:
            print(f"✓ Idempotency working: {job_id1}")
        else:
            print(f"✗ Idempotency failed: {job_id1} != {job_id2}")

    except Exception as e:
        print(f"✗ Idempotency test failed: {e}")


if __name__ == "__main__":
    asyncio.run(demo())

# File: examples/webhook_server.py
"""
Example webhook server for receiving QuackCore job completion callbacks.
"""

import hashlib
import hmac
import json

from fastapi import FastAPI, HTTPException, Request

app = FastAPI(title="QuackCore Webhook Server")

# Configure this to match your HMAC secret
HMAC_SECRET = "webhook-signing-secret"  # noqa: S105 -- demo placeholder, self-documenting, not a real credential


def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC signature."""
    if not signature.startswith("sha256="):
        return False

    expected = f"sha256={hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()}"
    return hmac.compare_digest(signature, expected)


@app.post("/webhook/quackcore")
async def handle_job_callback(request: Request) -> dict[str, Any]:
    """Handle job completion callbacks from quack_core."""

    body = await request.body()
    signature = request.headers.get("X-Quack-Signature", "")

    # Verify signature if HMAC is configured
    if HMAC_SECRET and signature:
        if not verify_signature(body, signature, HMAC_SECRET):
            raise HTTPException(401, "Invalid signature")
    elif HMAC_SECRET and not signature:
        raise HTTPException(401, "Signature required")

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON") from None

    job_id = data.get("job_id")
    status = data.get("status")
    result = data.get("result")
    error = data.get("error")

    print(f"📨 Received callback for job {job_id}")
    print(f"   Status: {status}")

    if status == "done":
        print(f"   ✓ Success: {result}")
        # Process successful result...

    elif status == "error":
        print(f"   ✗ Error: {error}")
        # Handle error...

    return {"received": True, "job_id": job_id}


@app.get("/health")
async def health() -> dict[str, bool]:
    """Health check endpoint."""
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    print("Starting webhook server on http://localhost:8000")
    print("Endpoints:")
    print("  POST /webhook/quack-core - Receive job callbacks")
    print("  GET  /health - Health check")
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104 -- demo/example code, not shipped runtime, self-documenting reachability choice
