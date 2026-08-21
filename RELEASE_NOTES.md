# zeocore 0.4.0

A hardening release: no new integrations, no breaking changes. It fixes a documentation defect,
adds a gitignore rule, and tightens credential file permissions.

## Lead item: a docs fix, because that's what was actually exposing users

The most severe thing in this release is not code — it's that `GET-STARTED.md` was teaching
users the wrong pattern. Its "Creating Custom Configuration" walkthrough had a junior construct
a secret inline (`MyAppConfig(api_key="your-api-key")`) and then call `.model_dump()` on it into
a `ZeoConfig.custom` dict that gets persisted to a YAML file — a file no `.gitignore` rule
protected. A second instance, not previously caught, embedded a literal `api_key: "your-api-key"`
in the same file's worked YAML example further down. Both are fixed: the walkthrough now reads
the secret from the environment and never serializes the object holding it.

**To be plain: no leak ever occurred.** `git log --all --diff-filter=A` finds no config or
secret file ever committed to this repo, and no credentials file exists anywhere on this host.
This release closes a *documented path to a future mistake*, not an incident. Nobody's secret
was exposed by this defect — the fix exists because the officially-taught pattern would have
exposed the next person who followed it correctly.

## What's new

- **`.env` is now the documented home for secrets.** This is not a runtime change — zeocore
  already merges `os.environ` over YAML config, so this changes where a byte is typed, not what
  the process does with it. It's adopted because YAML config files get committed by default and
  `.env` files don't, and zeocore's audience is junior enough that the default is the whole
  product. A new `.env.example` ships at the repo root with placeholders for `NOTION_TOKEN`,
  `GITHUB_TOKEN`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`. zeocore does not load `.env` on import —
  that stays your shell's or process manager's job (`uv run --env-file .env ...`, your own
  `python-dotenv` call, etc.) — a deliberate choice, not an oversight; see "Named, not fixed."
- **`.gitignore` now covers the two repo-relative default config locations**
  (`/zeo_config.yaml`, `/config/zeo_config.yaml`). Defense in depth: this protects the user who
  ignores the docs and types a secret into config YAML anyway, stopped by a rule instead of their
  own attention.
- **Credential files are now written `0600`.** The three credential writers
  (`google/auth.py`, `notion/auth.py`, `github/auth.py`) pass an explicit mode through the fs
  write chain, covering both the atomic and non-atomic write branches. The actual defect: the
  atomic-write path preserved a pre-existing loose file mode forever, with no path to tighten it
  on a later write. Newly-created files were already born `0600` under this repo's own umask
  probe — this is **not** a fix for files being created at `0644`; that defect does not exist,
  and an earlier draft of this analysis that claimed it did was wrong.

## Upgrade guidance for existing users

- If you already have a credentials file on disk from an earlier zeocore version, it may still
  be at whatever mode it was originally created with (commonly `0644` under a permissive umask).
  It is **not** retroactively tightened by installing this release — it tightens automatically
  the next time your integration writes to it (re-auth, token refresh, etc.), since the writer
  now passes `mode=0o600` on every write. If you want it tightened immediately: `chmod 0600
  <your credentials file>`.
- If you currently have a real secret sitting in a committed or uncommitted config YAML file
  (`zeo_config.yaml`, `config/zeo_config.yaml`, or elsewhere), move it to `.env` now. Copy
  `.env.example`, put the real value there, and remove it from the YAML file. If that YAML file
  was ever committed, treat the secret as compromised and rotate it — a `.gitignore` rule added
  today does not retroactively remove history.

## Named, not fixed

Recorded here rather than silently fixed or silently ignored — each is real, ranked, and out of
this release's own scope:

- **The env-writeback opt-in** (`LLMConfigProvider._setup_environment_variables`,
  `llms/config.py:228-273`) copies an `api_key` out of loaded YAML config into `os.environ` when
  the env var isn't already set. Sized this round, not changed: exactly **one gated production
  call site** reaches it (`prompt/_internal/enhancer.py`, itself behind an explicit `use_llm`
  opt-in), and a second candidate construction site is dead code with no live callers. Turning
  this off by default is still a breaking change for that one site — this release only replaces
  a broad, unenumerated estimate with a real count.
- **Typed secret models (`SecretStr`) aren't a drop-in fix here.** `ZeoConfig` has no
  secret-shaped field — `integrations` and `custom` are both untyped `dict[str, Any]`, so
  adopting `SecretStr` means designing how that dict is typed, not annotating an existing field.
- **`~/.zeo/config.yaml` and `/etc/zeo/config.yaml`** — two of the four default config
  locations — sit outside any git working tree, so no repo-local `.gitignore` rule can cover
  them. `.env` is the mitigation that doesn't depend on which config location you use.

## Upgrading

```bash
pip install --upgrade zeocore
```

No breaking changes in this release — upgrading from `0.3.x` requires no code changes.

Full diff: https://github.com/zeroemployeeorg/zeocore/compare/v0.3.0...v0.4.0
