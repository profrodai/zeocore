# Local integration setup

<!-- Teaches CLAUDE.md Rev 17; user documentation reviewed 2026-09-08. -->

From the source checkout, install the Python extras needed by your tools with
`uv pip install -e ".[pandoc,ffmpeg,jupytext]"` in the activated environment.
The Pandoc and FFmpeg executables are installed separately as described below.

Pandoc, FFmpeg and Jupytext have no provider account, API key or cloud sandbox.
Their test and production tracks separate inputs, configuration, temporary
files and outputs using the [environment launcher](environments.md). Install
only the tools needed for your application; keep their executable versions in
your deployment inventory. Missing executables must fail the live check.

## Pandoc

Install Pandoc using the package/download instructions for your operating
system at [Pandoc installation](https://pandoc.org/installing.html). Confirm
`pandoc --version` succeeds in the same shell/PATH used to launch ZeoCore.
The supported service operations include HTML to Markdown and Markdown to
DOCX. PDF conversion can need additional engines and is not this setup check.

In the test work directory create a tiny HTML file and call the real service:

```python
from pathlib import Path
from zeo_core.integrations.pandoc.service import PandocIntegration

Path("probe.html").write_text(
    "<!doctype html><html><head><title>Test</title></head>"
    "<body><h1>ZeoCore test</h1><p>Known text. This complete synthetic document "
    "is deliberately long enough to pass the converter minimum output size "
    "validation without disabling any checks.</p></body></html>"
)
service = PandocIntegration(output_dir=str(Path.cwd() / "output"))
assert service.initialize().success
result = service.html_to_markdown("probe.html", "probe.md")
assert result.success, result.message
assert "Known text." in Path("probe.md").read_text()
print("Pandoc converted the known test document")
```

Save as `check_pandoc.py` and run:

```bash
python -m zeo_core.integrations.environments --mode test   --root "$ZEO_ENV_ROOT" --integration pandoc --   python /absolute/path/check_pandoc.py
```

For a DOCX E2E check also call `markdown_to_docx("probe.md", "probe.docx")`,
assert success, and open the generated document to check headings and text.

## FFmpeg

Install FFmpeg and its companion `ffprobe` from your OS package manager or a
build linked by [FFmpeg downloads](https://ffmpeg.org/download.html). Confirm
`ffmpeg -version` and `ffprobe -version`. ZeoCore's Python wrapper also needs
its normal locked dependencies; installing a similarly named unrelated Python
package does not supply these binaries.

Save this complete synthetic audio check as `check_ffmpeg.py`:

```python
from pathlib import Path
import wave
from zeo_core.integrations.ffmpeg.service import FFmpegIntegration

with wave.open("probe.wav", "wb") as audio:
    audio.setnchannels(1)
    audio.setsampwidth(2)
    audio.setframerate(8000)
    audio.writeframes(b"\x00\x00" * 8000)
service = FFmpegIntegration(output_dir=str(Path.cwd() / "output"))
assert service.initialize().success
assert service.probe("probe.wav").success
result = service.convert("probe.wav", "probe.flac")
assert result.success, result.message
assert Path("probe.flac").stat().st_size > 0
assert service.probe("probe.flac").success
print("FFmpeg converted and probed synthetic media")
```

```bash
python -m zeo_core.integrations.environments --mode test   --root "$ZEO_ENV_ROOT" --integration ffmpeg --   python /absolute/path/check_ffmpeg.py
```

For video/render qualification use the existing
[synthetic video example](../../examples/ffmpeg_usage.py) in test mode and
inspect its generated video/thumbnail. Successful probing alone does not prove
perceived video or audio quality.

## Jupytext

Jupytext is a local Python notebook converter. Follow
[Jupytext installation](https://jupytext.readthedocs.io/en/latest/install.html)
and verify `jupytext --version` in the application's Python environment.
The ZeoCore checkout's dependency setup already supplies it. No Jupyter server
login or notebook execution permission is needed to convert files.

Save as `check_jupytext.py`:

```python
from pathlib import Path
import json
from zeo_core.integrations.jupytext.service import JupytextIntegration

Path("probe.py").write_text("# %%\nvalue = 2 + 3\n")
service = JupytextIntegration(output_dir=str(Path.cwd() / "output"))
assert service.initialize().success
result = service.script_to_notebook("probe.py", "probe.ipynb")
assert result.success, result.message
notebook = json.loads(Path("probe.ipynb").read_text())
assert notebook["cells"][0]["cell_type"] == "code"
assert "value = 2 + 3" in "".join(notebook["cells"][0]["source"])
back = service.notebook_to_script("probe.ipynb", "roundtrip.py")
assert back.success, back.message
assert "value = 2 + 3" in Path("roundtrip.py").read_text()
print("Jupytext preserved the known cell through a round trip")
```

```bash
python -m zeo_core.integrations.environments --mode test   --root "$ZEO_ENV_ROOT" --integration jupytext --   python /absolute/path/check_jupytext.py
```

This converts the source; it does not execute notebook cells.

## Production track for all three tools

Prepare production mode separately. Copy approved input assets into
`$ZEO_ENV_ROOT/production/work/input` and put the production converter settings
in `production/config/integrations.yaml`. Use an application script with
explicit input/output paths under that mode's work directory. Run the same
small synthetic check once with `--mode production` before processing real
assets; these scripts create only their named `probe`/`roundtrip` files.
For example:

```bash
python -m zeo_core.integrations.environments --mode production   --root "$ZEO_ENV_ROOT" --integration jupytext --   python /absolute/path/check_jupytext.py
```

Substitute `pandoc`/`check_pandoc.py` or `ffmpeg`/`check_ffmpeg.py` for those
tools. Never use a shared output directory for test and production. Explicit
application paths can still point outside the managed work directory: the
launcher is not an OS filesystem sandbox. Review those paths before batch
conversion and keep originals recoverable.

Canonical configuration variables beginning `ZEO_PANDOC_`, `ZEO_FFMPEG_`, or
`ZEO_JUPYTEXT_` must have the additional environment prefix when supplied to the
launcher, for example `ZEO_TEST_ZEO_PANDOC_OUTPUT_DIR`. Prefer the per-mode YAML
for a readable deployment configuration. Do not put executable content or
secrets in config copied from an untrusted source.

## E2E evidence and cleanup

Record executable versions, mode, sanitized input/output names, conversion
result and content comparison. Inspect rendered DOCX/video where applicable.
A fixture test with a fake converter is distinct from running the real binary.
After inspecting results remove only the known test artifacts from `test/work`;
do not run a recursive cleanup against a production or shared asset directory.
If initialization fails, check executable PATH and the selected mode's config.
No credential rotation is necessary because these tools have no API keys.
