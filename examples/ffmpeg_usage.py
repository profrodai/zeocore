"""
Example: probing and transcoding media with zeo_core.integrations.ffmpeg.

Requires the 'ffmpeg' extra:

    uv pip install "zeocore[ffmpeg]"

This wraps the org's own ffmpeg-zeo PyPI package (not the raw ffmpeg
binary directly) -- ffmpeg-zeo resolves real ffmpeg/ffprobe binaries
(downloading them if configured to, or finding them on PATH) and this
integration calls a small, curated set of its "recipes": probe, convert,
transcode_h264, extract_audio, thumbnail.

ffmpeg-zeo itself requires Python >=3.12; zeocore's own floor is >=3.14,
comfortably above that, so the extra installs cleanly on any
zeocore-supported interpreter, no version straddling.

This example needs a real ffmpeg/ffprobe on PATH (or resolvable via
ffmpeg-zeo's own download mechanism) to do anything -- it generates a tiny
synthetic test video with ffmpeg's own `lavfi` source (a colored test
pattern, no external file needed) rather than requiring you to supply
one.

Run this file directly:

    uv run examples/ffmpeg_usage.py
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from zeo_core.integrations.ffmpeg import FFmpegIntegration


def _generate_sample_video(path: Path) -> bool:
    """
    Generate a 1-second synthetic test video with ffmpeg's own lavfi
    source, so this example needs no external media file. Returns False
    (rather than raising) if the ffmpeg binary isn't on PATH -- this
    helper runs BEFORE the integration's own initialize() check, so a
    missing binary is caught here first with a clear message.
    """
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin is None:
        return False

    result = subprocess.run(  # noqa: S603 -- fixed argv, resolved absolute binary path via shutil.which, no shell
        [
            ffmpeg_bin,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=1:size=320x240:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0 and path.exists()


def main() -> None:
    """
    Initialize the ffmpeg integration, probe a synthetic video, transcode
    it, and generate a thumbnail -- all real subprocess calls through the
    real ffmpeg-zeo package, not mocked.
    """
    scratch_dir = Path("./tmp_ffmpeg_example")
    scratch_dir.mkdir(exist_ok=True)

    try:
        sample_path = scratch_dir / "sample.mp4"
        if not _generate_sample_video(sample_path):
            print(
                "ffmpeg binary not found on PATH (or sample generation "
                "failed) -- skipping (graceful skip, not an error). "
                "Install ffmpeg (e.g. `brew install ffmpeg`) to see this "
                "example run end to end."
            )
            return

        # FFmpegConfigProvider (like NotionConfigProvider, unlike
        # jupytext's) has no override that falls back to defaults on a
        # missing config file -- the base provider RAISES instead. A
        # minimal config file with an empty `ffmpeg: {}` block is enough.
        config_path = scratch_dir / "zeo_config.yaml"
        config_path.write_text("ffmpeg:\n  output_dir: .\n")

        ffmpeg = FFmpegIntegration(config_path=str(config_path))
        init_result = ffmpeg.initialize()
        if not init_result.success:
            print(f"Failed to initialize ffmpeg integration: {init_result.error}")
            return
        print(f"FFmpeg integration initialized: {init_result.message}")

        # Probe: real ffprobe under the hood, returns raw ffprobe JSON
        # plus derived convenience keys (has_video, width, height, ...).
        probe_result = ffmpeg.probe(str(sample_path))
        if not probe_result.success:
            print(f"probe failed: {probe_result.error}")
            return

        info = probe_result.content
        assert info is not None  # noqa: S101 -- success==True guarantees content
        print(
            f"Probed sample: {info['width']}x{info['height']}, "
            f"video_codec={info['video_codec']}, "
            f"duration={info['duration_seconds']:.2f}s"
        )

        # Transcode to H.264 at a specific quality/preset.
        transcode_result = ffmpeg.transcode_h264(
            str(sample_path), crf=30, preset="ultrafast"
        )
        if not transcode_result.success:
            print(f"transcode_h264 failed: {transcode_result.error}")
            return

        transcoded_path = Path(str(transcode_result.content))
        print(f"Transcoded to: {transcoded_path.name}")

        # Generate a thumbnail at the 0.5s mark.
        thumbnail_result = ffmpeg.thumbnail(str(sample_path), time=0.5)
        if not thumbnail_result.success:
            print(f"thumbnail failed: {thumbnail_result.error}")
            return

        thumbnail_path = Path(str(thumbnail_result.content))
        print(f"Thumbnail written to: {thumbnail_path.name}")
        print(f"Thumbnail exists on disk: {thumbnail_path.exists()}")

        print(
            f"\nmetrics: total_attempts={ffmpeg.metrics.total_attempts}, "
            f"successful_renders={ffmpeg.metrics.successful_renders}, "
            f"failed_renders={ffmpeg.metrics.failed_renders}"
        )
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
