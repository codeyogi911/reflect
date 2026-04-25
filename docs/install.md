# Install

reflect ships as a Python package called `reflect-cli`. The console script is named `reflect`.

## With uv (recommended)

[uv](https://docs.astral.sh/uv/) is fast and handles isolation:

```bash
uv tool install reflect-cli
```

This installs `reflect` into uv's tool bin (typically `~/.local/bin`). Verify:

```bash
reflect --version
```

To upgrade later:

```bash
uv tool upgrade reflect-cli
# or, from inside any reflect-managed repo:
reflect upgrade
```

## Run without installing

```bash
uvx reflect --help
uvx reflect status
```

`uvx` resolves and caches the package on first invocation, then reuses it.

## With pip

```bash
pip install reflect-cli
```

If you're not using a virtualenv, prefer `pipx`:

```bash
pipx install reflect-cli
```

## From source (development)

```bash
git clone https://github.com/codeyogi911/reflect
cd reflect
uv sync --all-extras
uv run reflect --help
```

`uv sync --all-extras` creates an editable install plus the dev (pytest, ruff,
mypy) and docs (mkdocs-material) groups.

## Required and optional dependencies

| Tool         | Required? | Provides                                     | Install                              |
|--------------|-----------|----------------------------------------------|--------------------------------------|
| `git`        | required  | git history evidence                         | system package manager               |
| `qmd`        | required  | wiki search index                            | `npm install -g @tobilu/qmd`         |
| `entire`     | optional  | session-transcript evidence                  | `curl -fsSL https://entire.io/install.sh \| bash` |
| `claude` CLI | optional  | LLM ingest + context (deterministic without) | [claude.ai/code](https://claude.ai/code) |

`reflect init` will attempt to auto-install qmd (via npm) and Entire CLI if
they're missing.
