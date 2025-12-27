# === QV-LLM:BEGIN ===
# path: quack-core/src/quack_core/interfaces/api/server.py
# module: quack_core.interfaces.api.server
# role: api
# neighbors: __init__.py
# exports: api_echo_text, api_validate_video
# git_branch: refactor/newHeaders
# git_commit: 0600815
# === QV-LLM:END ===

from fastapi import FastAPI
from quack_core.contracts.capabilities.demo import echo_text, EchoRequest, validate_video_ref, VideoRefRequest, CapabilityResult

app = FastAPI(title="QuackCore Capability API")

@app.post("/capabilities/demo/echo", response_model=CapabilityResult[str])
def api_echo_text(request: EchoRequest):
    return echo_text(request)

@app.post("/capabilities/media/validate", response_model=CapabilityResult[bool])
def api_validate_video(request: VideoRefRequest):
    return validate_video_ref(request)