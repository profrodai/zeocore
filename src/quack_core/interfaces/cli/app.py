# quack-core/src/quack_core/interfaces/cli/app.py
import typer
import json
from quack_core.capabilities.demo import echo_text, EchoRequest, validate_video_ref, VideoRefRequest

app = typer.Typer()

@app.command()
def echo(text: str, preset: str = None):
    """Test the echo capability."""
    req = EchoRequest(text=text, preset=preset)
    result = echo_text(req)
    # Output raw JSON for inspection
    print(result.model_dump_json(indent=2))

@app.command()
def validate(url: str):
    """Test the video validation capability."""
    req = VideoRefRequest(url=url)
    result = validate_video_ref(req)
    print(result.model_dump_json(indent=2))

if __name__ == "__main__":
    app()