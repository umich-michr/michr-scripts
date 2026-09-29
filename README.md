# michr-scripts

`michr-scripts` is a polyglot monorepo for reusable libraries, runnable
applications, and operational scripts maintained by the Michigan Institute for
Clinical & Health Research (MICHR).

## Repository layout

```text
michr-scripts/
├── python/          Python workspace, packages, and programs
├── shell/           Shell scripts and projects
├── lua/             Lua scripts and projects
├── tools/           Repository-maintenance utilities
├── Makefile         Shared development interface
├── pyproject.toml   Python workspace and tool configuration
└── uv.lock          Locked Python dependencies
```

Documentation lives with the behavior it governs. Start with the language or
project area, then follow links to the owning program or package.

## Setup

Prerequisites:

- [`uv`](https://docs.astral.sh/uv/)
- `make`

Bootstrap a clone:

```bash
git clone https://github.com/umich-michr/michr-scripts
cd michr-scripts
make setup
```

`make setup` installs the Python workspace and Git hooks. Python does not need
to be installed separately; `uv` uses `.python-version`.

Useful repository commands:

```bash
make members
make doctor
make check
```

Run `make` or `make help` for the complete target list.

Do not manually activate `.venv`, use `pip`, or edit `uv.lock`.

## Project areas

### Python

See the [Python workspace guide](python/README.md) for:

- package and program catalogs;
- direct program commands;
- end-to-end workflow examples;
- command defaults;
- Python development guidance;
- links to member documentation.

### Shell

See [`shell/README.md`](shell/README.md).

### Lua

See [`lua/README.md`](lua/README.md).

### Repository tools

`tools/` contains utilities that maintain this repository. User-facing or
operational applications belong in their language-specific program area.

## Repository-wide quality gates

| Command | Purpose |
|---|---|
| `make format-check` | Verify Python formatting |
| `make lint` | Run Ruff |
| `make typecheck` | Run strict mypy |
| `make test` | Run all member tests |
| `make coverage` | Run all member coverage gates |
| `make docs-check` | Verify documentation synchronization |
| `make audit` | Audit dependencies and source |
| `make check` | Run the complete local and CI gate |
| `make hooks-run` | Run all pre-commit hooks |

Before committing:

```bash
make check
make hooks-run
git diff --check
git status --short
```

## Documentation ownership

| Subject | Owner |
|---|---|
| Repository purpose, layout, setup, and shared gates | Root `README.md` |
| Python workspace, catalogs, and common execution | [`python/README.md`](python/README.md) |
| Python program index | [`python/programs/README.md`](python/programs/README.md) |
| Program CLI and configuration | Program README and `docs/` |
| Package public API | Package README and `docs/` |
| Shell and Lua usage | Documentation beside each script or project |
| Shared agent guidance | `.github/copilot-instructions.md` |
| Member-specific agent rules | `.github/instructions/` |

Do not duplicate detailed program, package, or analytical rules in the root
README. Link to the owning document.

## Security and data handling

- Never commit credentials, production connection details, operational SQL,
  source exports, generated reports, or institutional data.
- Use synthetic values in tests, examples, and documentation.
- Avoid logging payloads, free text, credentials, or secret-bearing connection
  strings.
- Run operational programs only in approved environments under applicable U-M
  controls.
- Repository checks are guardrails and do not replace institutional policy.

## License

MIT
