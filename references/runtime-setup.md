# Runtime Setup

Run setup from the skill root before doing real work from a fresh checkout:

```bash
python scripts/setup.py
```

The setup script installs an editable Python runtime into:

```text
~/.agentfeeds/runtime-venv/
```

The script wrappers re-exec through that virtual environment when it exists:

```bash
python scripts/agentfeeds.py --help
python scripts/agentfeeds_fetch.py --help
```

If Python cannot create a venv with `pip`, `scripts/setup.py` falls back to `uv pip install` when `uv` is available. If both `pip` and `uv` are missing, install one of them and rerun setup.

Console entry points installed by the package remain acceptable for local development:

```bash
agentfeeds --help
agentfeeds-fetch --help
```

For portable skill usage, prefer the bundled scripts.
