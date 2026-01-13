---
title: QuackCore HTTP Adapter
description: Optional FastAPI-based HTTP API for QuackCore _ops
---

# QuackCore HTTP Adapter

The QuackCore HTTP Adapter provides an optional FastAPI-based REST API that exposes QuackCore operations via HTTP endpoints. This enables external systems like n8n, webhooks, or other applications to invoke QuackCore functionality remotely.

## Features

- **Optional Installation**: Only available when the `http` extra is installed
- **Stateless Design**: Each request is independent with minimal in-memory job tracking
- **Authentication**: Bearer token authentication with optional HMAC signing for callbacks
- **Async & Sync Operations**: Both immediate synchronous endpoints and asynchronous job-based operations
- **Job Management**: Track long-running operations with polling support
- **Callback Support**: Notify external systems when jobs complete
- **OpenAPI Integration**: Automatic API documentation at `/docs`

## Installation

Install QuackCore with the HTTP adapter:

```bash
pip install quack-core[http]
```

This installs the following additional dependencies:
- FastAPI ≥0.112
- Uvicorn ≥0.30 (with standard extras)
- HTTPX ≥0.27 (for callbacks)

## Quick Start

### 1. Basic Configuration

Create a configuration file or use environment variables:

```yaml
# config/http.yaml
http:
  host: "0.0.0.0"
  port: 8080
  auth_token: "your-secret-token"
  cors_origins: ["*"]  # Configure appropriately for production
  max_workers: 4
  job_ttl_seconds: 3600
```

### 2. Running the Server

Using the Makefile:

```bash
# Development with auto-reload
make api-run-reload

# Production
make api-run
```

Or directly with uvicorn:

```bash
uvicorn quack_core.adapters.http.app:create_app --factory --host 0.0.0.0 --port 8080
```

### 3. Basic Usage

The API provides two styles of endpoints:

#### Synchronous Operations (Immediate Response)

```bash
curl -H "Authorization: Bearer your-secret-token" \
     -X POST http://localhost:8080/quackmedia/slice \
     -H "Content-Type: application/json" \
     -d '{
       "input_path": "/path/to/video.mp4",
       "output_path": "/path/to/output.mp4",
       "start": "00:00:05.000",
       "end": "00:00:15.000",
       "overwrite": true
     }'
```

#### Asynchronous Jobs (For Long-Running Operations)

Create a job:

```bash
curl -H "Authorization: Bearer your-secret-token" \
     -X POST http://localhost:8080/jobs \
     -H "Content-Type: application/json" \
     -d '{
       "op": "quack-media.slice_video",
       "params": {
         "input_path": "/path/to/video.mp4",
         "output_path": "/path/to/output.mp4",
         "start": "00:00:05.000",
         "end": "00:00:15.000",
         "overwrite": true
       },
       "callback_url": "https://your-app.com/webhook"
     }'
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
}
```

Check job status:

```bash
curl -H "Authorization: Bearer your-secret-token" \
     http://localhost:8080/jobs/550e8400-e29b-41d4-a716-446655440000
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "done",
  "result": {
    "success": true,
    "operation": "quack-media.slice_video",
    "output_path": "/path/to/output.mp4"
  },
  "error": null
}
```

## Configuration

### HttpAdapterConfig Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `host` | str | "0.0.0.0" | Bind address |
| `port` | int | 8080 | Port number |
| `cors_origins` | List[str] | [] | CORS allowed origins |
| `auth_token` | Optional[str] | None | Bearer token (None = auth disabled) |
| `hmac_secret` | Optional[str] | None | HMAC secret for callback signing |
| `public_base_url` | Optional[str] | None | Public URL for documentation |
| `job_ttl_seconds` | int | 3600 | How long to keep finished jobs |
| `max_workers` | int | 4 | Thread pool size for jobs |
| `request_timeout_seconds` | int | 900 | Per-job timeout limit |

### Environment Variables

Configuration can also be provided via environment variables with the `QUACK_HTTP__` prefix:

```bash
export QUACK_HTTP__AUTH_TOKEN="your-secret-token"
export QUACK_HTTP__PORT=9000
export QUACK_HTTP__MAX_WORKERS=8
```

## API Reference

### Health Endpoints

- `GET /health/live` - Liveness check
- `GET /health/ready` - Readiness check

Both return `{"ok": true}` with 200 status.

### Job Management

#### Create Job
`POST /jobs`

Request body:
```json
{
  "op": "quack-media.slice_video",
  "params": {"input_path": "/in.mp4", "output_path": "/out.mp4"},
  "callback_url": "https://optional-webhook.com/callback",
  "idempotency_key": "optional-unique-key"
}
```

Response:
```json
{
  "job_id": "uuid4-string",
  "status": "queued"
}
```

#### Get Job Status
`GET /jobs/{job_id}`

Response:
```json
{
  "job_id": "uuid4-string",
  "status": "done|queued|running|error",
  "result": {...},
  "error": null
}
```

### QuackMedia Endpoints (Synchronous)

#### Slice Video
`POST /quackmedia/slice`

```json
{
  "input_path": "/path/to/input.mp4",
  "output_path": "/path/to/output.mp4",
  "start": "00:00:05.000",
  "end": "00:00:15.000",
  "overwrite": true
}
```

#### Transcribe Audio
`POST /quackmedia/transcribe`

```json
{
  "input_path": "/path/to/audio.mp3",
  "model_name": "small",
  "device": "auto",
  "vad": true
}
```

#### Extract Frames
`POST /quackmedia/frames`

```json
{
  "input_path": "/path/to/video.mp4",
  "output_dir": "/path/to/frames/",
  "fps": 2.0,
  "pattern": "frame_%06d.png",
  "overwrite": true
}
```

## Authentication

### Bearer Token

Include the token in the Authorization header:

```bash
Authorization: Bearer your-secret-token
```

If no `auth_token` is configured, authentication is disabled (development only).

### Callback Signatures

When `hmac_secret` is configured, outgoing callbacks include a signature header:

```
X-Quack-Signature: sha256=hex-encoded-signature
```

The signature is computed as:
```python
hmac.new(secret.encode(), json_body.encode(), hashlib.sha256).hexdigest()
```

## Idempotency

Prevent duplicate job creation by providing an idempotency key:

```bash
# Header approach
curl -H "Idempotency-Key: unique-operation-123" ...

# Body approach
{
  "op": "...",
  "params": {...},
  "idempotency_key": "unique-operation-123"
}
```

Subsequent requests with the same operation, parameters, and key will return the same job ID.

## Error Handling

The API returns standard HTTP status codes:

- `200` - Success
- `401` - Authentication required/failed
- `404` - Job not found
- `500` - Internal server error

Error responses include descriptive messages:

```json
{
  "detail": "Job not found"
}
```

## Callbacks

When a job includes a `callback_url`, the system will POST the final result:

```json
{
  "job_id": "uuid4-string",
  "status": "done|error",
  "result": {...},
  "error": null
}
```

Callbacks include HMAC signatures when `hmac_secret` is configured. Callback failures are logged but don't affect job processing.

## Development

### Running Tests

```bash
# Quick test run
make api-test

# Verbose output
make api-test-verbose

# With coverage
make api-cov
```

### Project Structure

```
quackcore/src/quackcore/adapters/http/
├── __init__.py          # Package initialization with graceful imports
├── app.py              # FastAPI app factory
├── auth.py             # Authentication utilities
├── config.py           # Configuration model
├── jobs.py             # Job management and execution
├── models.py           # Request/response DTOs
├── service.py          # Service lifecycle management
├── util.py             # Utility functions
└── routes/
    ├── __init__.py
    ├── health.py       # Health check endpoints
    ├── jobs.py         # Job management endpoints
    └── quackmedia.py   # QuackMedia convenience endpoints
```

### Adding New Operations

1. Add the operation to the `OP_TABLE` in `jobs.py`:

```python
OP_TABLE = {
    "quack-media.slice_video": ("quack_core.quack-media", "slice_video"),
    "your_module.new_operation": ("quack_core.your_module", "new_operation"),
}
```

2. The operation will automatically be available via the `/jobs` endpoint
3. Optionally add a convenience route in `routes/` for synchronous access

### Mock Functions

When QuackMedia modules aren't available, the system automatically falls back to mock functions that return:

```json
{
  "success": true,
  "operation": "operation_name",
  "message": "Mock execution of operation_name",
  "params": {...}
}
```

This enables development and testing without requiring all dependencies.

## Integration Examples

### n8n Workflow

1. **HTTP Request Node** - Create Job:
   - Method: POST
   - URL: `http://your-server:8080/jobs`
   - Headers: `Authorization: Bearer your-token`
   - Body:
     ```json
     {
       "op": "quack-media.slice_video",
       "params": {
         "input_path": "{{$node.previous.json.file_path}}",
         "output_path": "/processed/{{$node.previous.json.filename}}"
       }
     }
     ```

2. **Wait Node** - Delay between polling attempts

3. **HTTP Request Node** - Check Status:
   - Method: GET
   - URL: `http://your-server:8080/jobs/{{$node.CreateJob.json.job_id}}`

4. **Switch Node** - Branch on job status

### Python Client Example

```python
import httpx
import time
from typing import Dict, Any

class QuackCoreClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {"Authorization": f"Bearer {token}"}
    
    async def create_job(self, op: str, params: Dict[str, Any]) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/jobs",
                json={"op": op, "params": params},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()["job_id"]
    
    async def wait_for_job(self, job_id: str, timeout: int = 300) -> Dict[str, Any]:
        start_time = time.time()
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout:
                response = await client.get(
                    f"{self.base_url}/jobs/{job_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                status = response.json()
                
                if status["status"] in ["done", "error"]:
                    return status
                
                await asyncio.sleep(1)
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")
    
    async def slice_video_sync(self, **params) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/quack-media/slice",
                json=params,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

# Usage
client = QuackCoreClient("http://localhost:8080", "your-token")
job_id = await client.create_job("quack-media.slice_video", {
    "input_path": "/input.mp4",
    "output_path": "/output.mp4",
    "start": "00:01:00",
    "end": "00:02:00"
})
result = await client.wait_for_job(job_id)
```

### Webhook Integration

Set up a webhook endpoint to receive job completion notifications:

```python
from fastapi import FastAPI, Request
import hmac
import hashlib

app = FastAPI()

@app.post("/webhook/quackcore")
async def handle_quackcore_callback(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Quack-Signature", "")
    
    # Verify signature if HMAC is configured
    if signature and HMAC_SECRET:
        expected = f"sha256={hmac.new(HMAC_SECRET.encode(), body, hashlib.sha256).hexdigest()}"
        if not hmac.compare_digest(signature, expected):
            return {"error": "Invalid signature"}, 401
    
    data = await request.json()
    job_id = data["job_id"]
    status = data["status"]
    
    if status == "done":
        print(f"Job {job_id} completed successfully")
        # Process result...
    elif status == "error":
        print(f"Job {job_id} failed: {data['error']}")
        # Handle error...
    
    return {"received": True}
```

## Production Deployment

### Docker Example

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Install QuackCore with HTTP support
RUN pip install -e .[http]

EXPOSE 8080

CMD ["uvicorn", "quack_core.adapters.http.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
```

### Environment Configuration

```bash
# .env file
QUACK_HTTP__HOST=0.0.0.0
QUACK_HTTP__PORT=8080
QUACK_HTTP__AUTH_TOKEN=your-production-token
QUACK_HTTP__HMAC_SECRET=your-hmac-secret
QUACK_HTTP__MAX_WORKERS=8
QUACK_HTTP__JOB_TTL_SECONDS=7200
QUACK_HTTP__CORS_ORIGINS=["https://your-frontend.com"]
```

### Reverse Proxy (nginx)

```nginx
upstream quackcore_api {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name api.yoursite.com;
    
    location / {
        proxy_pass http://quackcore_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Security Considerations

1. **Always use authentication in production** - Set a strong `auth_token`
2. **Configure CORS appropriately** - Don't use `["*"]` in production
3. **Use HTTPS** - Never transmit tokens over HTTP
4. **Secure file paths** - Validate and sanitize all file paths
5. **Rate limiting** - Consider adding rate limiting middleware
6. **Callback verification** - Use HMAC signatures for webhook security
7. **Monitoring** - Log all API access and monitor for suspicious activity

## Troubleshooting

### Common Issues

**"HTTP adapter requires FastAPI" Error**
```bash
pip install quack-core[http]
```

**Jobs stuck in "queued" status**
- Check server logs for worker thread errors
- Verify QuackMedia dependencies are installed
- Increase `max_workers` if needed

**Authentication failures**
- Verify token matches configuration
- Check for extra whitespace in token
- Ensure `Authorization: Bearer ` format

**Callback failures**
- Check callback URL accessibility
- Verify HMAC signature if configured
- Monitor server logs for callback errors

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger("quack_core.adapters.http").setLevel(logging.DEBUG)
```

Check job status programmatically:

```bash
curl -H "Authorization: Bearer your-token" \
     http://localhost:8080/jobs/your-job-id
```

## API Documentation

Once running, interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`
- **OpenAPI JSON**: `http://localhost:8080/openapi.json`

## Limitations

- **In-memory job storage** - Jobs are lost on restart
- **No job persistence** - Consider external job queue for production
- **Single-node only** - No built-in clustering support
- **Basic auth** - Only Bearer token authentication supported
- **File path requirements** - Expects absolute paths with proper permissions

## Future Enhancements

- Redis-backed job storage
- Advanced authentication (JWT, OAuth2)
- Rate limiting middleware
- Metrics and monitoring endpoints
- Job scheduling and recurring tasks
- Multi-node job distribution

## Contributing

To contribute to the HTTP adapter:

1. Install development dependencies: `pip install quackcore[http,dev]`
2. Run tests: `make api-test`
3. Follow existing code patterns and add tests for new features
4. Update documentation for any API changes

## License

The HTTP adapter is part of QuackCore and follows the same license terms.